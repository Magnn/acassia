# SaaS Roadmap — Plataforma de Agentes Espirituais via WhatsApp

> Documento mestre. Consolida visão de produto, decisões arquiteturais e roteiro de execução. Revisar a cada fechamento de fase.

---

## Visão de produto

Plataforma SaaS multi-tenant onde tarólogos, ciganas, mentores espirituais e coaches conectam o próprio número de WhatsApp e configuram um agente de IA que faz leituras, qualifica leads, vende ofertas e mantém recorrência — 24/7, sem precisar atender manualmente.

**Problema:** profissionais espirituais perdem 70%+ dos leads que chegam por WhatsApp porque atendem manualmente, em horário comercial, sem follow-up estruturado.

**Solução:** agente IA com persona configurável, funil visual no canvas, métricas isoladas por cliente, WhatsApp oficial.

**Diferencial vs Manychat / ManyMessage / Botpress:**
- IA nativa pra leitura espiritual (não bot genérico)
- Templates de funil com DNA testado (Tiragem Express R$19,90 e Consulta Premium R$197+)
- Brasil-first: pagamentos em Real, copy em PT-BR, integrações nacionais
- Setup em minutos via Embedded Signup oficial da Meta

---

## Decisões arquiteturais

| # | Decisão | ADR |
|---|---|---|
| 1 | Sem Chatwoot — inbox próprio | [ADR_001](adr/ADR_001_sem_chatwoot.md) |
| 2 | WhatsApp Cloud API oficial via Embedded Signup; sem QR Code | [ADR_002](adr/ADR_002_whatsapp_oficial_via_embedded_signup.md) |
| 3 | Stripe pra assinatura SaaS + Stripe Connect Express pra split end-user; Cakto coexiste como legado | [ADR_003](adr/ADR_003_stripe_payments.md) |
| 4 | Supabase Storage pra mídia (com plano de migração pra Cloudflare R2 em escala) | [ADR_004](adr/ADR_004_supabase_storage.md) |
| 5 | Cadência de recovery configurável por tenant via `TenantFlowVariable` | [ADR_005](adr/ADR_005_recovery_cadence_per_tenant.md) |
| 6 | Pós-pagamento híbrido: Python core + blueprint `post_payment` editável | [ADR_006](adr/ADR_006_post_payment_hibrido.md) |
| 7 | Postgres (Supabase) — descontinuar SQLite | ver [SAAS_GAP_ANALYSIS](SAAS_GAP_ANALYSIS.md) |
| 8 | n8n descontinuado — orquestração 100% Python via flow_executor | ver [SAAS_GAP_ANALYSIS](SAAS_GAP_ANALYSIS.md) |
| 9 | Pasta `cigana_tarot/` é referência histórica, não roda em produção | — |

---

## Fluxo do produto (resumo)

Detalhe completo em [ONBOARDING_FLOW.md](ONBOARDING_FLOW.md).

```
[Signup] → [Wizard 4 passos] → [Painel: Inbox / Canvas / Agente IA / Métricas]
              │
              ├─ 1. Persona (nome, tom, restrições)
              ├─ 2. Oferta (produto, preço, Stripe Connect)
              ├─ 3. Template (Express / Premium / em branco)
              └─ 4. WhatsApp (Embedded Signup)
```

Templates disponíveis no passo 3:
- [TEMPLATE_TIRAGEM_EXPRESS](templates/TEMPLATE_TIRAGEM_EXPRESS.md) — alto volume, ticket baixo, recorrência
- [TEMPLATE_CONSULTA_PREMIUM](templates/TEMPLATE_CONSULTA_PREMIUM.md) — ticket alto, conversão profunda

---

## Roadmap por fase

### Fase 0 — Decisões e fundação (1 semana)
- [x] Decidir sem Chatwoot
- [x] Decidir Stripe + Embedded Signup
- [ ] Quebrar `app.py` (172k linhas) em módulos coerentes — dívida técnica bloqueante
- **Critério de feito:** 5 módulos top-level documentados, `app.py` com < 30k linhas

### Fase 1 — Multi-tenant rígido (2 semanas)
- [ ] Migrar SQLite → Postgres (Supabase)
- [ ] Adicionar `tenant_id` em `Mensagem`, `EventoAudit`, `AudioCache`
- [ ] Habilitar Row-Level Security
- [ ] Suite de testes de isolamento bloqueando deploy
- **Critério de feito:** teste E2E com 3 tenants confirma zero vazamento

