# Gap Analysis — `engine.py` × `cigana_tarot/`

> Auditoria comportamento-por-comportamento dos 10 workflows n8n vs implementação Python. Base pra decidir o que falta portar antes do template "Tiragem Express" funcionar end-to-end no SaaS.
>
> **Não modificar `cigana_tarot/`**. Esta análise é só pra extrair o trabalho a fazer no `projeto_cigana/`.

---

## Sumário executivo

Dos **48 comportamentos** mapeados nos 10 workflows da `cigana_tarot/`:

| Status | Qtd | % | Significado |
|---|---|---|---|
| ✅ Implementado | 15 | 31% | Já funciona em Python, equivalente direto |
| ⚠️ Parcial | 22 | 46% | Existe parte; ou é diferente por design (ex: WhatsApp direto vs Chatwoot) |
| ❌ Ausente | 11 | 23% | Precisa ser construído |

**Veredito:** consolidação é **viável** sem reescrita grande. Os ⚠️ parciais são em maioria diferenças arquiteturais já decididas (sem Chatwoot, WhatsApp direto, Postgres em vez de Redis). Os ❌ ausentes reais que **bloqueiam** o template "Tiragem Express" são poucos e bem delimitados.

**Estimativa pra fechar o gap real:** **2-3 semanas** focando só no que falta de fato.

---

## ❌ Gaps reais que bloqueiam o template "Tiragem Express"

Lista priorizada do que precisa ser construído pra um cliente novo escolher Tiragem Express e ter funil funcionando end-to-end.

### 🔴 Crítico — sem isso o template não funciona

| # | Comportamento | Origem | Onde implementar | Estimativa |
|---|---|---|---|---|
| ✅ G1 | **Sorteio de 78 cartas (Marselha)** — embaralhar, sortear 3, retornar nomes pra IA | `03_zara_sorteio_cartas.json` | `flows/tarot/cartas.py` + `tests/test_tarot_cartas.py` (25 testes passando) | ~~2 dias~~ feito em 1h |
| ⚠️ G2 | **Envio de imagens das cartas** — 3 imagens em sequência com pausa de 2s | `03_zara_sorteio_cartas.json` | Código pronto: `flows/tarot/envio.py` (`enviar_tres_cartas`, `sortear_e_enviar_3_cartas`) + 10 testes; **pendente do usuário**: subir 79 JPGs via `scripts/upload_marselha_storage.py` (ver [MARSELHA_ASSETS.md](MARSELHA_ASSETS.md)) | código feito em 1h |
| ⚠️ G3 | **Envio do baralho fechado (foto ritualística)** | `02_zara_enviar_baralho.json` | Função pronta: `flows/tarot/envio.py:enviar_baralho_fechado()` + 2 testes; **pendente**: subir `baralho_fechado.jpg` (junto com G2) e criar nó no blueprint (faz parte de G5b) | código feito |
| ⚠️ G4 | **Primitivos de webhook: signature + idempotência** | `05_zara_webhook_pagamento.json` | Pronto: novo modelo `PaymentEventReceipt` em `db/models.py`; `api/payments/idempotency.py` (`claim_payment_event`); `api/payments/signatures.py` (Cakto + Stripe HMAC com anti-replay); 24 testes passando. **Pendente em G5a**: wiring no app.py atual (substitui handler legado em `app.py:3815`) | feito em 1.5h |
| ⚠️ G5a | **Dispatch pra blueprint `post_payment`** ([ADR_006](adr/ADR_006_post_payment_hibrido.md)) | derivado de `05` | Pronto: `api/payments/dispatch.py:dispatch_post_payment_blueprint()` — thread daemon, isolamento multi-tenant estrito, exceção capturada, 12 testes. **Pendente em G5b**: ligação da lista de Acao retornada na fila do motor (`_enfileirar_acoes_pendente` é hoje stub) | feito em 1h |
| ✅ G5b | **Blueprints semente + integração com fila do motor** | `05` + persona Zara | Seeds: `flows/post_payment/seeds/post_payment_{express,premium}.json` + loader. **Integração engine.py**: `Engine._compile_post_payment_blueprint` (Opção A) — `engine.py:911` agora tenta blueprint primeiro, fallback ao `_executar_node`. 25 testes (17 seeds + 8 engine hook). | seeds 1h + engine hook 1h |
| ✅ G5c | **Validador de blueprint tipo `post_payment`** | derivado de [ADR_006](adr/ADR_006_post_payment_hibrido.md) | `flows/post_payment/validator.py:validate_post_payment_blueprint()` — valida trigger event, mensagem em ≤60s (Dijkstra c/ delays), warning sem acao node; 24 testes. **Pendente em G5b/F3**: chamar este validador no endpoint de publish | feito em 1h |

