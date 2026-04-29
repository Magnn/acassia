# ADR 005 — Cadência de recovery configurável por tenant

**Status:** Aceito
**Data:** 2026-04-28
**Decisor:** Magno Alves
**Tags:** recovery, configuração, multi-tenant

## Contexto

A cadência de reengajamento de leads que sumiram é diferente entre os dois templates SaaS:

- **Tiragem Express** (volume + ticket baixo) — agressivo: `[5min, 60min, 180min]` (Protocolo Magno)
- **Consulta Premium** (qualificação + ticket alto) — espaçado: `[1h, 6h, 24h, 72h]`

A `cigana_tarot/` original usa `[2h, 12h, 48h]` — diferente de ambos.

Cada tenant pode querer ajustar dentro do template (ex: "minha base é mais paciente, quero mais tempo"). A questão é: **onde vive essa configuração?**

## Decisão

**Cadência fica em `TenantFlowVariable` por tenant.** Templates inicializam o default; cliente edita no painel "Configurações > Recovery".

Nó visual de recovery no canvas (cliente arrasta a cadência visualmente) **fica pra Fase 6** quando a paridade Manychat (Fase D) for atacada.

## Justificativa

1. **Cliente quer ajustar** — tarólogo conhece a base dele; quer subir/descer cadência sem chamar suporte
2. **Não queremos hardcoded por template** — engessa pra sempre, força redeploy pra mudar
3. **Canvas (opção C) é trabalho desproporcional agora** — Fase D do canvas é 4-6 semanas; resolver isso via DB é 1 dia
4. **`TenantFlowVariable` já existe** (`db/models.py:333`) — infra pronta, zero migração

## Implementação

### Schema

`TenantFlowVariable` com chave canônica:

```python
key: "recovery.cadence_minutes"
value_json: [5, 60, 180]  # array de int em minutos, ordenado
```

Outras chaves relacionadas:

```python
"recovery.max_attempts": 3
"recovery.encerrar_em_dias": 3
"recovery.estilo": "magno_agressivo"  # ou "elaborado_premium"
"recovery.bloquear_se_bot_pausado": true  # já hardcoded; flexibilizar
```

### Defaults por template

Template inicializa essas variáveis ao ser clonado pro tenant (passo 3 do onboarding):

| Variável | Tiragem Express | Consulta Premium |
|---|---|---|
| `recovery.cadence_minutes` | `[5, 60, 180]` | `[60, 360, 1440, 4320]` |
| `recovery.max_attempts` | `3` | `4` |
| `recovery.encerrar_em_dias` | `3` | `14` |
| `recovery.estilo` | `magno_agressivo` | `elaborado_premium` |

### Mudança em `recovery_engine.py`

Hoje (presumido): `SEQUENCIA_RECOVERY = [5, 60, 180]` hardcoded em código.

Depois:
```python
def get_recovery_cadence(tenant_id: str) -> list[int]:
    var = TenantFlowVariable.query.filter_by(
        tenant_id=tenant_id,
        key="recovery.cadence_minutes"
    ).first()
    return var.value_json if var else [5, 60, 180]  # fallback Express
```

### UI no painel

Tela "Configurações > Recovery" simples:
- Input com array editável (chips visuais com minutos)
- Preset: "Restaurar default do template"
- Aviso: "Mudanças aplicam aos novos leads. Leads em recovery ativo seguem a cadência antiga."

## Consequências

**Positivas:**
- Cliente customiza sem chamar suporte
- Sem deploy pra mudança
- Caminho limpo pra Fase 6 (UI no canvas) — basta migrar o input do "Configurações > Recovery" pra um nó visual

**Negativas:**
- Cliente pode configurar mal e prejudicar conversão (ex: cadência muito agressiva → spam → quality rating cai)
  - **Mitigação:** validar no backend (mín 5min entre toques, máx 14 dias entre toques, máx 7 toques)
- Mais um lugar pra configurar (vs hardcoded)

## Alternativas consideradas

1. **A. Hardcoded por template em `recovery_engine.py`** — descartado: engessa, força redeploy
2. **B. `TenantFlowVariable` por tenant (escolhido)** — flexível, simples
3. **C. Nó visual "Recovery" no canvas** — descartado pra agora: depende da Fase D, é trabalho desproporcional. Fica como evolução Fase 6

## Referências

- `recovery_engine.py` — onde a mudança técnica acontece
- `db/models.py:333` — `TenantFlowVariable` (já existe)
- ADR_001 (sem Chatwoot — recovery é nosso, não dele)
- [TEMPLATE_TIRAGEM_EXPRESS](../templates/TEMPLATE_TIRAGEM_EXPRESS.md)
- [TEMPLATE_CONSULTA_PREMIUM](../templates/TEMPLATE_CONSULTA_PREMIUM.md)
