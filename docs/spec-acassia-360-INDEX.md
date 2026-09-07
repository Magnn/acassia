# Spec Acássia 360° — Índice Mestre

> Source-of-truth completo do produto Acássia. 8 frentes, ~250 features especificadas.
> Última atualização: 2026-04-29

## Visão geral

Cada frente tem doc próprio com inventário numerado + deep-dive feature por feature.

| Frente | Tema                              | Doc                                       | Features |
|--------|-----------------------------------|-------------------------------------------|----------|
| 1      | Admin God-Mode                    | [frente-1.md](spec-acassia-360-frente-1.md) | 24       |
| 2      | Plan Gating & Billing             | [frente-2.md](spec-acassia-360-frente-2.md) | 34       |
| 3      | Inbox + Funnel Intelligence       | [frente-3.md](spec-acassia-360-frente-3.md) | 45       |
| 4      | Niche-Specific (espiritual moat)  | [frente-4.md](spec-acassia-360-frente-4.md) | 30       |
| 5      | UX da Plataforma                  | [frente-5.md](spec-acassia-360-frente-5.md) | 34       |
| 6      | AI Copilot (Cigana Coach)         | [frente-6.md](spec-acassia-360-frente-6.md) | 25       |
| 7      | Integrações & Network Effects     | [frente-7.md](spec-acassia-360-frente-7.md) | 30       |
| 8      | Trust, Segurança & Compliance     | [frente-8.md](spec-acassia-360-frente-8.md) | 35       |
| **TOTAL** |                                |                                           | **257**  |

## Como ler cada feature

Template padrão usado em todas:

- **Por quê** — rationale de negócio
- **User Story** — formato "como X, quero Y, pra Z"
- **UX micro-passos** — step by step + ASCII mockups onde aplicável
- **Data Model** — SQL CREATE TABLE
- **API Contracts** — endpoints + payloads
- **Permissões** — quem pode fazer o quê
- **Edge cases** — exhaustive list de casos limite
- **Estados de erro** — o que mostrar quando falha
- **Métricas** — telemetria pra capturar
- **Rollout** — plano de fases
- **Open questions** — decisões em aberto

## Como citar uma feature

Use a numeração `frente.feature`:
- "Vamos implementar **1.2** (Impersonate User) primeiro"
- "Adiciona campo X em **3.18** (dados do lead)"
- "**4.14** (voice cloning) é nosso killer feature"

## Estatísticas globais

### Tabelas novas (~80)
Distribuídas pelas frentes. Resumo:
- Frente 1: 14 tabelas (admin)
- Frente 2: 15 tabelas (billing + multi-tenant)
- Frente 3: 11 tabelas (inbox)
- Frente 4: 12 tabelas (espiritual)
- Frente 5: 5 tabelas (UX)
- Frente 6: 2 tabelas (AI)
- Frente 7: 16 tabelas (integrações)
- Frente 8: 6 tabelas (segurança)

### Refactors críticos
- **Multi-tenant** (Frente 2.10/2.33): quebrar 1user=1tenant → workspace com members
- **Storage de mídia** (Frente 7.24): migrar de DB/disk pra S3/R2
- **Audit log** (Frente 1.12 + 8.5): enriquecer + partition

### Provider integrations
**Pagamento**: Stripe, Mercado Pago, Pagar.me, Asaas, Cakto, Hotmart  
**Comunicação**: Meta Cloud, Coex BSP, Evolution, IG DM, Telegram, Messenger, Email (Resend)  
**IA**: Gemini, ElevenLabs (voice), Whisper (transcription), Stable Diffusion (Replicate)  
**Lead capture**: TikTok Marketing API, Meta Marketing API, Pixel próprio  
**Analytics**: PostHog/Amplitude (forwarder)  
**Calendário**: Cal.com, Calendly, Google Calendar, Apple Calendar  
**Storage**: Cloudflare R2 ou AWS S3  
**Astrologia**: Swiss Ephemeris (lib), API externa horóscopo  
**Workflow externo**: Zapier, n8n, Make  