### 🟡 Importante — não bloqueia mas é parte da experiência

| # | Comportamento | Origem | Onde implementar | Estimativa |
|---|---|---|---|---|
| G6 | **Comando `/reset`** — admin apaga histórico do lead pra testar | `01_zara_principal.json` | Endpoint admin `POST /api/admin/leads/{id}/reset` + UI no painel | 1 dia |
| G7 | **Comando `/teste`** — coloca lead em "modo teste" (etiqueta) | `01_zara_principal.json` | Flag `Lead.test_mode` + filtro de exclusão das métricas reais | 0.5 dia |
| G8 | **Resumo automático da conversa** (pra escalonamento humano) | `08_zara_escalar_humano.json` | Função `engine.py:resumir_conversa(lead_id) -> str` chamando Gemini com últimos N turnos | 1 dia |
| G9 | **Alertas internos pra equipe** (notifica múltiplos canais quando escala) | `08_zara_escalar_humano.json` | `tenant_settings.alert_channels` (lista de telefones/emails); `engine.py` envia notificação em todos | 1 dia |

### 🟢 Nice to have — pode esperar

| # | Comportamento | Origem | Estimativa |
|---|---|---|---|
| G10 | Validação `on_whatsapp` antes de enviar (verifica se número existe no WhatsApp) | `06_zara_buscar_contato.json` | 0.5 dia |
| G11 | Atributos customizados Cakto (cakto_id_cobranca, cakto_status, total_gasto) | `00_zara_setup.json` | 1 dia |

**Total crítico (G1-G5c):** ~10.5 dias
**Total importante (G6-G9):** ~3.5 dias
**Total geral:** ~14 dias úteis (~3 semanas)

---

## ⚠️ "Parciais" que NÃO são gap real (diferenças arquiteturais já decididas)

Estes aparecem como "parcial" no relatório mas **não precisam ser portados** porque o `projeto_cigana/` resolveu a mesma coisa de outro jeito (decisão consciente):

| Comportamento na cigana_tarot | Equivalente Python | Por que não é gap |
|---|---|---|
| Webhook Chatwoot | Webhook Meta direto (`app.py:3674`) | [ADR_001](adr/ADR_001_sem_chatwoot.md) — sem Chatwoot |
| Etiquetas Chatwoot (agente-off, lead-quente, etc) | `Lead.bot_pausado`, `Lead.tags` (JSON) | Mesmo papel, modelo diferente |
| Histórico em Redis | Postgres (`Mensagem`) + `context_compressor.py` | Postgres é fonte da verdade; Redis pode entrar como cache se preciso |
| `estado_funil` (NOVO, PERGUNTA_1, OFERTA_VISTA…) | `Lead.node_atual` | Mesmo conceito, nome diferente. Ver mapa abaixo |
| Sub-workflow `06_buscar_contato` | `Lead` é encontrado por `(tenant_id, telefone)` direto no DB | Não precisa busca dinâmica — o lead já existe |
| Sub-workflow `07_quebrar_mensagens` | `engine.py:_quebrar_baloes()` + `copy_sanitizer.py:delay_entre_baloes()` | ✅ já implementado |
| Cadência recovery `[2h, 12h, 48h]` | `recovery_engine.py` usa `[5min, 60min, 180min]` (Protocolo Magno) | Diferente por design — Python é mais agressivo. **Sugestão**: parametrizar via `template` no tenant (Express usa Magno, Premium usa cadência mais espaçada) |

