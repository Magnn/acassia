# Integração `dispatch.py` ↔ Fila do Motor

> Após G5a, a função `_run_post_payment` em [api/payments/dispatch.py](../api/payments/dispatch.py) **compila** o blueprint mas **ainda não envia** as Acao resultantes pra fila real do motor (envio WhatsApp). Este doc documenta o gap, o que foi descoberto sobre a arquitetura, e os caminhos pra fechar.

---

## Diagnóstico — como a fila funciona hoje

### Entrypoints existentes

[engine.py:911](../engine.py) — `Motor.iniciar_fluxo_post_venda(telefone)`:

```python
def iniciar_fluxo_post_venda(self, telefone: str):
    db = SessionLocal()
    lead = self._obter_ou_criar_lead(db, telefone)
    lead.convertido = True
    lead.node_atual = target_entrega   # "14_confirmacao_entrega" ou static_meumisterio_b7
    # ... audit ...
    ctx = ContextoConversa(lead_id=lead.id, telefone=..., node_atual=target_entrega, ...)
    ctx.metadata["__config__"] = CONFIG_CLIENTE
    # injects studio + flow metadata
    self._restaurar_memoria(lead, ctx)
    acoes = self._executar_node(target_entrega, ctx, db, lead)   # ← caminho HARDCODED
    self._processar_fila(lead.id, ctx, acoes)                    # ← envio efetivo
```

[engine.py:1037](../engine.py) — `Motor._processar_fila(lead_id, ctx, acoes)`:
- Pega lock por lead (`_lock_envio_lead`) — evita corrida quando 2 webhooks chegam
- Aplica gancho de transformação (`aplicar_gancho_na_lista_acoes`)
- Trata cada `Acao` por tipo (`text`, `audio`, `image`, `delay`, `typing`, `tts`)
- Envia via WhatsApp Cloud API
- Persiste mensagens em `Mensagem` table

### Schema da `Acao`

[schema.py:17](../schema.py):

```python
@dataclass
class Acao:
    tipo: str          # text|interactive|audio|image|vcard|delay|tts|typing
    conteudo: str      # texto da mensagem, número do vcard, etc
    url: str           # URL pra mídia externa
    segundos: int      # delay em segundos
    tts_template: str  # template pra voz
    metadata: dict     # extras
```

### Compilação blueprint → Acao já existe

[flow_executor.py:197](../flow_executor.py) — `document_to_acoes(doc, context, *, blueprint_id, tenant_id, ...)` retorna `list[Acao]`. Isso já é o que `dispatch._run_post_payment` chama.

---

## Onde está o gap

`api/payments/dispatch.py:_enfileirar_acoes_pendente` recebe a lista de Acao mas só loga — **não chama** `motor._processar_fila`. Resultado: blueprint compila, mas mensagem não vai pro WhatsApp.

---

## 3 caminhos pra fechar a integração

### Opção A — Surgical edit em `engine.py:911` (recomendado)

Modificar `Motor.iniciar_fluxo_post_venda` pra **olhar primeiro** se o tenant tem blueprint `post_payment`. Se sim, compilar e usar suas Acao em vez do `_executar_node` hardcoded. Se não, fallback ao caminho atual.

**Patch conceitual** (~15 linhas):

```python
def iniciar_fluxo_post_venda(self, telefone: str):
    db = SessionLocal()
    try:
        lead = self._obter_ou_criar_lead(db, telefone)
        # ... mark convertido + audit como antes ...
        ctx = ContextoConversa(...)
        # ... inject metadata ...

        # NEW: tenta blueprint primeiro
        bp_acoes = self._compile_post_payment_blueprint(db, ctx)
        if bp_acoes is not None:
            acoes = bp_acoes
            logger.info("[engine] post_venda usando blueprint customizado")
        else:
            acoes = self._executar_node(target_entrega, ctx, db, lead)

        self._processar_fila(lead.id, ctx, acoes)
    finally:
        db.close()


def _compile_post_payment_blueprint(self, db, ctx) -> Optional[list[Acao]]:
    """Tenta compilar blueprint slug=post_payment do tenant. None se não tem."""
    bp = db.query(FlowBlueprint).filter_by(
        tenant_id=self.tenant_id, slug="post_payment"
    ).first()
    if not bp:
        return None
    try:
        from flow_executor import document_to_acoes
        return document_to_acoes(
            bp.body_json or {},
            context=ctx.__dict__,  # ou um dict construído
            tenant_id=self.tenant_id,
            blueprint_id=bp.id,
        )
    except Exception:
        logger.exception("[engine] blueprint post_payment falhou — fallback")
        return None
```

