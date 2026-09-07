# SaaS Gap Analysis — o que existe vs o que falta

> Status snapshot pra navegar o roadmap. Atualizar quando fechar uma fase.

Legenda: ✅ pronto | ⚠️ parcial | ❌ ausente

---

## 1. Multi-tenancy (Banco de dados)

| Item | Status | Onde está | O que falta |
|---|---|---|---|
| `tenant_id` em `Lead` | ✅ | `db/models.py:26` | — |
| `tenant_id` em `StudioAgent` / `FlowBlueprint` | ✅ | `db/models.py:177, 228` | — |
| `tenant_id` em `WhatsAppInboundReceipt` | ✅ | `db/models.py:148` | — |
| `tenant_id` em `Mensagem` | ❌ | herda via `lead_id` | adicionar coluna direta (vazamento entre tenants) |
| `tenant_id` em `EventoAudit` | ❌ | herda via `lead_id` | adicionar coluna direta |
| `tenant_id` em `AudioCache` | ❌ | sem coluna | adicionar coluna |
| Row-Level Security no Postgres | ❌ | — | habilitar policies (`SET app.tenant_id`) |
| Postgres em produção | ❌ | usando SQLite (`cigana.db`) | migrar |
| Suite de testes de isolamento | ❌ | — | escrever testes que CI bloqueie merge |

**Estimativa:** 2 semanas

---

## 2. Canvas / Flow Builder

| Item | Status | Onde está |
|---|---|---|
| Desenhar nós e ligar | ✅ | `dashboard.html` (Flow Builder) |
| Validação + compile + simulação | ✅ | `flow_builder_runtime.py` |
| Versionamento de blueprint | ✅ | `FlowBlueprintVersion` |
| Publicar blueprint por tenant | ✅ | `FlowPublish` |
| Executar fluxo num lead | ✅ | `flow_executor.py` |
| Ramos condicionais (B1) | ✅ | `flow_graph_walk.py` |
| Divisão A/B determinística (B2) | ✅ | — |
| Variáveis de fluxo (B3) | ✅ | — |
| Anotações internas (B4) | ✅ | — |
| HTTP request com flag de segurança (C1) | ✅ | — |
| LLM real (Gemini) no nó (C2) | ✅ | — |
| `motor_ref` com allowlist (C3) | ✅ | `flow_motor_ref.py` |
| **Inbound governado pelo blueprint (Fase D)** | ❌ | — pendente |
| Marketplace de templates | ❌ | — |
| Tags / audiências / broadcast | ❌ | — |

**Estimativa:** Fase D = 4-6 semanas; Marketplace = 1 semana

---

## 3. IA / Agente

| Item | Status | Onde está |
|---|---|---|
| `StudioAgent` (persona com versionamento) | ✅ | `db/models.py:174` |
| Intent classifier | ✅ | `ai/intent_classifier.py` |
| Sentiment analyzer | ✅ | `ai/sentiment_analyzer.py` |
| Response validator | ✅ | `ai/response_validator.py` |
| Recovery engine | ✅ | `ai/recovery_engine.py` |
| Personalizer | ✅ | `personalizer.py` |
| Template registry | ✅ | `ai/template_registry.py` |
| Stage intelligence | ✅ | `ai/stage_intelligence.py` |
| Context compressor | ✅ | `ai/context_compressor.py` |
| Conhecimento (knowledge base) | ✅ | `ai/knowledge.py` |
| 3 abas no dashboard (personalidade / conhecimento / restrições) | ⚠️ | UI existe (linhas 8662-8715); ligação ao `tenant_id` real falta |

**Estimativa:** integração ao multi-tenant = 1 semana

---

## 4. Inbox / atendimento humano

| Item | Status | O que falta |
|---|---|---|
| Storage de mensagens | ✅ | `Mensagem` model |
| Campo `bot_pausado` no lead (takeover) | ✅ | `Lead.bot_pausado` |
| UI de inbox (lista de conversas) | ❌ | construir |
| UI de conversa individual | ❌ | construir |
| Botão "humano assume" | ❌ | construir |
| Notificação realtime (WebSocket / SSE) | ❌ | construir |
| Storage de mídia persistente | ⚠️ | URL Meta expira em 5min — verificar se já tem download |
| Filtros e busca | ❌ | — |

**Estimativa:** 2-3 semanas

---

## 5. Onboarding e billing SaaS

| Item | Status |
|---|---|
| Cadastro / login | ❌ |
| Wizard de 4 passos | ❌ |
| Stripe Subscriptions (assinatura SaaS) | ❌ |
| Stripe Connect Express (end-user split) | ❌ |
| Bloqueio por inadimplência | ❌ |
| Provisionamento automático do tenant | ❌ |

**Estimativa:** 3-4 semanas

---

## 6. Integração WhatsApp

| Item | Status | Onde |
|---|---|---|
| Webhook Meta direto | ✅ | `app.py:3674` |
| Envio Cloud API | ✅ | `api/whatsapp_api.py` |
| Idempotência (`wamid`) | ✅ | `WhatsAppInboundReceipt` |
| Validação X-Hub-Signature | ⚠️ | verificar implementação |
| Roteamento `phone_number_id` → tenant | ❌ | adicionar lookup |
| Embedded Signup | ❌ | — |
| App Review Meta | ❌ | — |
| Quality Rating monitor | ❌ | — |

**Estimativa:** roteamento = 3 dias; Embedded Signup = 4-6 semanas; App Review = 1-2 meses externos

---

## 7. Operacional / observabilidade

| Item | Status |
|---|---|
| Sentry | ✅ `requirements.txt` |
| Logs estruturados | ⚠️ verificar |
| Metering por tenant (custo Gemini / Stripe / storage) | ❌ |
| Backup por tenant | ❌ |
| LGPD: política, DPA, retenção | ❌ |
| Termos de uso (você ↔ tenant ↔ end-user) | ❌ |

**Estimativa:** 2 semanas técnico + jurídico em paralelo

---

## 8. Dívida técnica bloqueante

| Item | Severidade | Impacto |
|---|---|---|
| `app.py` com 172k linhas | 🔴 alta | Qualquer feature nova custa 3x |
| Pasta `cigana_tarot/` paralela | 🟡 média | Resolvido pela decisão de produto (referência apenas) |
| `Mensagem` sem `tenant_id` | 🔴 alta | Vaza dados entre tarólogos em multi-tenant |
| Sem CI/CD documentado | ⚠️ | verificar `.github/` |

---

## Resumo executivo

**Pronto pra produção single-tenant:** ✅ ~80%
**Pronto pra produção SaaS multi-tenant:** ⚠️ ~40%

**Maiores gaps por esforço:**
1. Frontend de SaaS (login + onboarding + inbox + métricas) — ~6-8 semanas
2. Embedded Signup + App Review Meta — ~2-3 meses
3. Stripe (assinatura + Connect) — ~3-4 semanas
4. Multi-tenant rígido + RLS — ~2 semanas
5. Refactor `app.py` — ~2-3 semanas

**Total realista pra v1 SaaS vendável:** 4-5 meses com 1 dev fulltime.

**Caminho de menor risco:** Modo "done-for-you" manual durante 2 meses pra validar economia, depois investir em self-service com confiança.