### Fase 2 — Templates e Canvas (2-3 semanas)
- [ ] Criar 2 blueprints semente (Tiragem Express + Consulta Premium)
- [ ] Marketplace de templates no onboarding
- [ ] Mapear gap n8n (`cigana_tarot/`) → Python já existente em `engine.py`
- [ ] Implementar comportamentos faltantes (sorteio cartas, recovery 5min, quebra balões)
- **Critério de feito:** cliente novo escolhe template e tem agente respondendo em 2 minutos

### Fase 3 — UI mínima de SaaS (3-4 semanas)
- [x] Login / cadastro com tenant isolado (`api/saas/auth.py` + 32 testes)
- [x] Wizard de onboarding 4 passos: persona → oferta → template → WhatsApp (`api/saas/onboarding.py` + 29 testes)
- [x] Stripe Subscriptions (cobrança SaaS via Checkout + webhook + Customer Portal) — `api/saas/billing.py` + `api/payments/stripe_webhook.py` + 30 testes
- [x] Stripe Connect Express (onboarding KYC do tarólogo pra split) — `api/saas/connect.py` + 6 testes
- [x] Inbox com takeover humano — `api/saas/inbox.py` + 9 testes
- [x] Settings UI (recovery + status WhatsApp + status Stripe) — `api/saas/settings.py` + 7 testes
- [x] Métricas básicas por tenant — `api/saas/metrics.py` + 5 testes
- **Critério de feito:** 3 betas pagantes operando self-service

### Fase 4 — Pagamento end-user com Stripe Connect (2 semanas)
- [ ] Stripe Connect Express por tenant
- [ ] Split automático (% plataforma + restante pro tenant)
- [ ] Webhook de confirmação → libera entrega da consulta
- **Critério de feito:** tenant beta vende e recebe payout sem intervenção

### Fase 5 — Embedded Signup + escala (2-3 meses, paralelo)
- [ ] Submeter App Review Meta (whatsapp_business_management + messaging)
- [ ] Implementar callback do Embedded Signup
- [ ] Onboarding manual nos primeiros 5-10 clientes em paralelo
- **Critério de feito:** cliente conecta WhatsApp em 5 minutos sem intervenção

### Fase 6 — Diferenciação e escala (contínuo)
- [ ] Fase D do canvas (inbound governado pelo blueprint, paridade Manychat — ver [roadmap-canvas-orbita.md](roadmap-canvas-orbita.md))
- [ ] Marketplace de templates da comunidade
- [ ] Métricas avançadas (cohort, LTV, payback)
- [ ] App mobile pra inbox em movimento

---

## Métricas de sucesso

| Métrica | Meta Fase 3 | Meta Fase 5 |
|---|---|---|
| Tenants ativos | 3 | 30 |
| MRR | R$ 1k | R$ 15k |
| Churn mensal | — | < 8% |
| Tempo de onboarding | < 30 min (manual) | < 5 min (Embedded) |
| GMV processado/mês | R$ 5k | R$ 100k |
| NPS | — | > 50 |

---

## Riscos conhecidos

1. **App Review Meta** pode demorar / ser rejeitado → Mitigação: onboarding manual nos primeiros clientes
2. **Política Meta sobre conteúdo espiritual** zona cinza → Validar caso a caso, recusar tenant que prometa cura/medicina/garantia
3. **`app.py` 172k linhas** é dívida → Quebrar antes de adicionar features novas
4. **LGPD em conversas sensíveis** (dor emocional) → DPA, política, retenção, base legal explícita
5. **Custos de IA por tenant** → Metering desde o dia 1; senão margem queima silenciosamente
6. **Quality Rating WhatsApp por tenant** → Monitorar, alertar tenant antes de cair tier
7. **Stripe Risk em categoria espiritual** → Termos claros, política de reembolso, descrição certinha do produto

---

## Próximas decisões em aberto

- [ ] Frontend: estender HTML/Jinja existente, ou React/Next.js separado?
- [ ] Caminho B (done-for-you) primeiro ou A (self-service) direto?
- [ ] Pix recorrente: aceitar limitação Stripe (só cartão recorrente) ou avaliar híbrido?