### Mapa estado_funil → node_atual

Pra evitar refactor desnecessário, sugerir aliases no template:

| n8n estado_funil | Python node_atual | Significado |
|---|---|---|
| NOVO | `1_apresentacao` | Lead chegou, primeira mensagem |
| PERGUNTA_1 | `2_investigacao` | Primeira pergunta investigativa |
| PERGUNTA_2 | `3_loop_aberto` | Segunda pergunta com gancho de oferta |
| OFERTA_VISTA | `8_oferta_principal` | Lead viu a oferta R$19,90 |
| ASSINANTE | `convertido=True` + recorrencia | Cliente recorrente |
| POS_COMPRA_AVULSO | `9_entrega` | Pagou, recebendo entrega |
| INATIVA_7D | `recovery_stage>=3` | Recovery encerrado |

---

## ✅ Já implementado (15 comportamentos)

Confirmados pela auditoria — equivalência direta n8n → Python:

| Comportamento | Local |
|---|---|
| Setup de tabelas (via ORM) | `db/models.py` |
| Webhook WhatsApp Meta | `app.py:3674` |
| Extração de dados de mensagem inbound | `app.py` (inbound_message) |
| Resolução de URL de checkout (Cakto) | `api/cakto_api.py:130-154` |
| Quebra de balões com IA | `engine.py:_quebrar_baloes()` |
| Cálculo de delay entre balões (humanização) | `copy_sanitizer.py:670+` |
| Cron de recovery | `recovery_engine.py:90+` |
| Critérios de seleção de leads pendentes | `recovery_engine.py:200+` |
| Geração de copy de recovery por estágio | `recovery_engine.py:300+` |
| Envio de mensagem WhatsApp | `recovery_engine.py:640+` |
| Bloqueio de recovery via `bot_pausado` | `recovery_engine.py` (check) |
| Análise de sentimento | `ai/sentiment_analyzer.py` |
| Validação de resposta IA | `ai/response_validator.py` |
| Personalização por arquétipo | `personalizer.py` |
| Compressão de contexto histórico | `ai/context_compressor.py` |

---

## 🎁 O que o `projeto_cigana/` tem a MAIS que a `cigana_tarot/` não tem

Capacidades únicas do Python que **viram diferencial competitivo** dos templates SaaS:

1. **Multi-tenant nativo** (`tenant_context.py`) — n8n é single-tenant
2. **Canvas visual / Flow Builder** (`flow_builder_runtime.py` + `flow_executor.py`) — n8n é canvas externo, aqui é nativo
3. **Identificação de arquétipo** (`personalizer.py`) — classifica lead em "Mártir", "Cético", "Ansioso" etc; adapta toda copy
4. **Fases estruturadas 1-4** (`flows/fase_*`) — preflight → saudação → leitura → oferta → entrega; nodes numerados, recuperáveis
5. **TTS / Audio Engine** (`tts/audio_engine.py`) — geração de voz Gemini com pacing dramático e cache
6. **Intent classifier** (`ai/intent_classifier.py`) — roteia por amor / trabalho / prosperidade
7. **Stage intelligence** (`ai/stage_intelligence.py`) — enriquece contexto por fase
8. **Response validator** (`ai/response_validator.py`) — bloqueia output que prometa cura/garantia
9. **Recovery Engine SUPREME v4.3** (`recovery_engine.py`) — multimodal (áudio na R1), locks anti-colisão, max 120 leads/ciclo
10. **Atomic updates** (`reliability/lead_metadata_atomic.py`) — patches em `metadata_json` sem race condition
11. **Funnel audit & analytics** (`analytics/funnel_audit.py`) — transições de nó, custos IA, KPIs
12. **Copy sanitizer 1000+ linhas** (`copy_sanitizer.py`) — limpeza, compactação URL, detecção de cortes IA, fatias por ritmo celular
13. **Modelo Lead robusto** (`db/models.py`) — 20+ campos com índices, soft deletes, event audit
14. **API Flow Platform** (`api/flow_platform.py`) — expõe funções motor_ref pro canvas (extensibilidade)
15. **Estudio de versionamento de Agente** (`StudioAgent` + `StudioAgentVersion` + `StudioPublish`) — n8n não versiona

