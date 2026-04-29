# Spec Acássia 360° — Frente 2: Plan Gating & Billing

> Source-of-truth versionado. Atualizar conforme implementação revelar edge cases.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada
> Última atualização: 2026-04-29

## Inventário (mapa completo)

| #    | Feature                                  | Crítico? | Sprint |
|------|------------------------------------------|----------|--------|
| 2.1  | Schema canônico de planos                | 🔴 sim   | A      |
| 2.2  | Quota counters atômicos                  | 🔴 sim   | A      |
| 2.3  | Reset mensal de cotas (cron)             | 🔴 sim   | A      |
| 2.4  | Quota — leads/mês                        | 🔴 sim   | A      |
| 2.5  | Quota — mensagens WhatsApp/mês           | 🔴 sim   | A      |
| 2.6  | Quota — tokens Gemini/mês                | 🔴 sim   | A      |
| 2.7  | Quota — fluxos ativos                    | 🟡 alto  | B      |
| 2.8  | Quota — agentes IA                       | 🟡 alto  | B      |
| 2.9  | Quota — conexões WhatsApp simultâneas    | 🟡 alto  | B      |
| 2.10 | Quota — team seats                       | 🟢 médio | C      |
| 2.11 | Soft warnings (80%, 95%)                 | 🔴 sim   | A      |
| 2.12 | Hard limit behavior (queue vs block)     | 🔴 sim   | A      |
| 2.13 | `<FeatureGate>` component                | 🔴 sim   | A      |
| 2.14 | Plan picker / pricing page redesign      | 🟡 alto  | B      |
| 2.15 | Stripe Checkout integration              | 🔴 sim   | A      |
| 2.16 | Stripe webhook handling robusto          | 🔴 sim   | A      |
| 2.17 | Self-service upgrade (proration)         | 🔴 sim   | A      |
| 2.18 | Self-service downgrade com grace         | 🟡 alto  | B      |
| 2.19 | Trial 14d Pro                            | 🔴 sim   | A      |
| 2.20 | Dunning (failed payment retry)           | 🔴 sim   | B      |
| 2.21 | Cancellation flow + win-back             | 🟡 alto  | B      |
| 2.22 | Reactivation flow                        | 🟡 alto  | B      |
| 2.23 | Annual billing                           | 🟢 médio | C      |
| 2.24 | Coupons / discount codes                 | 🟢 médio | C      |
| 2.25 | NF-e + tax handling Brasil               | 🔴 sim*  | C      |
| 2.26 | Pix billing alternativo                  | 🟡 alto  | C      |
| 2.27 | Usage dashboard pro user                 | 🔴 sim   | A      |
| 2.28 | Branding removal (Pro+)                  | 🟢 médio | B      |
| 2.29 | Custom domain (Enterprise)               | 🟢 médio | D      |
| 2.30 | API access tokens (Enterprise)           | 🟢 médio | D      |
| 2.31 | Webhook subscriptions (Enterprise)       | 🟢 médio | D      |
| 2.32 | Priority support tier UI                 | 🟢 médio | C      |
| 2.33 | Team seats / member invites              | 🟡 alto  | C      |
| 2.34 | Member roles                             | 🟡 alto  | C      |

\* obrigatório legalmente

---

## 2.1 Schema canônico de planos

### Decisão de design
Híbrido: código (`plans.py`) define base, DB (`plan_global_overrides`) sobrepõe campo a campo.

