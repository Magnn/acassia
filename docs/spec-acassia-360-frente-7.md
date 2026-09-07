# Spec Acássia 360° — Frente 7: Integrações & Network Effects

> Pix nativo, TikTok ads, marketplace, affiliate, IG DM. O que faz o produto crescer organicamente.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada.
> Última atualização: 2026-04-29

## Inventário

| #    | Feature                                          | Crítico? | Sprint |
|------|--------------------------------------------------|----------|--------|
| 7.1  | Pix QR dinâmico nativo                           | 🔴 sim   | A      |
| 7.2  | Mercado Pago integration                         | 🟡 alto  | B      |
| 7.3  | Pagar.me integration                             | 🟡 alto  | B      |
| 7.4  | Asaas integration                                | 🟡 alto  | B      |
| 7.5  | Carteira digital interna (créditos)              | 🟢 médio | C      |
| 7.6  | TikTok Lead Ads import                           | 🟡 alto  | B      |
| 7.7  | Instagram Lead Ads import                        | 🟡 alto  | B      |
| 7.8  | Pixel Acássia (JS snippet)                       | 🟡 alto  | C      |
| 7.9  | Link mágico bio (acassia.bio/maria)              | 🔴 sim   | A      |
| 7.10 | Instagram DM unificado                           | 🟡 alto  | C      |
| 7.11 | Telegram integration                             | 🟢 médio | D      |
| 7.12 | Messenger integration                            | 🟢 médio | D      |
| 7.13 | Email warmup (SendGrid/Resend)                   | 🟢 médio | C      |
| 7.14 | Marketplace de fluxos                            | 🟡 alto  | C      |
| 7.15 | Affiliate program (referral)                     | 🔴 sim   | B      |
| 7.16 | Diretório público (acassia.com.br/maria)         | 🟢 médio | C      |
| 7.17 | Reviews/testimonials                             | 🟢 médio | C      |
| 7.18 | Notion sync                                      | 🟢 médio | D      |
| 7.19 | Google Sheets sync                               | 🟡 alto  | C      |
| 7.20 | Cal.com / Calendly integration                   | 🟡 alto  | B      |
| 7.21 | Zapier integration                               | 🟢 médio | D      |
| 7.22 | n8n integration                                  | 🟢 médio | D      |
| 7.23 | OpenAI TTS alternativa (já em 4.14)              | -        | -      |
| 7.24 | Cloudinary/S3 média storage                      | 🔴 sim   | A      |
| 7.25 | Resend transactional email                       | 🔴 sim   | A      |
| 7.26 | PostHog/Amplitude analytics forwarder            | 🟡 alto  | B      |
| 7.27 | Slack/Discord webhook (notificações user)        | 🟢 médio | C      |
| 7.28 | YouTube/Spotify embed em msgs                    | 🟢 médio | D      |
| 7.29 | Cakto/Hotmart webhook (já existe — expandir)     | 🟡 alto  | A      |
| 7.30 | Apple/Google Calendar sync (agendamentos)        | 🟢 médio | D      |

---

## 7.1 Pix QR dinâmico nativo

### Por quê (KILLER)
Lead pergunta "como pago?" — bot manda **QR code Pix com vencimento de 30min**. Urgência = conversão.

### Provider
- **Mercado Pago** API (mais simples, suporta Pix nativo)
- Alternativas: Asaas, Pagar.me, EFI Bank, Gerencianet

### Fluxo
1. No fluxo Builder: nó "Pix" → config valor + descrição + expira_min
2. Quando lead chega no nó:
   - Backend: `mercadopago.payment.create({transaction_amount, payment_method=pix, expiration: NOW+30min})`
   - Recebe `qr_code_image_url` + `qr_code_text` (copy-paste)
   - Bot manda imagem QR + texto "Vence em 30min — depois preciso gerar novo"
3. Webhook do MP → `payment.approved` → bot manda confirmação automática