---

## Plano de ação recomendado (Fase 2 do roadmap)

Sequência de execução pra fechar o gap em ~2-3 semanas:

### Semana 1 — Tarot e mídias (G1, G2, G3)

- [ ] **Dia 1-2**: criar `flows/tarot/cartas.py` com array de 78 cartas Marselha, função `sortear_3_cartas()`, testes
- [ ] **Dia 3**: subir 79 imagens (78 cartas + 1 baralho fechado) em Supabase Storage; URLs canônicas
- [ ] **Dia 4**: integrar nó `motor_ref` no canvas → função Python que envia 3 imagens com pausa
- [ ] **Dia 5**: nó "envia baralho fechado" no blueprint Tiragem Express; teste end-to-end manual

### Semana 2 — Cakto/Stripe webhook e dispatch (G4, G5a)

- [ ] **Dia 6-7** (G4): completar `app.py:/webhook/cakto` + criar `app.py:/webhook/stripe`; validação de signature; novo modelo `PaymentEventReceipt`
- [ ] **Dia 8-9** (G5a): após validação, dispatch `flow_executor.execute_blueprint(slug="post_payment")`
- [ ] **Dia 10** (G5c): validador de blueprint `post_payment` no `flow_builder_runtime.py`

### Semana 3 — Blueprints pós-pagamento + polish (G5b, G6-G9)

- [ ] **Dia 11-12** (G5b): desenhar `post_payment_express` e `post_payment_premium` no canvas; clonar no onboarding junto com template principal
- [ ] **Dia 13** (G6, G7): comandos `/reset` e `/teste` (admin only)
- [ ] **Dia 14** (G8, G9): resumo automático + alertas internos
- [ ] **Dia 15**: documentar templates completos, checklist de QA, teste com 1 lead real ponta-a-ponta

---

## Decisões de design — 3 fechadas, 1 ainda em aberto

### ✅ Fechadas (2026-04-28)

1. **Storage de mídia** → **Supabase Storage** no MVP, plano de migração pra Cloudflare R2 quando egress doer ([ADR_004](adr/ADR_004_supabase_storage.md))
2. **Gateway no template Tiragem Express** → **Stripe default + Cakto legado** por tenant; blueprint é gateway-agnóstico ([ADR_003 — seção Coexistência com Cakto](adr/ADR_003_stripe_payments.md#coexistência-com-cakto-legado-transição))
3. **Cadência de recovery** → **`TenantFlowVariable` por tenant**; templates inicializam defaults; cliente edita no painel "Configurações > Recovery" ([ADR_005](adr/ADR_005_recovery_cadence_per_tenant.md))

### ✅ Decisão #4 fechada (2026-04-28)

4. **Sub-fluxo de entrega pós-pagamento** → **Híbrido** ([ADR_006](adr/ADR_006_post_payment_hibrido.md)):
   - Python webhook handler faz validação + idempotência + audit (não-editável)
   - Em seguida dispara blueprint `post_payment` editável pelo cliente no canvas
   - Templates inicializam blueprints semente (`post_payment_express`, `post_payment_premium`)
   - Validador rejeita publish se faltarem nós obrigatórios
   - **Impacto:** G5 cresce de 2 → 5 dias; Fase 2 vai de 2-3 → ~3 semanas

---

## Referências cruzadas

- [SAAS_ROADMAP](SAAS_ROADMAP.md) — onde esse gap se encaixa (Fase 2)
- [SAAS_GAP_ANALYSIS](SAAS_GAP_ANALYSIS.md) — visão geral de gaps SaaS (este doc é o detalhe da seção "Canvas / Flow Builder")
- [TEMPLATE_TIRAGEM_EXPRESS](templates/TEMPLATE_TIRAGEM_EXPRESS.md) — o que o template promete entregar
- [ADR_001](adr/ADR_001_sem_chatwoot.md) — explica por que tantos itens "parciais" são na verdade decisões arquiteturais