### `plans.py` (estrutura)
```python
PLANS = {
    "free": {
        "label": "Grátis", "price_brl": 0, "stripe_price_id": None,
        "limits": {"leads_month": 50, "wa_msgs_month": 200,
                   "gemini_tokens_month": 10_000, "flows": 1, "agents": 1,
                   "wa_connections": 1, "team_seats": 1},
        "features": {"branding_removed": False, "ab_test": False,
                     "api_access": False, "webhooks": False,
                     "custom_domain": False, "priority_support": False},
    },
    "starter": {"label": "Starter", "price_brl": 97, ...},
    "pro": {"label": "Pro", "price_brl": 197, "price_brl_annual": 1_894,
            "limits": {"leads_month": 5000, "flows": 5, ...}, ...},
    "enterprise": {"label": "Enterprise", "price_brl": 497,
                   "limits": {"leads_month": -1, ...},  # -1 = ilimitado
                   "features": {"api_access": True, ...}},
}

def get_plan_config(plan_key) -> dict: ...
def has_quota(plan, kind, current) -> bool: ...
def has_feature(plan, feature) -> bool: ...
```

### Data Model (overrides)
```sql
CREATE TABLE plan_global_overrides (
  id BIGSERIAL PRIMARY KEY,
  plan_key VARCHAR(32) NOT NULL,
  field_path VARCHAR(100) NOT NULL,
  field_value JSONB NOT NULL,
  set_by_admin_id INT NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(plan_key, field_path) WHERE active = TRUE
);
```

### API
```
GET /api/plans → {plans: [...]}
GET /api/me/plan → {plan, source, expires_at, usage, limits, features}
PATCH /api/admin/plans/<key>/override {field_path, field_value, reason}
```

### Frontend
```typescript
// useMyPlan() hook
// useFeature(feature: string): boolean
// <FeatureGate feature="ab_test">{...}</FeatureGate>
```

### Edge cases
- Plan deletado mas tenant tem: fallback `free` + alerta admin
- `-1` (unlimited) deve funcionar em todas comparações

---

## 2.2 Quota counters atômicos

### Data Model
```sql
CREATE TABLE tenant_usage_counters (
  tenant_id VARCHAR(64) NOT NULL,
  period_yyyymm INT NOT NULL,
  kind VARCHAR(40) NOT NULL,
  count BIGINT DEFAULT 0,
  cost_brl_cents BIGINT DEFAULT 0,
  updated_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (tenant_id, period_yyyymm, kind)
);
CREATE INDEX ix_counters_tenant_kind ON tenant_usage_counters(tenant_id, kind, period_yyyymm DESC);
```

### CAS atômico
```sql
WITH upsert AS (
  INSERT INTO tenant_usage_counters (tenant_id, period_yyyymm, kind, count)
  VALUES (:tid, :yyyymm, :kind, 0)
  ON CONFLICT DO NOTHING
)
UPDATE tenant_usage_counters
SET count = count + :amount, updated_at = NOW()
WHERE tenant_id = :tid AND period_yyyymm = :yyyymm AND kind = :kind
  AND (count + :amount <= :limit OR :limit = -1)
RETURNING count;
-- 0 rows = quota_exceeded
```

### Helper
```python
def consume_quota(tenant_id, kind, amount=1) -> tuple[bool, int, int]:
    # retorna (allowed, current_after, limit)
```

### Edge cases
- Race do UPSERT: Postgres garante atomicidade
- Period boundary mid-request: usar timestamp do request, não NOW()
- Counter corrompido: admin reset via UI

### Métricas
- `quota.consumed` {kind, amount}
- `quota.exceeded` {kind, current, limit}

---

## 2.3 Reset mensal de cotas

### Cron
- Hourly job, processa tenants cuja `now_local.day == 1 AND now_local.hour == 0`
- Pré-cria row `(tenant_id, period_yyyymm=novo, kind=*, count=0)`
- Email "cotas renovadas — você tem X leads disponíveis"
- Recalcula health score (1.15)
- Limpa banners "limite atingido"

### Edge cases
- Timezone: usar `users.timezone` (default `America/Sao_Paulo`)
- Period > 6m: archive em tabela separada (compliance)

---

## 2.4 Quota — leads/mês

### Onde plugar
- `engine.py` ou `webhook_handler` no on_new_lead
- Decisão: **queue** (não block) — bloquear lead = perder venda

