# Migração `config_cliente.py` → multi-tenant

> Audit do `config_cliente.py` (462 linhas) pra mapear o que é configuração GLOBAL do produto vs o que precisa virar configuração POR TENANT. Pré-requisito pro template Premium funcionar como SaaS.

---

## Estado atual: como funciona hoje

`config_cliente.py` carrega ~80 valores de variáveis de ambiente (`.env`) ao importar e expõe um singleton `CONFIG_CLIENTE: dict`. **Tudo single-tenant** — toda a aplicação consome o mesmo dict.

```python
# config_cliente.py
CONFIG_CLIENTE: dict = carregar()  # singleton no boot
```

Consumido em:
- `engine.py` (preços, links, copy guardrails)
- `flows/fase_*` (mídia, áudio, imagem, link de pagamento)
- `recovery_engine.py` (cadência, limites)
- `app.py` (URLs, webhook handlers)

---

## Inventário — o que tem em CONFIG_CLIENTE

### A. Identidade do tarólogo / branding (**→ tenant**)

| Chave | .env source | Exemplo | Migração |
|---|---|---|---|
| `perfil_negocio.slug` | `NEGOCIO_SLUG` | "cigana_piloto" | → `tenant.slug` ou `TenantFlowVariable` |
| `perfil_negocio.nome_exibicao` | `NEGOCIO_NOME` | "Cigana Esmeralda" | → `tenant.display_name` |
| `perfil_negocio.vertical` | `NEGOCIO_VERTICAL` | "consultoria_mistica" | → `tenant.vertical` |
| `perfil_negocio.oferta_resumo` | `NEGOCIO_OFERTA_RESUMO` | "Leitura guiada + ritual..." | → `TenantFlowVariable` |
| `perfil_negocio.publico_hint` | `NEGOCIO_PUBLICO` | "Pessoas em crise afetiva..." | → `TenantFlowVariable` |
| `perfil_negocio.tom_voz` | `NEGOCIO_TOM_VOZ` | "acolhedor_mistico" | → `StudioAgent.body_json` |
| `perfil_negocio.timezone` | `NEGOCIO_TIMEZONE` | "America/Manaus" | → `tenant.timezone` |
| `numero_whatsapp` | `CLIENTE_NUMERO_WHATSAPP` | "+55 92 8497-9419" | → `tenant_whatsapp_credentials.phone_number_id` (via Embedded Signup) |
| `link_prova_social` | `LINK_INSTAGRAM` | "https://instagram.com/..." | → `TenantFlowVariable` |
| `imagem_perfil_instagram` | `CLIENTE_IMAGEM_PERFIL_INSTAGRAM` | URL https | → `TenantFlowVariable` |
| `imagem_altar` | `CLIENTE_IMAGEM_ALTAR` | URL | → `TenantFlowVariable` |

### B. Preços e produtos (**→ tenant**)

| Chave | .env source | Exemplo | Migração |
|---|---|---|---|
| `preco_materiais` | `CLIENTE_PASSO_FE` ou `_PRECO_MATERIAIS` | "65" | → `TenantFlowVariable` |
| `preco_servico` | `CLIENTE_HONORARIO_SUCESSO` ou `_PRECO_SERVICO` | "65" | → `TenantFlowVariable` |
| `preco_original` | `CLIENTE_VALOR_TOTAL` | "360" | → `TenantFlowVariable` |
| `dias_resultado` | `CLIENTE_DIAS_RESULTADO` | "5 a 7" | → `TenantFlowVariable` |
| `link_pagamento` | `LINK_CHECKOUT`/`CAKTO_CHECKOUT_URL` | URL | → `TenantFlowVariable` (gateway-agnostic) |
| `checkout_urls.{130,100,65,...}` | `CHECKOUT_URL_*` | URL por faixa | → `TenantFlowVariable.checkout_urls_by_ticket` |
| `link_downsell` | `CLIENTE_LINK_DOWNSELL` | URL | → `TenantFlowVariable` |
| `depoimentos_urls` | `CLIENTE_DEPOIMENTOS_URLS` | csv URLs | → `TenantFlowVariable` |
| `cakto.client_id` | `CAKTO_CLIENT_ID` | string | → `TenantFlowSecret` (cifrado) |
| `cakto.client_secret` | `CAKTO_CLIENT_SECRET` | string | → `TenantFlowSecret` |
| `cakto.webhook_secret` | `CAKTO_WEBHOOK_SECRET` | string | → `TenantFlowSecret` |
| `cakto.offer_id` / `_slug` / `_id_map.*` | `CAKTO_OFFER_*` | string | → `TenantFlowVariable` |