### Data Model
```sql
CREATE TABLE pix_payments (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  lead_id BIGINT,
  flow_run_id BIGINT,
  provider VARCHAR(40),  -- mercadopago|asaas|...
  provider_payment_id VARCHAR(100),
  amount_brl_cents INT,
  description TEXT,
  qr_code_image_url VARCHAR(500),
  qr_code_text TEXT,
  expires_at TIMESTAMP,
  status VARCHAR(20),  -- pending|approved|expired|cancelled
  paid_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_pix_status ON pix_payments(status, expires_at);
```

### UX (admin)
- `/integrations/payments` — conectar MP/Asaas com OAuth
- Test mode: gera QR sandbox antes de produção

### Edge cases
- Provider down: fallback link checkout web
- Lead pagou mas webhook atrasou: confirma manualmente botão admin
- QR expirado, lead voltou: auto-gera novo (usa flow_run state)
- Refund: botão admin → MP API + bot manda msg "reembolso processado"

### Métricas
- `pix.created`, `pix.paid`, `pix.expired_unpaid`
- Conversão Pix vs cartão

---

## 7.2 / 7.3 / 7.4 Mercado Pago / Pagar.me / Asaas

### Sub-features de 7.1
- Cada provider = adapter com mesma interface:
  ```python
  class PaymentProvider(ABC):
      def create_pix(amount, description, expires) -> PixResult
      def create_credit_card_link(amount, ...) -> str
      def get_payment_status(provider_id) -> Status
      def refund(provider_id, amount?) -> bool
  ```
- User escolhe provider preferido em settings
- Multi-provider: mesma conta pode ter MP+Stripe+Cakto ativos

---

## 7.5 Carteira digital interna

### Por quê
Lead recorrente compra "10 créditos" = R$500 (volume discount). Gasta gradativo. Aumenta LTV + retenção.

### Conceito
- Tarólogo define produtos em "créditos": Tiragem 1 carta = 1 crédito, Mistério = 5 créditos
- Lead compra pacote: 10 créditos R$200 (R$20/crédito vs R$25 unitário)
- Saldo persiste, gasta em consultas