### UX
- Topbar: barra "412/500 leads" (verde<80, amarela<95, vermelha>=95)
- 100%: banner "Limite atingido. Novos leads em fila até 01/05" + CTA upgrade

### Lead duplicado
- Mesmo phone reaparecendo: NÃO consome quota

### Quota refund (anti-spam)
```python
def refund_lead_quota(lead_id, reason="spam_detected"):
    consume_quota(tenant_id, "leads", -1)
```

---

## 2.5 Quota — mensagens WhatsApp/mês

### Onde plugar
- `api/whatsapp_api.py:enviar_mensagem` ANTES do envio
- Falha → system message no inbox: "⚠️ Mensagem não enviada — limite atingido"

### Edge cases
- Inbound: NÃO conta (quota é outbound)
- HSM template: conta na mesma quota
- Failed send: refund quota (-1)

---

## 2.6 Quota — tokens Gemini/mês

### Onde plugar
- Wrapper único `TokenBudgetGemini`
- Estima tokens prompt antes do call, reconcilia com `response.usage.total_tokens` depois

### UX
- Quota exceeded: bot responde fallback estático ("Estou processando, volto já") + admin notificado
- `/billing/usage` mostra gráfico Gemini diário

### `essential_paths_use_grants` (admin policy)
- Admin marca fluxo crítico → quota usa grants extras automaticamente em vez de cair no fallback

---

## 2.7 Quota — fluxos ativos

### Lógica
- Quota é **estado**, não counter — `count_active_flows(tenant)` real-time
- Check em `POST /api/flows/<id>/publish`

### UX
- Tentar publicar 2º no Starter: modal "despublicar 'Funil X'?" ou "[Upgrade]"

### Downgrade
- 5 publicados Pro→Starter: bloqueia 4, força escolha (2.18)

---

## 2.8 Quota — agentes IA

Mesmo padrão do 2.7 mas pra `studio_agents.is_published=true`.

---

## 2.9 Quota — conexões WhatsApp simultâneas

### Lógica
- Check em `POST /api/whatsapp/connections`
- `count_active_connections(tenant) < plan.limits.wa_connections`

---

## 2.10 Quota — team seats

### Refactor multi-tenant (ver 2.33)
- Hoje: 1 user = 1 tenant
- Refactor: tenant tem múltiplos `tenant_members`

### Tabelas
```sql
CREATE TABLE tenants (
  id VARCHAR(64) PRIMARY KEY,
  owner_user_id INT NOT NULL,
  display_name VARCHAR(200),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE tenant_members (
  tenant_id VARCHAR(64) REFERENCES tenants(id),
  user_id INT REFERENCES users(id),
  role VARCHAR(20),
  invited_by INT, invited_at TIMESTAMP, joined_at TIMESTAMP,
  PRIMARY KEY (tenant_id, user_id)
);
```

### Migration
- Pré-fill: cada user atual vira owner do tenant_id atual.

---

## 2.11 Soft warnings (80%, 95%)

### Email automático
- 80%: 1x/mês/kind "você usou 80% das suas mensagens"
- 95%: "você está prestes a atingir limite"
- 100%: "limite atingido"

### Backend
- Hourly cron: pra cada tenant×kind, calcula pct e dispara email se cruzou threshold
- Tabela `quota_warning_emails_sent` (tenant_id, period_yyyymm, kind, threshold_pct, sent_at)

### Edge case
- Upgrade depois do email 80%: cancela 95%/100%

---

## 2.12 Hard limit behavior

### Decisões por kind
| Kind            | Comportamento                                    |
|-----------------|--------------------------------------------------|
| leads_month     | **Queue** (lead capturado, marcado, processa próximo mês) |
| wa_msgs_month   | **Block** (mensagem não envia) |
| gemini_tokens   | **Fallback estático** |
| flows           | **Block** |
| agents          | **Block** |
| wa_connections  | **Block** |
| team_seats      | **Block** |