**Prós:**
- Mudança local e bem-definida (~15 linhas)
- Reusa toda a infra de queue + locks + audit que já funciona
- Mantém retrocompatibilidade (sem blueprint → caminho antigo intacto)
- `dispatch_post_payment_blueprint` em api/payments fica como segundo entry-point pra webhooks novos
- Nada precisa ser refatorado em app.py

**Contras:**
- Toca `engine.py` (172k linhas — mas só 1 lugar local)
- `dispatch.py` fica obsoleto pra esse caminho — só faz sentido pra webhooks novos que NÃO passam por `iniciar_fluxo_post_venda`

### Opção B — `dispatch.py` chama `motor._processar_fila` direto

Atualizar `_enfileirar_acoes_pendente` pra:
1. Construir `ContextoConversa` mínimo a partir do lead
2. Importar `motor` (singleton) e chamar `motor._processar_fila(lead.id, ctx, acoes)`

**Prós:**
- Sem tocar engine.py
- `dispatch.py` vira self-contained (webhook → blueprint → queue)

**Contras:**
- Chama método privado (`_processar_fila`) — frágil
- Duplica responsabilidades de `iniciar_fluxo_post_venda` (mark convertido, audit) que precisam acontecer **antes** de _processar_fila
- `ContextoConversa` precisa ser construído manualmente — fácil errar metadata necessário (ex: studio injection, flow metadata)
- Importar `from app import motor` pode trazer side-effects do import-time da app

### Opção C — Refatorar `Motor` pra expor `enqueue_acoes(lead_id, acoes)` público

Adicionar método público em `Motor` que apenas processa a fila:

```python
def enqueue_acoes(self, lead_id: int, telefone: str, acoes: list[Acao]) -> None:
    """API pública pra outros módulos enfileirarem ações sem replicar boilerplate."""
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter_by(id=lead_id).first()
        if not lead:
            return
        ctx = ContextoConversa(...)  # construção mínima centralizada
        self._processar_fila(lead_id, ctx, acoes)
    finally:
        db.close()
```

E `dispatch.py` chama essa API pública.

**Prós:**
- Separação limpa de responsabilidades
- Testável (motor.enqueue_acoes pode ser mockado)
- Reusável por outros módulos no futuro

**Contras:**
- 2 mudanças (engine.py + dispatch.py)
- Decisão sobre o que entra no `ContextoConversa` mínimo precisa ser tomada
- Mais código que A

---

## Recomendação

**Opção A pra primeira iteração** (semana de G5b).

Razões:
1. Mudança menor e bem-bounded
2. Backward-compatible (clientes sem blueprint continuam funcionando)
3. Reusa todos os hooks que `iniciar_fluxo_post_venda` já tem (audit, studio injection, flow metadata)
4. `dispatch_post_payment_blueprint` em api/payments **continua útil** pra webhooks NOVOS que querem ignorar o caminho legado de `iniciar_fluxo_post_venda` — não conflita

Após **A em produção**, considerar **C** quando refatoração maior do motor estiver na pauta.

---

## Implementação proposta (Opção A)

Diff conceitual em `engine.py:911`:

```diff
 def iniciar_fluxo_post_venda(self, telefone: str):
     db = SessionLocal()
     try:
         lead = self._obter_ou_criar_lead(db, telefone)
         node_antes = lead.node_atual
         lead.convertido = True
         # ... target_entrega, registrar_node_transition, db.commit()
         ctx = ContextoConversa(...)
         ctx.metadata["__config__"] = CONFIG_CLIENTE
         # ... inject studio + flow metadata ...
         self._restaurar_memoria(lead, ctx)
-        acoes = self._executar_node(target_entrega, ctx, db, lead)
+        acoes = self._compile_post_payment_blueprint(db, ctx) \
+            or self._executar_node(target_entrega, ctx, db, lead)
         self._processar_fila(lead.id, ctx, acoes)
```

Adicionar novo método `_compile_post_payment_blueprint` (~20 linhas) abaixo do existente.

**Tests:**
- Lead com blueprint slug=post_payment → motor usa as Acao do blueprint
- Lead sem blueprint → fallback pro `_executar_node`
- Blueprint inválido → fallback + log de erro

**Estimativa:** 1 dia (incluindo tests).

---

## Quando essa integração for feita

Atualizar:
- [GAP_ENGINE_VS_CIGANA_TAROT.md](GAP_ENGINE_VS_CIGANA_TAROT.md) — marcar G5b como ✅
- [api/payments/dispatch.py](../api/payments/dispatch.py) — `_enfileirar_acoes_pendente` chama `motor.enqueue_acoes` (Opção C) ou só loga "use motor.iniciar_fluxo_post_venda" (Opção A)
- Adicionar test E2E que exercita: webhook chega → idempotência → dispatch → blueprint compila → fila envia → mensagem persiste em `Mensagem`
