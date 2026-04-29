# Smoke Test — Template Tiragem Express ponta-a-ponta

> Guia manual pra você (Magno) validar que o template Express funciona end-to-end no seu ambiente. Não roda em CI — exige Supabase, WhatsApp Cloud API e .env real.

---

## Pré-requisitos (15 min)

- [ ] [.env](../.env) com:
  - `WEBAPP_TOKEN` e `PHONE_NUMBER_ID` (WhatsApp Cloud API — Meta Developer Console)
  - `GEMINI_API_KEY`
  - `NEXT_PUBLIC_SUPABASE_URL` e `SUPABASE_SERVICE_ROLE_KEY`
  - `WHATSAPP_TYPING_ENABLED=1` (opcional, mais bonito)
- [ ] Bucket `templates-public` criado no Supabase (Storage → New bucket → marcar **Public**)
- [ ] Pelo menos 5 imagens JPG na sua máquina:
  - `baralho_fechado.jpg` — qualquer foto de baralho fechado
  - `o_louco.jpg`, `o_mago.jpg`, `a_torre.jpg`, `a_lua.jpg` — pode ser qualquer JPG mockup pro smoke test
  
  Pra teste mais real, pegue do Wikimedia Commons (ver [MARSELHA_ASSETS.md](MARSELHA_ASSETS.md))

- [ ] Seu próprio número de WhatsApp registrado como destino de teste no app Meta

---

## Etapa 1 — Validar pasta local + subir imagens (5 min)

```bash
cd projeto_cigana

# Lista os 79 slugs esperados:
py scripts/upload_marselha_storage.py --list | head -10

# Validar que sua pasta tem (pelo menos) os arquivos do smoke test:
py scripts/upload_marselha_storage.py /caminho/para/sua/pasta --dry-run
```

Para o smoke, **não precisa dos 79** — basta ter `baralho_fechado.jpg` + 5 cartas (qualquer 5 dos 78 slugs). A função `enviar_tres_cartas` sorteia 3 das 78 — se a URL retornar 404, o WhatsApp ignora a imagem mas o resto do fluxo segue.

Pra subir:

```bash
SUPABASE_URL=https://xxxxxx.supabase.co \
SUPABASE_SERVICE_ROLE_KEY=eyJhbG... \
py scripts/upload_marselha_storage.py /caminho/para/sua/pasta
```

Esperar `--- RESUMO --- sucessos=N falhas=0`.

---

## Etapa 2 — Validar URLs públicas (1 min)

```python
# python REPL
from flows.tarot.cartas import sortear_3_cartas, url_imagem, url_baralho_fechado

BASE = "https://xxxxxx.supabase.co/storage/v1/object/public/templates-public"
print(url_baralho_fechado(BASE))
for c in sortear_3_cartas(seed=0):
    print(c.nome, "→", url_imagem(c, BASE))
```

Cole as URLs no navegador. Devem abrir as imagens. Se der 404, voltar à etapa 1.

---

## Etapa 3 — Criar tenant + blueprint via Python shell (3 min)

```python
# python REPL — projeto_cigana
from db.database import Base, SessionLocal, engine
from db import models
from flows.post_payment.seeds import load_seed

# 1. Garantir tabelas criadas
Base.metadata.create_all(bind=engine)

# 2. Criar lead de teste (use SEU número WhatsApp pra receber a mensagem)
TENANT = "smoke_test"
TELEFONE = "5511999999999"  # ← seu número, com DDI 55 sem +

db = SessionLocal()
lead = db.query(models.Lead).filter_by(tenant_id=TENANT, telefone=TELEFONE).first()
if not lead:
    lead = models.Lead(tenant_id=TENANT, telefone=TELEFONE, node_atual="14_confirmacao_entrega")
    db.add(lead)
    db.commit()
print(f"Lead criado: id={lead.id}")

# 3. Criar blueprint post_payment do tenant a partir do seed Express
existing = db.query(models.FlowBlueprint).filter_by(tenant_id=TENANT, slug="post_payment").first()
if existing:
    db.delete(existing)
    db.commit()
seed = load_seed("express")
bp = models.FlowBlueprint(
    tenant_id=TENANT,
    slug="post_payment",
    title=seed["title"],
    body_json=seed,
)
db.add(bp)
db.commit()
print(f"Blueprint criado: id={bp.id}")
db.close()
```

---

## Etapa 4 — Disparar dispatch direto (1 min)

```python
from api.payments.dispatch import dispatch_post_payment_blueprint

ok = dispatch_post_payment_blueprint(
    tenant_id="smoke_test",
    lead_id=lead.id,  # do passo anterior
    provider="cakto",
    event_id="smoke_test_evt_001",
    payment_metadata={"amount": 1990, "product": "Tiragem Express"},
)
print(f"dispatch={ok}")
```

Esperar `dispatch=True`.