### Data Model
```sql
CREATE TABLE lead_wallets (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT UNIQUE,
  balance_credits INT DEFAULT 0,
  total_purchased_brl_cents BIGINT DEFAULT 0,
  total_consumed_credits BIGINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE wallet_transactions (
  id BIGSERIAL PRIMARY KEY,
  wallet_id BIGINT REFERENCES lead_wallets(id),
  type VARCHAR(20),  -- purchase|consume|refund|gift
  credits_delta INT,  -- +/-
  brl_cents_paid INT,
  reference TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### UX
- Lead recebe msg "Você tem 7 créditos. Próxima tiragem usa 1?"
- Tarólogo dashboard: total créditos vendidos, leads com saldo

---

## 7.6 TikTok Lead Ads import

### Por quê
TikTok Lead Ads é canal hot pra tarot. Hoje user precisa exportar CSV manual.

### Implementação
- TikTok Marketing API: `Lead Ads → Webhook` real-time
- User conecta conta TikTok Business via OAuth
- Cada lead capturado vira `leads` row + dispara fluxo "boas-vindas TikTok"

### Data Model
- Reutiliza `leads` com `utm_source="tiktok"`
- Tabela `tiktok_integrations` (tenant_id, oauth_token, ad_account_ids)

### UX
- `/integrations/tiktok` → conectar
- Map fields: TikTok lead form → leads.* (nome, telefone, email)

---

## 7.7 Instagram Lead Ads import

### Igual 7.6 mas Meta API
- Webhook Facebook Lead Ads
- Mesmo mapping pattern

---

## 7.8 Pixel Acássia (JS snippet)

### Por quê
Tarólogo cola JS no site/landing → captura visitantes → tag automático no Acássia.

### Implementação
- Snippet:
  ```html
  <script src="https://app.acassia.com.br/pixel.js" data-tenant="tenant_xxx"></script>
  ```
- Pixel envia eventos: pageview, click WhatsApp button, form submit
- Backend recebe via `POST /api/pixel/event`
- Cria/atualiza lead com source="pixel"

### Data Model
```sql
CREATE TABLE pixel_events (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  visitor_id VARCHAR(64),  -- cookie ID
  event_type VARCHAR(40),
  url VARCHAR(500),
  payload JSONB,
  ip VARCHAR(45),
  user_agent TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### UX
- `/integrations/pixel` → snippet pronto pra copiar
- Verificação live: "última visita há 2min ✓"

---

## 7.9 Link mágico bio (acassia.bio/maria)

### Por quê (KILLER pra orgânico)
Substitui Linktree. Tarólogo coloca `acassia.bio/maria` na bio TikTok/IG → lead clica → captura phone → vai pro WhatsApp dela com fluxo já iniciado.

### UX (`/settings/biolink`)
- Editor de página:
  - Avatar
  - Nome + tagline
  - Botões customizáveis (até 5):
    - "💬 Falar no WhatsApp" (default — captura)
    - "📅 Agendar consulta"
    - "💝 Comprar tiragem"
    - "📺 Meu YouTube" (link externo)
    - "📷 Meu Instagram"
  - Background customizável (gradient ou imagem)
- URL pública: `acassia.bio/maria` (subdomain dedicado)
- Mobile-first design

### Captura
- Click "Falar WhatsApp" → modal "Qual seu telefone?" (fricção mínima)
- Phone collected → redirect `wa.me/<tarólogo>?text=encoded_intent_token` com UTM
- Bot recebe primeira msg com token, identifica origem (bio link)

### Data Model
```sql
CREATE TABLE biolinks (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  slug VARCHAR(60) UNIQUE,
  data JSONB,  -- toda config visual + botões
  visit_count INT DEFAULT 0,
  conversion_count INT DEFAULT 0,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Métricas
- Visits, conversions, CTR
- Heatmap clicks por botão
- A/B test variantes de página

---

## 7.10 Instagram DM unificado

### Por quê
Leads vêm via IG Direct também. Não migrar pra WhatsApp = perder.

### Implementação
- Meta Messenger Platform → IG DM webhook
- Mensagens IG aparecem no mesmo inbox com badge "📷 IG"
- Resposta funciona idêntico

### Edge cases
- IG limita 1 conversa só após 7d sem msg do user (24h+template approved)
- Some features (templates, reactions) diferentes do WA

---

## 7.11 / 7.12 Telegram / Messenger

- Padrão similar a IG: webhook → unified inbox
- Cada canal é provider-specific connector
- Lead pode ter múltiplos `lead_channels`

### Data Model
```sql
CREATE TABLE lead_channels (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT,
  channel_type VARCHAR(20),  -- whatsapp|instagram|telegram|messenger
  external_id VARCHAR(100),  -- phone, ig user id, telegram id, etc
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 7.13 Email warmup

### Por quê
Lead que não responde WA ainda pode reagir a email.

### Fluxo
- Lead inativo > 14d sem resposta
- IA gera msg follow-up via email (se tem email)
- Resend API ou SendGrid envia
- Tracking: open, click → atualiza status no CRM

### Edge cases
- Lead sem email: skip
- Email rejected (bounce): marca email como inválido
- Spam complaints > 0.1%: pausa automação + alerta

---

## 7.14 Marketplace de fluxos

### Por quê (NETWORK EFFECT)
Tarólogo top vende seu fluxo provado. Comprador ganha tempo. Você fica com 30% comissão.

### UX (`/marketplace`)
- Galeria de fluxos pagos:
  - Nome, autor verificado, descrição
  - Métricas: usado por X pessoas, conversão média Y%
  - Preço: R$97-497
  - Preview interativo
  - Reviews
- Click "Comprar" → Stripe Checkout
- Após compra: clona pra workspace + acesso vitalício

### Para vendedores (Pro+)
- `/marketplace/sell` — publicar fluxo:
  - Descrição, preço
  - Aprovar moderação Acássia (~24h)
  - Recebe 70% (você fica com 30%)

### Data Model
```sql
CREATE TABLE marketplace_listings (
  id BIGSERIAL PRIMARY KEY,
  seller_tenant_id VARCHAR(64),
  flow_template_id VARCHAR(40),  -- referência ao 5.3
  title VARCHAR(200),
  description TEXT,
  price_brl_cents INT,
  metrics JSONB,  -- avg_conversion, sample_size
  status VARCHAR(20),  -- pending_review|active|paused|removed
  approved_by_admin INT,
  approved_at TIMESTAMP,
  total_sales INT DEFAULT 0,
  total_revenue_brl_cents BIGINT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE marketplace_purchases (
  id BIGSERIAL PRIMARY KEY,
  buyer_tenant_id VARCHAR(64),
  listing_id BIGINT,
  amount_brl_cents INT,
  acassia_fee_cents INT,
  seller_payout_cents INT,
  stripe_payment_id VARCHAR(100),
  purchased_at TIMESTAMP DEFAULT NOW()
);
```

### Edge cases
- Vendedor cancela conta: fluxos vendidos continuam funcionando, mas listing some
- Comprador downgrade: mantém acesso ao fluxo comprado
- Disputa qualidade: refund 7 dias

---

## 7.15 Affiliate program

### Por quê (GROWTH ENGINE)
"Cada nova tarot reader que você indicar te dá 30% recorrente."

### Fluxo
- Cada tenant ganha link único: `acassia.com.br/?ref=maria123`
- Click → cookie 30d → signup atribui referral
- Referral paga assinatura → afiliado recebe 30% mensal enquanto ativo
- Pagamento: PIX mensal automático ou desconto na sub do afiliado

### Data Model
```sql
CREATE TABLE affiliates (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  ref_code VARCHAR(40) UNIQUE,
  total_referrals INT DEFAULT 0,
  total_earned_brl_cents BIGINT DEFAULT 0,
  total_paid_out_brl_cents BIGINT DEFAULT 0,
  pix_key VARCHAR(100),  -- pra payout
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE referrals (
  id BIGSERIAL PRIMARY KEY,
  affiliate_id BIGINT,
  referred_user_id INT,
  signed_up_at TIMESTAMP,
  first_payment_at TIMESTAMP,
  status VARCHAR(20),  -- pending|active|churned
  total_commission_earned_cents BIGINT DEFAULT 0
);
CREATE TABLE affiliate_payouts (
  id BIGSERIAL PRIMARY KEY,
  affiliate_id BIGINT,
  period_yyyymm INT,
  amount_brl_cents BIGINT,
  status VARCHAR(20),  -- pending|paid|failed
  paid_at TIMESTAMP,
  pix_receipt_url VARCHAR(500)
);
```

### UX
- `/affiliate` dashboard:
  - Link ref + share buttons
  - Métricas: clicks, signups, MRR ativo, total ganho
  - Histórico de payouts
  - Tier sistema: 30% padrão → 40% após 10 ativos → 50% após 50 ativos

### Edge cases
- Self-referral: bloqueado (mesmo email/CPF/IP)
- Fraud: refer pessoas fake → detect + ban
- Affiliate churna: comissão para imediatamente
- Comprou via cupom: comissão sobre valor pós-desconto

---

## 7.16 Diretório público

### Por quê
SEO + descoberta orgânica + prova social.

### UX (`acassia.com.br/diretorio`)
- Listagem pública de tarólogas verificadas
- Filtros: especialidade (amor, dinheiro, etc), preço médio, idioma, online/agora
- Cards com: avatar, nome, especialidade, rating, preço a partir de
- Click → perfil público `/diretorio/maria-cigana`:
  - Bio
  - Reviews
  - "Falar agora no WhatsApp" CTA → biolink (7.9)

### Data Model
```sql
CREATE TABLE public_profiles (
  tenant_id VARCHAR(64) PRIMARY KEY,
  slug VARCHAR(60) UNIQUE,
  display_name VARCHAR(200),
  bio TEXT,
  avatar_url VARCHAR(500),
  specialties JSONB,
  languages JSONB,
  starting_price_brl_cents INT,
  is_public BOOLEAN DEFAULT FALSE,
  is_verified BOOLEAN DEFAULT FALSE,
  rating_avg FLOAT,
  rating_count INT DEFAULT 0,
  view_count INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### SEO
- Server-side rendering (Next.js + Acássia main app pode usar SSG pra perfis)
- Schema.org Person/Service markup
- Sitemap.xml automático

### Verificação
- Tarólogo ativo > 30d + 5+ reviews + sem reports = `is_verified=true`
- Badge ✓ "Verificada Acássia"

---

## 7.17 Reviews/testimonials

### Fluxo
- Após consulta paga, bot pergunta "como foi sua experiência? ⭐⭐⭐⭐⭐"
- Lead avalia + comentário opcional
- Salva em `tenant_reviews`
- Tarólogo aprova (modera) antes de aparecer público

### Data Model
```sql
CREATE TABLE tenant_reviews (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  lead_id BIGINT,
  rating INT,  -- 1-5
  comment TEXT,
  is_public BOOLEAN DEFAULT FALSE,
  approved_by_user BOOLEAN,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Anti-fraud
- Lead só pode avaliar tarólogo se tem `payment_event_receipt` (comprou)
- 1 review por lead/tarólogo
- Reviews falsos: detect + remove

---

## 7.18 Notion sync

### Implementação
- OAuth Notion API
- Tarólogo escolhe database Notion
- Acássia exporta leads automaticamente:
  - Cada lead novo → row no Notion DB com fields mapeados
  - Update em mensagens importantes

### UX
- `/integrations/notion` → conectar + map fields

---

## 7.19 Google Sheets sync

### Por quê
Tarólogo conservador prefere planilha.

### Implementação
- OAuth Google Sheets API
- Cria planilha "Acássia Leads — Maria" automaticamente
- Cada lead novo → row append
- Status updates → row update

### Edge cases
- Planilha deletada: detect + recria
- Quota Google API: rate limit + retry

---

## 7.20 Cal.com / Calendly

### Fluxo
- No Builder: nó "Agendar consulta"
- Conecta Cal.com OAuth
- Lead recebe link de agendamento
- Após agendar: Cal.com webhook → Acássia atualiza lead + marca compromisso

### Data Model
```sql
CREATE TABLE scheduled_appointments (
  id BIGSERIAL PRIMARY KEY,
  lead_id BIGINT,
  tenant_id VARCHAR(64),
  provider VARCHAR(20),  -- cal_com|calendly
  external_event_id VARCHAR(100),
  starts_at TIMESTAMP,
  ends_at TIMESTAMP,
  meeting_url VARCHAR(500),
  status VARCHAR(20),  -- scheduled|completed|cancelled|no_show
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Pre/post hooks
- 1h antes: bot manda lembrete WA
- Pós: bot pede review (7.17)

---

## 7.21 Zapier integration

### Por quê
Tarólogos power-users querem conectar com qualquer ferramenta.

### Implementação
- Acássia como app público no Zapier
- Triggers: `lead.created`, `payment.received`, `flow.completed`, etc
- Actions: `send_message`, `create_lead`, `add_tag`, etc

### Backend
- Endpoints públicos `/api/v1/*` (já em Frente 2.30)
- Webhook subscriptions (Frente 2.31)
- OAuth simplificado pra Zapier

### Edge cases
- Rate limit: 100 req/min por integração

---

## 7.22 n8n integration

- Mesmo padrão Zapier mas self-hosted
- Acássia node oficial no n8n marketplace

---

## 7.24 Cloudinary/S3 média storage

### Por quê
Hoje mídia fica no DB ou disk local. Não escala. Cloudinary/S3 + CDN = barato e rápido.

### Implementação
- Provider: Cloudflare R2 (sem egress fees) ou AWS S3 + CloudFront
- Upload: signed URL pra client → S3 direto (não passa pelo backend)
- Mídia inbound: download da URL Meta + upload pra S3
- URL signed expira 7d (privacidade)

### Data Model
- `mensagens.media_url` agora aponta pra S3
- Tabela `media_assets` (id, tenant_id, key, mime, size, url, expires_at)

### Edge cases
- Migration de mídia existente: job batch
- Vencimento URL: regenera on-demand

---

## 7.25 Resend transactional email

### Por quê
Hoje sem email transacional consistente. Resend.com é simples e barato.

### Casos
- Welcome email signup
- Trial expirando D-3, D-1
- Failed payment dunning
- Quota warning 80%, 95%, 100%
- LGPD data export pronto
- Affiliate payout enviado
- Coach weekly report

### Implementação
- Resend SDK
- Templates MJML versionados em `templates/email/*.mjml`
- Tracking: open + click via Resend webhook

### Backend
- Função única `send_email(to, template, vars)`
- Logs em `email_log` table

---

## 7.26 PostHog/Amplitude analytics forwarder

### Por quê
Frente 1.14 (telemetria) já loga. Forwarder envia pra PostHog server-side pra análise produto.

### Implementação
- Background worker: lê logs `[ANALYTICS]` → POST PostHog Capture API
- Distinct ID: tenant_id
- Properties: do payload do evento

### Edge case
- PostHog down: queue local, retry
- High volume: batch 100 events/req

---

## 7.27 Slack/Discord webhook

### Casos
- Lead VIP entrou (notifica time interno)
- Venda > R$500
- Erro crítico
- Anomaly alert

### UX
- `/integrations/slack` → conectar webhook URL
- Config quais eventos enviar

---

## 7.28 YouTube/Spotify embed

### Por quê
Tarólogo manda link YouTube/Spotify → bot embed bonito no WhatsApp.

### Implementação
- Detect URL no compose → preview rich
- Em msg WA: WhatsApp expande automaticamente

---

## 7.29 Cakto/Hotmart webhook expandir

### Já existe parcial em `payment_event_receipts`
- Adicionar mais providers: Hotmart, Eduzz, Kiwify, Monetizze
- UI de conexão visual

---

## 7.30 Apple/Google Calendar sync

### Por quê
Tarólogo agenda consulta → bloqueia calendário pessoal.

### Implementação
- OAuth Google Calendar / Apple Calendar (CalDAV)
- Quando appointment criado (7.20): cria event no calendário pessoal
- Sync bidirecional opcional

---

## Resumo executivo Frente 7

### Tabelas novas (16)
1. `pix_payments`
2. `lead_wallets` + `wallet_transactions`
3. `tiktok_integrations` (e similar pra outros)
4. `pixel_events`
5. `biolinks`
6. `lead_channels`
7. `marketplace_listings` + `marketplace_purchases`
8. `affiliates` + `referrals` + `affiliate_payouts`
9. `public_profiles`
10. `tenant_reviews`
11. `scheduled_appointments`
12. `media_assets`
13. `email_log`

### Provider integrations
- Mercado Pago, Asaas, Pagar.me (Pix)
- TikTok Marketing API, Meta Marketing API (lead ads)
- Meta Messenger Platform (IG/Messenger)
- Telegram Bot API
- Cal.com, Calendly
- Notion, Google Sheets
- Zapier, n8n
- Resend (email)
- Cloudflare R2 ou AWS S3 + CloudFront
- PostHog, Amplitude
- Slack, Discord webhooks
- Google Calendar, Apple Calendar (CalDAV)

### Endpoints novos: ~40 (`/api/integrations/*`, `/api/marketplace/*`, `/api/affiliate/*`, `/api/v1/*` público, `/api/pixel/*`, `/api/biolinks/*`)

### Frontend
- `/integrations/<provider>` páginas (15+)
- `/marketplace` + `/marketplace/sell`
- `/affiliate` dashboard
- `/settings/biolink` editor
- `/diretorio` público + `/diretorio/<slug>` perfis

### Sub-domain
- `acassia.bio` (biolink subdomain) — DNS + SSL setup

### Sprints
- **A (sem 1-3)**: 7.1, 7.9, 7.24, 7.25, 7.29 — pagamento + bio link + storage + email
- **B (sem 4-6)**: 7.2, 7.3, 7.4, 7.6, 7.7, 7.15, 7.20, 7.26 — multi-payment + lead ads + affiliate + agendamento + analytics
- **C (sem 7-9)**: 7.5, 7.8, 7.10, 7.13, 7.14, 7.16, 7.17, 7.19, 7.27 — wallet + pixel + IG DM + marketplace + diretório + reviews
- **D (sem 10+)**: 7.11, 7.12, 7.18, 7.21, 7.22, 7.28, 7.30 — long tail