### Implementação queue (leads)
```sql
CREATE TABLE leads_queued_quota (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  phone VARCHAR(30),
  source_payload JSONB,
  queued_at TIMESTAMP DEFAULT NOW(),
  processed_at TIMESTAMP,
  process_attempt INT DEFAULT 0
);
```
- Cron 1º do mês: processa fila

### UX
- Banner "23 leads em fila — entram dia 01/05"
- CTA "Antecipar — upgrade"

---

## 2.13 `<FeatureGate>` component

### React API
```tsx
<FeatureGate feature="ab_test">
  <ABTestButton />
</FeatureGate>

<FeatureGate plan="enterprise" fallback="lock">
  <ApiKeyManager />
</FeatureGate>
```

### Fallbacks
- `lock`: opaque + lock icon (default)
- `hide`: null
- `tooltip`: tooltip "disponível no Pro"

### Companion `<QuotaGate>`
```tsx
<QuotaGate kind="leads">
  {({remaining, percentage}) => <div>{remaining} restantes</div>}
</QuotaGate>
```

### Edge cases
- Loading state: skeleton (não vaza feature)
- Upgrade: invalida `useMyPlan` query → atualiza sem refresh

---

## 2.14 Plan picker / pricing redesign

### Layout
- Toggle Mensal/Anual com badge -20%
- 3 plan cards (free/starter omitido se já assinado)
- Pro destacado com "Mais Popular"
- CTA contextual:
  - Sem plano → "Trial 14d"
  - Starter → "Upgrade Pro"
  - Pro → "Upgrade Enterprise"
- Tabela comparativa completa (collapsible)
- FAQ + selo Stripe + métodos pagamento

### API
```
GET /api/plans
GET /api/me/plan
POST /api/billing/checkout {plan_key, billing_period, coupon_code?}
  → {url}
```

### Edge case
- Plan custom (Frente 1.5): mostra "plano negociado — falar suporte"

### Métricas
- `pricing.{viewed|plan_clicked|checkout_started|faq_opened}`

---

## 2.15 Stripe Checkout integration

### Backend
```python
session = stripe.checkout.Session.create(
    mode="subscription",
    line_items=[{"price": price_id, "quantity": 1}],
    customer_email=current_user.email,
    client_reference_id=current_user.tenant_id,
    success_url=f"{APP_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
    cancel_url=f"{APP_URL}/billing",
    subscription_data={
        "trial_period_days": 14 if not had_trial(current_user) else 0,
        "metadata": {"tenant_id": tid, "user_id": uid},
    },
    discounts=[{"coupon": coupon}] if coupon else [],
    allow_promotion_codes=True,
    billing_address_collection="required",
    tax_id_collection={"enabled": True},
    locale="pt-BR",
)
```

### Frontend
- Click upgrade → POST → redirect `session.url`
- Success page: polling 5x até webhook processar

---

## 2.16 Stripe webhook robusto

### Eventos
- `customer.subscription.{created,updated,deleted}`
- `invoice.payment_{succeeded,failed}`
- `customer.subscription.trial_will_end`
- `checkout.session.completed`

### Idempotência
- Reutiliza `payment_event_receipts`
- Cada `event.id` processado 1x

### Edge cases
- Out-of-order delivery: handler usa UPSERT
- Handler falha: 500 → Stripe retenta 3 dias

---

## 2.17 Self-service upgrade

### Fluxo
1. User Starter → "Upgrade Pro"
2. Modal proration: "R$100 hoje, próxima R$197 em DD/MM"
3. Confirma → `stripe.Subscription.modify` com `proration_behavior="create_prorations"`
4. Webhook → backend atualiza plan
5. Quotas recalculadas imediatamente

### Edge case
- Cartão expirado: redirect Stripe portal

---

## 2.18 Self-service downgrade com grace