### Endpoints novos (~250)
Organizados em namespaces:
- `/api/admin/*` (~45)
- `/api/billing/*` (~10)
- `/api/me/*` (~15)
- `/api/leads/*`, `/api/conversations/*` (~20)
- `/api/flows/*`, `/api/analytics/*` (~25)
- `/api/lunar/*`, `/api/tarot/*`, `/api/voice/*` (~25)
- `/api/integrations/*` (~30)
- `/api/marketplace/*`, `/api/affiliate/*` (~15)
- `/api/auth/*`, `/api/security/*`, `/api/privacy/*` (~20)
- `/api/v1/*` (público Enterprise) (~30)
- `/api/admin/*`, `/api/coach/*`, etc (~20)

## Roadmap macro sugerido

Cada frente tem seus sprints A/B/C/D. Recomendação de **ordem global** caso queira sequenciar:

### Fase 0 — Foundations (já iniciado, Sprint 1 pre-VPS)
- ✅ Alembic, CORS, telemetria, /api/health/deep, ErrorBoundary

### Fase 1 — Admin Cockpit + Billing (4-6 semanas)
- Frente 1 sprints A+B (1.1, 1.2, 1.3, 1.4, 1.8, 1.9, 1.21, 1.5, 1.6, 1.7, 1.10, 1.12, 1.14, 1.23)
- Frente 2 sprint A (2.1-2.6, 2.11-2.13, 2.15-2.17, 2.19, 2.27)
- Frente 8 sprint A (8.1, 8.4-8.11, 8.13-8.17, 8.22, 8.24, 8.25, 8.32-8.34)

### Fase 2 — Produto principal (Inbox + UX) (4-6 semanas)
- Frente 3 sprints A+B (inbox 3-painel, scoring, funnel)
- Frente 5 sprints A+B (onboarding, Cmd+K, mobile PWA, a11y)

### Fase 3 — Diferenciação espiritual + IA (4-6 semanas)
- Frente 4 sprint A (voice cloning, tarô virtual, lunar, signo)
- Frente 6 sprint A+B (Coach, copy generator, summarizer)

### Fase 4 — Crescimento (4-6 semanas)
- Frente 7 sprints A+B (Pix, biolink, lead ads, affiliate, agendamento)
- Frente 2 sprints B+C (downgrade, dunning, multi-tenant, Pix billing)

### Fase 5 — Maturidade (8+ semanas)
- Frente 1 sprints C+D (broadcasts, fraud, search, team mgmt)
- Frente 3 sprints C+D
- Frente 4 sprints B+C
- Frente 5 sprint C
- Frente 6 sprint C
- Frente 7 sprint C
- Frente 8 sprints B+C

### Fase 6 — Enterprise & V2 (12+ semanas)
- Custom domain, API keys, webhooks (2.29-2.31)
- ML scoring (6.14-6.15)
- SSO, SOC 2, GDPR (8.3, 8.19, 8.27)
- Marketplace, diretório público (7.14, 7.16)

## Princípios transversais (aplicar em tudo)

1. **Multi-tenant first** — cada query filtra por tenant_id (Frente 2)
2. **Quota-aware** — toda action consome quota (Frente 2.2)
3. **Audit-by-default** — toda mutação loga em eventos_audit (Frente 1.12)
4. **PII redaction** — logs sem dados pessoais (Frente 8.24)
5. **a11y AA** — WCAG 2.1 AA (Frente 5.21)
6. **Mobile-first** — PWA + responsive (Frente 5.8)
7. **i18n-ready** — strings em JSON (Frente 5.22)
8. **Idempotency** — webhooks e mutações idempotentes (Frente 1, 7)
9. **Privacy-by-design** — consent management embutido (Frente 8)
10. **Observabilidade** — telemetria, Sentry, métricas em tudo

## Open questions globais (decisões pendentes)

- **DB**: Postgres em prod definido? SQLite só dev? (Sprint 1 já preparou Alembic pra ambos)
- **Hosting**: Hostinger VPS confirmed; precisa preparar Caddy + Cloudflare?
- **Mídia**: Cloudflare R2 ou AWS S3? Decisão custo×latência
- **IA**: Gemini exclusive ou multi-LLM (OpenAI fallback)?
- **Email**: Resend ou Mailgun? Custos similares
- **Pix provider**: Mercado Pago primeiro ou Asaas?
- **Marketplace launch**: pre-curated com top 5 fluxos próprios ou aberto direto?
- **Affiliate %**: 30% padrão competitivo? Tier system progressivo?
- **Custom domain**: necessário ter API keys/webhooks pra ter Enterprise?
- **Multi-language**: pt-BR only V1, V2 expande pra es-AR/MX?