**Stripe equivalents** (por [ADR_003](adr/ADR_003_stripe_payments.md), virão na migração):
- `stripe.publishable_key` → `TenantFlowVariable`
- `stripe.secret_key` → `TenantFlowSecret`
- `stripe.webhook_secret` → `TenantFlowSecret`
- `stripe.connect_account_id` → `tenant_stripe_connect.account_id`

### C. Mídia e áudios (**→ tenant** ou storage)

| Chave | .env source | Migração |
|---|---|---|
| `audio_bloco{3,4,5,6,7}_*` (~20 chaves) | `CLIENTE_AUDIO_BLOCO*` | → `TenantFlowVariable` (URLs) ou Supabase Storage por tenant |
| `audio_bloco4_d{1,2,3}` | `CLIENTE_AUDIO_BLOCO4_D{1,2,3}` | → idem |
| `link_pagamento_b5` | `LINK_PAGAMENTO_B5` | → `TenantFlowVariable` |

**Recomendação:** áudios viram arquivos no bucket `tenant-media-{tenant_id}/audio/blocoN.ogg` (ver [ADR_004](adr/ADR_004_supabase_storage.md)). `TenantFlowVariable` aponta apenas pra URL.

### D. Copy/persona (**→ StudioAgent**)

| Chave | .env source | Migração |
|---|---|---|
| `pontes_copy.*` (6 chaves: preco_fora_da_ordem, desconfianca, etc) | `PONTE_*` ou defaults | → `StudioAgentVersion.body_json.bridges` |
| `copy_guardrails.tom_evitar` | `COPY_EVITAR_TOM` | → `StudioAgentVersion.body_json.restrictions` |
| `copy_guardrails.nao_prometer` | `COPY_NAO_PROMETER` | → `StudioAgentVersion.body_json.restrictions` |

### E. IA budget e modelos (**→ tenant** ou global, depender)

| Chave | .env source | Migração sugerida |
|---|---|---|
| `modelo_ia` | `CLIENTE_MODELO_IA` (default `gemini-2.5-flash`) | **global** (pra controlar custo na plataforma); **tenant** se quiser modelo melhor como upsell |
| `modelo_stt` | `CLIENTE_MODELO_STT` | **global** |
| `tts_ativo` | `CLIENTE_TTS_ATIVO` | **tenant** (feature por plano: Pro/Premium) |
| `ia_economia.orcamento_tokens_por_lead` | `IA_ORCAMENTO_TOKENS_POR_LEAD` | **tenant** (limite por plano) |
| `ia_economia.max_tentativas_ia_por_node` | `IA_MAX_TENTATIVAS_POR_NODE` | **global** |
| `ia_economia.max_output_tokens_por_node.*` | `IA_MAX_OUTPUT_NODE*` (10 chaves) | **global** (parte do produto, não cliente) |

### F. Operacional / motor (**→ global**)

| Chave | .env source | Razão |
|---|---|---|
| `recovery_max_leads_por_ciclo` | `RECOVERY_MAX_LEADS_POR_CICLO` | global — proteção da plataforma |
| `inbox_max_concorrencia_processamento` | `INBOX_MAX_CONCORRENCIA_PROCESSAMENTO` | global |
| `inbox_max_retries_busy` | `INBOX_MAX_RETRIES_BUSY` | global |
| `inbox_max_tamanho_fila_por_lead` | `INBOX_MAX_TAMANHO_FILA_POR_LEAD` | global |
| `inbox_silence_seconds` | `INBOX_SILENCE_SECONDS` | global |
| `inbox_after_text_grace_seconds` | `INBOX_AFTER_TEXT_GRACE_SECONDS` | global |
| `node_exec_sla_warn_seconds` | `NODE_EXEC_SLA_WARN_SECONDS` | global |
| `whatsapp_typing_enabled` | `WHATSAPP_TYPING_ENABLED` | global |
| `node6_pausa_leitura_*` (4 chaves) | `NODE6_PAUSA_LEITURA_*_SEGUNDOS` | **tenant** (parte da experiência da cigana) |

### G. Compliance (**→ global** com override por tenant)

| Chave | Migração |
|---|---|
| `compliance.respeitar_opt_out` | global (não-negociável) |
| `compliance.limite_recovery_ciclos_sugerido` | tenant (parte do template; ver [ADR_005](adr/ADR_005_recovery_cadence_per_tenant.md)) |
| `compliance.intervalo_min_entre_recovery_min` | tenant idem |

### H. Funil estático "meu mistério" (**→ deprecated**)