### Fluxo
1. User Pro → "Downgrade Starter"
2. Modal aviso:
   - Lista tudo que vai perder (4 fluxos, 2 agentes, A/B test, branding)
   - Pede escolha: qual fluxo manter?
   - "Downgrade só entra em vigor em DD/MM (fim do ciclo)"
3. Confirma → marca `pending_downgrade_at` + Stripe update
4. Banner persistente até efetivar
5. Botão "Cancelar downgrade" reverte

### Edge case
- Sem escolha até fim: sistema escolhe último publicado

---

## 2.19 Trial 14d Pro (sem cartão)

### Fluxo
- Signup → `trial_ends_at = NOW() + 14d`
- Banner "Trial: 12 dias restantes"
- Email D-12, D-7, D-3, D-1
- D-0: vai pra free + tela "escolha plano"

### Data Model
```sql
ALTER TABLE users ADD COLUMN trial_started_at TIMESTAMP;
ALTER TABLE users ADD COLUMN trial_ends_at TIMESTAMP;
ALTER TABLE users ADD COLUMN trial_extended_count INT DEFAULT 0;
```

### Edge cases
- Paga antes de 14d: trial cancela limpo
- Trial farming: same email/phone/card blocked

### Métricas
- `trial.{started|day_N_email|converted_to_paid|expired_to_free}`
- Funnel: signup → trial_active → trial_converted (target 25%+)

---

## 2.20 Dunning

### Fluxo
- Webhook `invoice.payment_failed` → `dunning_status="past_due"` dia 0
- Email imediato + Stripe Smart Retries (dia 1, 3, 5, 7)
- Banner persistente in-app
- Dia 7 sem sucesso: cancel sub → free

### UX
- Funcionalidade não-crítica liberada
- Modal hard ao publicar fluxo / mandar mensagem: "Resolva pagamento primeiro"

### Métricas
- `dunning.{started|recovered|churned}` {days_to_recover}

---

## 2.21 Cancellation flow + win-back

### Fluxo
- Modal multi-step:
  1. "Por quê está saindo?" (multiple choice)
  2. Win-back ofertado (baseado na razão):
     - "Caro" → 50% off 3m
     - "Não usando" → "pausar 2 meses?"
     - "Falta feature" → "qual? Vamos avisar"
  3. Confirmação: "Acesso até DD/MM, dados 30d"

### Data Model
```sql
CREATE TABLE cancellation_surveys (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  reason_category VARCHAR(40),
  reason_text TEXT,
  win_back_offered VARCHAR(40),
  win_back_accepted BOOLEAN,
  cancelled_at TIMESTAMP DEFAULT NOW(),
  reactivated_at TIMESTAMP
);
```

### Métricas
- `cancellation.{survey_started|win_back_offered|win_back_accepted|confirmed|reactivated_within_30d}`

---

## 2.22 Reactivation flow

### Fluxo
- User cancelado → email + dashboard "Reativar"
- Click → checkout → sub criada
- Dados intactos se < 30d

---

## 2.23 Annual billing

- Stripe price ID separado
- Toggle no pricing
- 20% off
- Cancelamento mid-year: non-refundable, mantém acesso até final

---

## 2.24 Coupons

### Casos
- Promo manual ("BLACKFRIDAY50")
- Win-back (auto)
- Afiliados

### Data Model
```sql
CREATE TABLE acassia_coupons (
  code VARCHAR(40) PRIMARY KEY,
  stripe_coupon_id VARCHAR(64),
  description TEXT,
  discount_type VARCHAR(10),  -- percent|amount
  discount_value INT,
  duration VARCHAR(20),  -- once|repeating|forever
  duration_in_months INT,
  max_redemptions INT,
  redeemed_count INT DEFAULT 0,
  expires_at TIMESTAMP,
  created_by INT REFERENCES users(id),
  active BOOLEAN DEFAULT TRUE
);
```

### UX
- Pricing: campo "tem cupom?"
- Admin `/admin/coupons` cria/desativa

---

## 2.25 NF-e + tax handling Brasil