**O que acontece em background** (logs em stdout/Sentry):
1. Thread daemon spawnada
2. Blueprint compilado pelo `flow_executor.document_to_acoes`
3. `_enfileirar_acoes_pendente` chamado com a lista de Acao
4. **HOJE: só loga.** Pra mensagem chegar no WhatsApp, precisa de uma das duas integrações:
   - Opção A da [ENGINE_QUEUE_INTEGRATION.md](ENGINE_QUEUE_INTEGRATION.md) já está aplicada → use [Etapa 5a](#etapa-5a)
   - Caso contrário → use [Etapa 5b](#etapa-5b) (motor.iniciar_fluxo_post_venda direto)

---

## Etapa 5a — Verificar via `Motor.iniciar_fluxo_post_venda` (com Opção A aplicada)

A Opção A do GAP é o **surgical edit em `engine.py:911`** que faz `iniciar_fluxo_post_venda` consultar o blueprint primeiro. Se o seu engine.py já tem `_compile_post_payment_blueprint`:

```python
from engine import motor
motor.tenant_id = "smoke_test"  # forçar tenant
motor.iniciar_fluxo_post_venda(TELEFONE)
```

**Esperado:**
- Logs: `[engine] post_venda usando blueprint customizado: tenant=smoke_test ...`
- Seu WhatsApp recebe (em sequência):
  1. "🔮 Recebi tua energia. Pagamento confirmado..."
  2. (pausa 30s)
  3. "As cartas que sairão pra ti são únicas..."
  4. **3 imagens de cartas** (uma a cada 2s, via motor_ref → `flows.tarot.envio:sortear_e_enviar_3_cartas`)
  5. "Lê com calma. Deixa cada carta tocar onde precisa."
  6. (após 24h) Mensagem de oferta de recorrência

Pra não esperar 24h no smoke, edite `delay_24h.config.delay_amount` pra `1` no body_json do blueprint antes do dispatch.

---

## Etapa 5b — Verificar sem Opção A (motor.iniciar_fluxo_post_venda legado)

Se o engine.py ainda não tem o hook, o motor vai usar o caminho legado e o blueprint não será disparado — você verá só as mensagens hardcoded do `_executar_node`.

Pra forçar o blueprint sem aplicar a Opção A, manualmente:

```python
from db.database import SessionLocal
from db import models
from flow_executor import document_to_acoes

db = SessionLocal()
bp = db.query(models.FlowBlueprint).filter_by(tenant_id="smoke_test", slug="post_payment").first()
lead = db.query(models.Lead).filter_by(tenant_id="smoke_test", telefone=TELEFONE).first()
acoes = document_to_acoes(
    bp.body_json,
    context={"lead_id": lead.id, "telefone": lead.telefone, "nome": lead.nome or ""},
    tenant_id="smoke_test",
    blueprint_id=bp.id,
)
print(f"acoes compiladas: {len(acoes)}")
for a in acoes[:3]:
    print(f"  - tipo={a.tipo} conteudo={a.conteudo[:60]}")
db.close()
```

Compila mas NÃO envia (esse é exatamente o gap que a integração resolve).

---

## Etapa 6 — Limpar smoke test

```python
from db.database import SessionLocal
from db import models

db = SessionLocal()
db.query(models.FlowBlueprint).filter_by(tenant_id="smoke_test").delete()
db.query(models.Lead).filter_by(tenant_id="smoke_test").delete()
db.query(models.PaymentEventReceipt).filter_by(tenant_id="smoke_test").delete()
db.commit()
db.close()
print("smoke_test cleaned")
```

---

## Sinais de sucesso (checklist)

- [ ] URLs do Supabase Storage abrem no navegador
- [ ] Lead criado com `tenant_id=smoke_test`
- [ ] Blueprint criado com `slug=post_payment`
- [ ] `dispatch_post_payment_blueprint` retornou `True`
- [ ] Etapa 5a/5b: blueprint compilou sem erro
- [ ] Etapa 5a: 3 imagens chegaram no WhatsApp em sequência (com pausa de ~2s entre cada)

## Falhas comuns

| Sintoma | Causa provável | Fix |
|---|---|---|
| `dispatch=False` | Lead ou blueprint não existe pro tenant | Refazer etapa 3 |
| `404` na URL Supabase | Bucket não público OU arquivo não subido | Storage → editar bucket → marcar Public |
| Mensagem não chega no WhatsApp | `WEBAPP_TOKEN` inválido OU número não cadastrado no Meta | Conferir Meta Developer Console → WhatsApp → Configuration |
| Imagens enviam mas com 404 visual | URLs corretas mas Storage não tem o JPG | Etapa 1 → upload |
| Blueprint compila vazio | YAML inválido ou edge mal formado | Validar com `validate_post_payment_blueprint(seed)` |
| Erro de import circular | env de teste sem `.env` carregado | Carregar `dotenv` no REPL antes |

## Quando esse smoke vira CI

Quando a Fase 3 estiver pronta (login + onboarding wizard real), o smoke vira teste E2E automatizado:
- Tenant criado via API HTTP
- Blueprint clonado via API HTTP
- Webhook simulado via HTTP POST com signature válida
- Mensagens verificadas via mock do `whatsapp_client.enviar_mensagem`

Por enquanto, é manual.