| Chave | Razão |
|---|---|
| `funil_estatico_meu_misterio_ativo` | Legado do cliente piloto. Nova plataforma: cada tenant escolhe template no onboarding (Express/Premium/em branco). Manter durante migração, deprecar depois |
| `ia_motor_desligada` | idem |
| `funil_entrada_inicial` | idem |
| Todos `static_meumisterio_*` | idem |

---

## Plano de migração faseado

### Fase 1 — Configuração read-only por tenant (preparação)

- [ ] Criar `api/tenant_config.py:get_tenant_config(tenant_id) -> dict` que devolve **mesma forma** do `CONFIG_CLIENTE` mas resolvido do DB
- [ ] Implementação inicial: read-through cache; busca em `TenantFlowVariable`/`TenantFlowSecret`/`StudioAgent`/`tenant_whatsapp_credentials`; fallback pra valores de `CONFIG_CLIENTE` (do .env) se chave faltar
- [ ] **Não substitui `CONFIG_CLIENTE` ainda** — coexiste

**Esforço:** 2 dias

### Fase 2 — Migrar consumidores um por um

Trocar `from config_cliente import CONFIG_CLIENTE` por `from api.tenant_config import get_tenant_config(self.tenant_id)` nos seguintes consumidores em ordem:

| Ordem | Consumidor | Risco |
|---|---|---|
| 1 | `recovery_engine.py` | baixo (já tem `tenant_id`) |
| 2 | `flows/fase_*` (chamado pelo engine) | médio — passar `tenant_id` via ctx |
| 3 | `engine.py` | médio — Motor já tem `self.tenant_id` |
| 4 | `app.py` (handlers) | alto — superficie grande, fazer por seção |

**Esforço:** ~3 dias por consumidor (12 dias total)

### Fase 3 — Wizard do onboarding popula DB

UI do wizard (passos 1-3 do [ONBOARDING_FLOW.md](ONBOARDING_FLOW.md)) escreve em:
- `StudioAgent` + `StudioAgentVersion` (passo 1)
- `TenantFlowSecret` + `TenantFlowVariable` (passo 2)
- `FlowBlueprint` (passo 3)

**Esforço:** 3 dias (depende da decisão de frontend)

### Fase 4 — Deprecar `CONFIG_CLIENTE` global

- [ ] `config_cliente.py` deixa de carregar no import; vira só lib de helpers (`_normalizar_url_https`, `_obter_limpo`)
- [ ] `.env` mantém só configuração GLOBAL da plataforma (Gemini API key, Sentry DSN, etc) — não específica de cliente
- [ ] CI bloqueia novo uso de `CONFIG_CLIENTE` (lint rule)

**Esforço:** 1 dia + cleanup

---

## Riscos e mitigações

1. **Performance**: `get_tenant_config(tenant_id)` é chamada toda hora — sem cache, vira N+1. **Mitigação:** cache in-memory por processo (TTL 60s) com invalidação via Redis pubsub quando tenant edita config
2. **Compat com funil estático**: clientes legados que rodam funil estático "meu mistério" precisam de transição manual. **Mitigação:** criar tenant especial `legacy_meu_misterio` que mantém todos os valores antigos
3. **Secrets em DB**: `TenantFlowSecret` deve usar criptografia simétrica (campo `value_cipher`) com chave mestra em env var. Hoje o modelo já tem o campo; falta a key derivation em produção
4. **`CONFIG_CLIENTE` é dict mutável** — código pode mexer e cachear referências. **Mitigação:** `get_tenant_config` retorna `MappingProxyType` (somente leitura)

---

## Decisões pendentes

- [ ] Definir formato exato do `TenantFlowVariable.value_json` pra `checkout_urls_by_ticket`, `audio_blocoN`, etc — schema vs flat
- [ ] Onde guardar Stripe Connect KYC status — novo modelo `tenant_stripe_connect` (já mencionado em [ADR_003](adr/ADR_003_stripe_payments.md)) ou campo em tabela existente
- [ ] Estratégia de migração pra clientes que estão hoje em produção single-tenant: criar tenant `default` que herda os valores do `.env` atual e só re-lê do DB depois

---

## Referências

- `config_cliente.py` (singleton `CONFIG_CLIENTE`)
- `db/models.py` — `StudioAgent`, `TenantFlowVariable`, `TenantFlowSecret`
- [ADR_003](adr/ADR_003_stripe_payments.md) — Stripe + Connect
- [ADR_004](adr/ADR_004_supabase_storage.md) — mídia em Supabase Storage
- [ADR_005](adr/ADR_005_recovery_cadence_per_tenant.md) — cadência via TenantFlowVariable
- [ONBOARDING_FLOW.md](ONBOARDING_FLOW.md) — wizard que popula tudo isso