### Implementação
- Stripe Tax (suporta Brasil)
- NFE.io ou Enotas pra emitir NF-e
- User cadastra CNPJ → NF-e auto após cobrança
- Email com PDF NF-e

### UX
- `/billing/info` form: CNPJ ou CPF, endereço
- Validação CNPJ via Receita

### Edge cases
- CPF: NF pessoa física
- Sem CNPJ: invoice Stripe simples
- Nota recusada: admin notificado

---

## 2.26 Pix billing alternativo

### Decisão
- Stripe não suporta Pix recorrente
- Integrar Asaas ou Pagar.me
- Pix mensal: QR code via WhatsApp/email; bloqueia se não pagar D+0; cancela D+3

### UX
- Pricing: toggle Cartão/Pix
- Lembretes diários

### Edge cases
- Confirmação Pix demora ~10s: "aguardando confirmação"
- Pix expirado: gera novo QR

---

## 2.27 Usage dashboard

### `/billing/usage`
- Cards top: cota cada kind com barra
- Gráfico linha uso diário
- Top 10 fluxos por consumo tokens
- "Histórico cobranças" → invoices Stripe
- CTA upgrade se > 80% qualquer kind

### API
```
GET /api/me/usage?period=current_month
  → {leads, wa_msgs, gemini_tokens, by_flow}
```

---

## 2.28 Branding removal

### Implementação
```python
def render_message(template, tenant):
    body = template
    if not has_feature(tenant.plan, "branding_removed"):
        body += "\n\n— enviado via Acássia"
    return body
```

### Edge case
- Downgrade: branding volta automaticamente

---

## 2.29 Custom domain (Enterprise)

### Implementação
- User adiciona domain → CNAME `app.acassia.com.br`
- Backend valida via DNS query
- Caddy/Nginx auto SSL Let's Encrypt
- Resolve tenant pelo `Host` header

### Data Model
```sql
CREATE TABLE tenant_custom_domains (
  tenant_id VARCHAR(64),
  domain VARCHAR(200) PRIMARY KEY,
  ssl_status VARCHAR(20),
  cname_verified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 2.30 API access tokens (Enterprise)

### Data Model
```sql
CREATE TABLE api_keys (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  name VARCHAR(100),
  key_hash VARCHAR(64) NOT NULL UNIQUE,  -- bcrypt(plaintext)
  prefix VARCHAR(20) NOT NULL,
  scopes JSONB,
  created_by INT,
  expires_at TIMESTAMP,
  last_used_at TIMESTAMP,
  revoked_at TIMESTAMP
);
```

### Auth
- Header `Authorization: Bearer acassia_sk_xxx`
- Resolve tenant + scopes
- Rate limit por key

### Endpoints públicos
- `/api/v1/leads`, `/api/v1/flows`, etc

### Edge cases
- Revoked: 401 "key revoked"
- Scope insuficiente: 403 "missing scope: leads:write"

---

## 2.31 Webhook subscriptions (Enterprise)

### Data Model
```sql
CREATE TABLE webhook_subscriptions (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  url VARCHAR(500),
  events JSONB,  -- ["lead.created", ...]
  secret VARCHAR(64),
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE webhook_deliveries (
  id BIGSERIAL PRIMARY KEY,
  subscription_id BIGINT,
  event_type VARCHAR(40),
  payload JSONB,
  status VARCHAR(20),
  http_status INT,
  attempts INT DEFAULT 0,
  next_retry_at TIMESTAMP,
  delivered_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Delivery
- Worker fila, POSTs com `X-Acassia-Signature: sha256=...`
- Retry: 1m, 5m, 30m, 2h, 12h (5x exponential backoff)
- Falha 5x: marca failed + email user

---

## 2.32 Priority support tier UI

### Data Model
```sql
CREATE TABLE support_tickets (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  subject VARCHAR(200),
  message TEXT,
  priority VARCHAR(10),
  status VARCHAR(20),
  created_at TIMESTAMP,
  resolved_at TIMESTAMP,
  sla_hours INT
);
```

### UX
- Sidebar badge "Suporte Prioritário ✦" pra Pro+
- `/support` form com SLA visível

---

## 2.33 Team seats / member invites

### Conceito
Tenant = workspace. Owner convida atendentes.

### Data Model (refactor)
```sql
CREATE TABLE tenants (
  id VARCHAR(64) PRIMARY KEY,
  owner_user_id INT NOT NULL,
  display_name VARCHAR(200),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE tenant_members (
  tenant_id VARCHAR(64) REFERENCES tenants(id),
  user_id INT REFERENCES users(id),
  role VARCHAR(20),
  invited_by INT, invited_at TIMESTAMP, joined_at TIMESTAMP,
  PRIMARY KEY (tenant_id, user_id)
);
CREATE TABLE tenant_member_invites (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  email VARCHAR(200),
  role VARCHAR(20),
  invited_by INT,
  token VARCHAR(64) UNIQUE,
  expires_at TIMESTAMP,
  accepted_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Migration cuidadosa
- Cada user atual vira owner do tenant_id atual
- Foreign keys preservadas via tenant_id

### Edge cases
- Convidar email member de OUTRO tenant: aceito permite "trocar workspace"
- Owner sai: bloqueado, precisa transferir ownership

---

## 2.34 Member roles

### Roles
| Role        | Inbox | Builder | Studio | Settings | Billing | Convidar |
|-------------|-------|---------|--------|----------|---------|----------|
| owner       | ✓     | ✓       | ✓      | ✓        | ✓       | ✓        |
| admin       | ✓     | ✓       | ✓      | ✓        | ✗       | ✓        |
| atendente   | ✓     | ✗       | ✗      | parcial  | ✗       | ✗        |
| viewer      | read  | read    | read   | ✗        | ✗       | ✗        |

### Implementação
- Decorator `@require_member_role("owner", "admin")`
- Resolver tenant ativo via header `X-Acassia-Tenant` ou cookie
- Header com dropdown de tenant (multi-tenant user)

---

## Resumo executivo

### Tabelas novas (15)
1. `plan_global_overrides`
2. `tenant_usage_counters`
3. `quota_warning_emails_sent`
4. `leads_queued_quota`
5. `cancellation_surveys`
6. `acassia_coupons`
7. `tenant_custom_domains`
8. `api_keys`
9. `webhook_subscriptions`
10. `webhook_deliveries`
11. `support_tickets`
12. `tenants`
13. `tenant_members`
14. `tenant_member_invites`

### Alterações existentes
- `users`: `trial_started_at`, `trial_ends_at`, `trial_extended_count`, `dunning_status`, `dunning_attempts`, `timezone`

### Refactor crítico
- **Quebrar 1user=1tenant** → multi-tenant via `tenant_members`. Migration cuidadosa, FK atualizadas.

### Endpoints novos: ~30 sob `/api/billing/*`, `/api/me/*`, `/api/v1/*`, `/api/admin/plans/*`

### Frontend
- `/billing` redesign + `/billing/usage` + `/settings/team` + `/settings/api-keys` + `/settings/webhooks`
- `<FeatureGate>` + `<QuotaGate>` componentes
- `useMyPlan()` + `useFeature()` hooks

### Sprints sugeridos
- **A (sem 1-2)**: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.11, 2.12, 2.13, 2.15, 2.16, 2.17, 2.19, 2.27 — foundation + core
- **B (sem 3-4)**: 2.7, 2.8, 2.9, 2.14, 2.18, 2.20, 2.21, 2.22, 2.28 — completar self-service
- **C (sem 5-6)**: 2.10, 2.23, 2.24, 2.25, 2.26, 2.32, 2.33, 2.34 — multi-tenant + LATAM payments
- **D (sem 7+)**: 2.29, 2.30, 2.31 — Enterprise features
