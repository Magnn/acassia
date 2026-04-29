# Spec Acássia 360° — Frente 1: Admin God-Mode

> Source-of-truth versionado das features admin. Atualizar conforme implementação for revelando edge cases.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada
> Última atualização: 2026-04-29

## Inventário (mapa completo)

| #    | Feature                                | Crítico? | Sprint |
|------|----------------------------------------|----------|--------|
| 1.1  | Rota `/admin/*` com guard duplo + 2FA  | 🔴 sim   | A      |
| 1.2  | Impersonate User                       | 🔴 sim   | A      |
| 1.3  | Cross-tenant grid                      | 🔴 sim   | A      |
| 1.4  | Tenant detail page                     | 🔴 sim   | A      |
| 1.5  | Override de plano                      | 🟡 alto  | B      |
| 1.6  | Override de tokens (Gemini/WA)         | 🟡 alto  | B      |
| 1.7  | Refund Stripe pelo UI                  | 🟡 alto  | B      |
| 1.8  | Suspend/reactivate tenant              | 🔴 sim   | A      |
| 1.9  | Soft-delete + recovery (30d window)    | 🔴 sim   | A      |
| 1.10 | Feature flags por tenant               | 🟡 alto  | B      |
| 1.11 | Broadcast in-app                       | 🟢 médio | C      |
| 1.12 | Audit log viewer (global + por tenant) | 🔴 sim   | B      |
| 1.13 | Live activity feed                     | 🟢 médio | C      |
| 1.14 | Métricas de negócio (MRR/churn/LTV)    | 🔴 sim   | B      |
| 1.15 | Tenant health score                    | 🟡 alto  | C      |
| 1.16 | At-risk auto-flagging                  | 🟡 alto  | C      |
| 1.17 | Fraud signals dashboard                | 🟢 médio | D      |
| 1.18 | Global search (Cmd+K) admin            | 🟢 médio | C      |
| 1.19 | Saved views / filtros salvos           | 🟢 médio | C      |
| 1.20 | Tenant tags & categorias               | 🟢 médio | C      |
| 1.21 | Notas internas por tenant              | 🟢 médio | A      |
| 1.22 | Email composer (1:1 + bulk)            | 🟡 alto  | C      |
| 1.23 | LGPD data export por tenant            | 🔴 sim*  | B      |
| 1.24 | Admin team management                  | 🟢 médio | D      |

\* obrigatório legalmente quando lançar comercialmente

---

## 1.1 Rota `/admin/*` com guard duplo + 2FA

### Por quê
Admin compartilhar rota com user é receita pra catástrofe. Isolamento por URL + role + allowlist user_id (env var, não DB) + 2FA = defesa em profundidade.

### User Story
**Como** founder, **quero** que `/admin` seja inacessível pra qualquer usuário fora da minha allowlist explícita, mesmo que `role=admin` no banco, **pra** que comprometimento de uma conta admin (phishing, leak DB) não vire pwn total.

### UX micro-passos
1. User acessa `app.acassia.com.br/admin`
2. Backend checa: tem sessão? → não: redirect `/saas/login?next=/admin`
3. Checa: `role == "admin"`? → não: redirect `/dashboard` + flash "rota restrita"
4. Checa: `user_id ∈ ADMIN_ALLOWLIST_IDS`? → não: 403 hard + log Sentry
5. Checa: cookie `admin_2fa_verified` válido (15min TTL)? → não: redirect `/admin/2fa-challenge`
6. Em challenge: pede TOTP 6 dígitos
7. Confirma → seta cookie httpOnly Secure SameSite=Strict TTL 15min
8. Redirect pro destino original
9. Visual: tema escuro/sóbrio (fundo grafite #1a1a1a, accent vermelho-bordô) — distinto do app user

### Data Model
```sql
ALTER TABLE users ADD COLUMN totp_secret VARCHAR(64);
ALTER TABLE users ADD COLUMN totp_enabled_at TIMESTAMP;
ALTER TABLE users ADD COLUMN totp_recovery_codes JSON;  -- 10 one-time
-- ADMIN_ALLOWLIST_IDS=1,42,107 (env var, NÃO no DB)
```

### API Contracts
```
POST /admin/2fa-challenge {totp}
  200 → {ok, expires_at}
  401 → {error: "invalid_totp"}
  429 → rate limit (5/min)

GET /admin/2fa-status
  200 → {has_totp, last_verified_at}
```

### Permissões
`role=admin` AND `id ∈ ALLOWLIST` AND `2fa_verified < 15min`

### Edge cases
- Perdeu TOTP → `/admin/2fa-recover {recovery_code}`
- 2FA expirado mid-ação → modal reverificação sem perder contexto
- Allowlist vazia em prod = `/admin` 100% inacessível (failsafe)
- IP fora de country whitelist → bloqueio adicional opcional
- Sessão admin não migra pra user

### Estados de erro
- TOTP errado: shake + "código inválido (3 restantes)"
- 5 erros/1min: lockout 15min + email "tentativa suspeita"

### Métricas
- `admin.access.granted` {user_id, ip, route}
- `admin.access.denied` {reason, user_id, ip}
- `admin.2fa.success/fail/lockout`

### Rollout
1. Deploy com allowlist vazia
2. Setup TOTP do Magno + recovery codes salvos
3. Add ID 1 na allowlist
4. Testa fluxo
5. Documenta procedimento de recovery

### Open questions
- WebAuthn/Passkey ao invés de TOTP?
- IP whitelist obrigatório?

---

## 1.2 Impersonate User

### Por quê
80% dos tickets resolve em 30s se admin entra como user.

### User Story
**Como** admin, **quero** entrar como qualquer usuário com 1 clique (após justificar e validar 2FA), **pra** ver exatamente a tela dele com banner persistente + tudo gravado em audit log.

### UX micro-passos
1. Em `/admin/tenants`, hover linha → botão olho 👁️ "Entrar como"
2. Modal:
   - Motivo (obrigatório, min 10 chars)
   - 2FA TOTP
   - Duração: 15min / 1h / 4h
   - Aviso: "ações registradas no audit log"
3. Confirma → backend valida + cria session + cookie especial → redirect `/dashboard`
4. Visual durante impersonate:
   - Banner top fixo vermelho-bordô 40px: `⚠️ IMPERSONATE: maria@x.com — 0:42:13 — [Sair]`
   - Header com border-bottom vermelha 2px
   - Body com leve tinta avermelhada (opacity 5%)
   - Toast em mutações: "✓ Salvou (como Maria)"
5. Sair: click "Sair" → POST stop → redirect `/admin/tenants`

### Data Model
```sql
CREATE TABLE impersonation_sessions (
  id BIGSERIAL PRIMARY KEY,
  admin_user_id INT NOT NULL REFERENCES users(id),
  target_user_id INT NOT NULL REFERENCES users(id),
  target_tenant_id VARCHAR(64) NOT NULL,
  reason TEXT NOT NULL,
  started_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  end_reason VARCHAR(20),  -- manual|expired|forced|crash
  ip_address VARCHAR(45),
  user_agent TEXT,
  actions_count INT DEFAULT 0,
  CONSTRAINT no_self_impersonate CHECK (admin_user_id != target_user_id)
);
CREATE INDEX ix_imp_admin ON impersonation_sessions(admin_user_id, started_at DESC);
CREATE INDEX ix_imp_target ON impersonation_sessions(target_tenant_id, started_at DESC);
CREATE INDEX ix_imp_active ON impersonation_sessions(ended_at) WHERE ended_at IS NULL;

ALTER TABLE eventos_audit ADD COLUMN impersonation_id BIGINT
  REFERENCES impersonation_sessions(id);
```

### API Contracts
```
POST /api/admin/impersonate
  body: {target_user_id, reason, duration_min, totp}
  201 → {ok, session_id, expires_at, redirect_to}
  401 → {error: "totp_invalid"}
  403 → {error: "target_is_admin"}
  422 → {error: "reason_too_short"}

POST /api/admin/impersonate/stop
  200 → {ok, redirect_to}

GET /api/admin/impersonate/active
  200 → {active, session}

GET /api/admin/impersonations?admin_id=&tenant_id=&since=
  200 → {sessions, total}
```

### Permissões
- Admin pode impersonar `role=user` qualquer tenant
- Admin **não pode** impersonar outro admin
- Admin não pode impersonar a si mesmo (CHECK constraint)
- Durante impersonate, **bloqueado**:
  - DELETE da própria conta
  - Mudar email/senha
  - Trocar tenant_id
  - Acessar `/admin/*`

### Edge cases
- Tab fechada: cron 5min fecha sessões expiradas
- Login normal em outra tab: sessão impersonate não vaza (cookies distintos)
- Server restart: cookie ainda válido até `ended_at` setado por cron
- WhatsApp inbound chega: processado normal
- Tentou impersonar tenant suspended: modal "ativar primeiro?"

### Estados de erro
- 2FA expirado mid-impersonate → modal reverificar
- Target deletado mid-session → forced stop
- Target já tem outra sessão admin impersonando → modal warning

### Acessibilidade
- Banner com `role="alert"` `aria-live="polite"`
- Atalho `Cmd+Shift+X` força sair
- Foco volta pro botão original ao sair

### Métricas
- `admin.impersonate.start` {target_tenant, duration_planned, reason_length}
- `admin.impersonate.stop` {duration_actual_s, actions_count, end_reason}
- `admin.impersonate.action` {action_type}
- Dashboard: tempo total/admin/mês, tenants mais visitados

### Rollout
1. **Phase 1**: só Magno, banner roxo, read-only (mutações bloqueadas)
2. **Phase 2**: mutações liberadas, banner vermelho, audit obrigatório
3. **Phase 3**: notificar user por email pós-fato (LGPD transparência)

### Open questions
- Notificar user em tempo real?
- Permitir user opt-out?
- Hotjar-style recording?

---

## 1.3 Cross-tenant grid

### Por quê
A tabela mãe. Founder precisa visão global denso/rápido.

### User Story
**Como** admin, **quero** tabela de todos os tenants com métricas-chave, filtros, busca, ações em massa, **pra** ter pulso da empresa em 1 tela.

### UX layout (`/admin/tenants`)
```
┌──────────────────────────────────────────────────────────────────────┐
│ Tenants (1.247) — [+ novo] [exportar CSV]                            │
│ [🔍 buscar email/id/tel] [Plano ▾] [WA ▾] [Risco ▾] [Mais ▾]         │
│ ┌───┬────────────┬──────┬───┬───────┬──────┬─────┬────┬────┬──────┐ │
│ │ ☐ │ Tenant     │ Plano│MRR│ Signup│ Last │Leads│Msgs│ WA │Risco │ │
│ ├───┼────────────┼──────┼───┼───────┼──────┼─────┼────┼────┼──────┤ │
│ │ ☐ │ Maria 🌙   │ Pro  │197│ 12/01 │ 2h   │ 412 │8.4k│ 🟢 │ 1 ▁  │ │
│ │ ☐ │ João Tarot │Start │ 97│ 03/03 │ 5d   │  18 │ 89 │ 🟡 │ 4 ▆  │ │
│ └───┴────────────┴──────┴───┴───────┴──────┴─────┴────┴────┴──────┘ │
│ Selecionados: 0 → [Email] [Comp 30d] [Flag] [Suspend]                │
└──────────────────────────────────────────────────────────────────────┘
```

### Comportamentos
- Click linha → `/admin/tenants/<id>` (detalhe)
- Click header → sort asc/desc
- Hover linha → botões inline 👁️ 📧 ⚙️
- Sticky header
- Densidade 36px/linha
- Scroll virtual > 100 linhas (TanStack Virtual)
- Loading skeleton 20 linhas

### Filtros (combinam AND)
- **Plano**: starter, pro, enterprise, trial, comp, churned (multiselect chip)
- **Status WA**: 🟢 conectado, 🟡 pending, 🔴 desconectado, ⚫ nunca conectou
- **Risco**: 1-5 (slider range)
- **Last login**: < 24h, < 7d, < 30d, > 30d (chip)
- **Tags**: multiselect (1.20)
- **MRR range**: input min/max
- **Tem fluxo publicado**: yes/no
- **Trial expirando**: < 3d, < 7d
- **Drawer "mais"**: signup_at range, leads_count range, country, etc.

### Bulk actions
- 📧 Enviar email (1.22)
- 🎁 Comp tokens/dias (1.6)
- 🏷️ Adicionar tag (1.20)
- 🚩 Toggle feature flag (1.10)
- ⏸️ Suspender (1.8)
- 📤 Exportar CSV/Excel

### Data Model
```sql
CREATE MATERIALIZED VIEW admin_tenant_overview AS
SELECT
  u.tenant_id, u.id AS user_id, u.email, u.name,
  u.criado_em AS signup_at, u.last_login_at, u.role,
  COALESCE(p.plan, 'free') AS plan,
  COALESCE(p.mrr_brl, 0) AS mrr_brl,
  COALESCE(p.status, 'inactive') AS billing_status,
  (SELECT COUNT(*) FROM leads l WHERE l.tenant_id = u.tenant_id
    AND l.criado_em > NOW() - INTERVAL '30 days') AS leads_30d,
  (SELECT COUNT(*) FROM mensagens m JOIN leads l ON m.lead_id = l.id
    WHERE l.tenant_id = u.tenant_id AND m.timestamp > NOW() - INTERVAL '30 days') AS msgs_30d,
  (SELECT status FROM tenant_wa_status WHERE tenant_id = u.tenant_id) AS wa_status,
  (SELECT health_score FROM tenant_health WHERE tenant_id = u.tenant_id) AS health_score
FROM users u
LEFT JOIN tenant_billing p ON u.tenant_id = p.tenant_id
WHERE u.deleted_at IS NULL;

CREATE INDEX ix_overview_plan ON admin_tenant_overview(plan);
CREATE INDEX ix_overview_signup ON admin_tenant_overview(signup_at);
CREATE INDEX ix_overview_mrr ON admin_tenant_overview(mrr_brl DESC);

-- Cron 15min: REFRESH MATERIALIZED VIEW CONCURRENTLY admin_tenant_overview;
```

### API Contracts
```
GET /api/admin/tenants
  ?cursor=&limit=50&sort=mrr_brl:desc
  &filter[plan]=pro,enterprise&filter[wa_status]=connected
  &filter[mrr_min]=100&search=maria
  200 → {
    tenants: [{tenant_id, user_id, email, name, plan, mrr_brl,
              signup_at, last_login_at, leads_30d, msgs_30d,
              wa_status, health_score, tags, has_active_flow}],
    cursor_next, total_count
  }
```

### Permissões
- `/admin/tenants` requer admin + 2FA
- Bulk actions logadas individualmente em audit

### Edge cases
- Tenant 0 atividade: `—` placeholder (não 0)
- Search query > 200 chars: trunca + warning
- Filter combo retorna 0: empty state
- Bulk em > 100: confirmação extra
- Sort em coluna sem index: fallback `id`
- MV stale: banner "dados de 23h atrás"
- Tenant deletado mid-view: removido na refresh

### Métricas
- `admin.tenants.list_viewed`
- `admin.tenants.filter_applied` {filter_key}
- `admin.tenants.bulk_action_executed` {action, count}
- `admin.tenants.export_csv` {row_count}

### Rollout
1. MV + endpoint sem filtros
2. Filtros básicos (plano, search)
3. Filtros avançados + bulk
4. Export CSV
5. Saved views (1.19)

### Open questions
- Realtime (WS) ou polling 30s? Polling pro MVP.
- Edição inline de tags?

---

## 1.4 Tenant detail page

### Por quê
Página única substitui DBeaver + Stripe + SSH.

### UX (`/admin/tenants/<tenant_id>`)
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Voltar                                                              │
│ ┌──┐ Maria Silva ✦                              [👁️] [📧] [⏸️] [⋯]  │
│ │M │ maria@example.com  •  tenant_abc123                              │
│ └──┘ Pro  •  R$197/mo  •  Signup 12/01  •  Active  •  São Paulo, BR  │
│ [Visão geral][Leads][Fluxos][Faturamento][Tokens][Audit][Notas][...] │
└──────────────────────────────────────────────────────────────────────┘
```

### Tabs

**Visão geral**
- Cards top: MRR, leads_30d, msgs_30d, wa_status
- Timeline vertical de eventos importantes
- Card "Saúde" (health score 1.15)
- Card "Próxima ação sugerida"

**Leads**
- Lista paginada idêntica a `/leads` user
- Filtros status, score, fluxo
- Click → drawer detalhe sem impersonar

**Fluxos**
- Lista blueprints + última edição
- Click → preview readonly
- Botão "ver runs"

**Faturamento**
- Histórico Stripe: subs, invoices, refunds
- Botão "Ver no Stripe"
- Ações: override (1.5), refund (1.7), comp tokens (1.6)
- Próxima cobrança
- Método pagamento mascarado

**Tokens**
- Gráfico Gemini últimos 30d
- Breakdown por modelo
- Total mês vs limite
- Histórico de grants admin

**Audit**
- Tabela `eventos_audit` filtrada
- Filtros tipo, autor (user/impersonate), período
- Export CSV

**Notas**
- Markdown editor lite
- Notas pinadas no topo
- Cada nota: autor + timestamp

### Data Model
```sql
CREATE TABLE tenant_admin_notes (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  author_admin_id INT NOT NULL REFERENCES users(id),
  content TEXT NOT NULL,
  pinned BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP
);
CREATE INDEX ix_notes_tenant ON tenant_admin_notes(tenant_id, pinned DESC, created_at DESC);
```

### API Contracts
```
GET /api/admin/tenants/<id>/overview
GET /api/admin/tenants/<id>/leads
GET /api/admin/tenants/<id>/flows
GET /api/admin/tenants/<id>/billing
GET /api/admin/tenants/<id>/tokens
GET /api/admin/tenants/<id>/audit
GET /api/admin/tenants/<id>/notes
POST /api/admin/tenants/<id>/notes {content, pinned}
PATCH /api/admin/tenants/<id>/notes/<note_id>
DELETE /api/admin/tenants/<id>/notes/<note_id>
```

### Edge cases
- Tenant soft-deleted: banner "deletado em DD/MM — restaurar?"
- Tab Faturamento sem Stripe: empty state
- Notas markdown malformado: fallback texto puro

### Métricas
- `admin.tenant.detail_viewed`
- `admin.tenant.tab_switched` {tab}
- `admin.tenant.note_added`

### Rollout
1. Tabs Visão geral + Leads + Audit (read-only)
2. Tabs Fluxos + Tokens
3. Tab Faturamento (read-only)
4. Tab Notas
5. Ações de override (1.5-1.7)

---

## 1.5 Override de plano

### Por quê
Founder fecha deal "Enterprise grátis 6 meses" no zap → UI pra aplicar sem hackear Stripe.

### UX
- Tab Faturamento → "Override plano"
- Modal: plano novo, duração (30d/90d/1ano/permanente), pausa Stripe?, motivo obrigatório
- User vê banner: "Você tem Pro grátis até DD/MM"

### Data Model
```sql
CREATE TABLE tenant_plan_overrides (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  plan VARCHAR(32) NOT NULL,
  granted_by_admin_id INT NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  starts_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP,  -- null = permanente
  pauses_stripe BOOLEAN DEFAULT TRUE,
  revoked_at TIMESTAMP,
  revoked_by INT REFERENCES users(id),
  revoked_reason TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_overrides_tenant_active ON tenant_plan_overrides(tenant_id)
  WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW());
```

### Lógica `effective_plan`
```python
def effective_plan(tenant_id) -> str:
    o = active_override(tenant_id)
    if o: return o.plan
    s = stripe_subscription(tenant_id)
    if s and s.status == 'active': return s.plan
    if user.trial_ends_at > now(): return 'pro'
    return 'free'
```

### API Contracts
```
POST /api/admin/tenants/<id>/plan-overrides
  {plan, duration_days, pauses_stripe, reason}
  201 → {override, effective_plan_now}

DELETE /api/admin/tenants/<id>/plan-overrides/<id> {reason}
GET /api/admin/tenants/<id>/plan-overrides?include=expired
```

### Edge cases
- Cron diário envia email D-7, D-3, D-1 antes do expire
- User com Stripe Pro + override Enterprise: vê Enterprise; Stripe pausado
- Override permanente em vermelho na grid pra audit
- Revogar: volta ao plano anterior + email aviso
- Stripe cancelou durante override: override válido até expire, depois free

### Métricas
- `admin.plan_override.created` {plan, duration, pauses_stripe}
- `admin.plan_override.revoked`
- `admin.plan_override.expired_auto`
- Dashboard: total comp/mês, taxa conversão pós-comp

---

## 1.6 Override de tokens (Gemini/WA/Leads)

### Por quê
"Maria viralizou no TikTok, deu 5000 leads" → cota extra rápida.

### UX
- Tab Tokens → "+ Conceder cota"
- Modal: tipo (Gemini/WA msgs/Leads), quantidade, validade, motivo

### Data Model
```sql
CREATE TABLE tenant_quota_grants (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  kind VARCHAR(20) NOT NULL,  -- gemini_tokens|wa_msgs|leads
  amount INT NOT NULL,
  used_amount INT DEFAULT 0,
  expires_at TIMESTAMP,
  granted_by INT NOT NULL REFERENCES users(id),
  reason TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ix_grants_tenant_kind ON tenant_quota_grants(tenant_id, kind, expires_at);
```

### Lógica
```python
def effective_quota(tenant_id, kind) -> int:
    base = PLANS[effective_plan(tenant_id)][kind]
    grants = sum_active_grants(tenant_id, kind)
    return base + grants

def consume_quota(tenant_id, kind, amount):
    # FIFO by expiry: gasta grants próximos do expiry primeiro
```

### Edge cases
- Grant expira sem uso: sumiu, sem refund
- Sobra no mês não acumula
- Múltiplos grants ativos: FIFO by expiry

### Métricas
- `admin.quota.granted` {kind, amount, duration}
- `tenant.quota.exceeded_grant`

---

## 1.7 Refund Stripe pelo UI

### UX
- Tab Faturamento → linha invoice → botão "Refund"
- Modal: total/parcial, motivo (vai pro Stripe), email user opt-in

### Data Model
```sql
CREATE TABLE admin_refunds (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  stripe_charge_id VARCHAR(64) NOT NULL,
  stripe_refund_id VARCHAR(64) NOT NULL UNIQUE,
  amount_brl_cents INT NOT NULL,
  reason TEXT NOT NULL,
  initiated_by INT NOT NULL REFERENCES users(id),
  status VARCHAR(20) DEFAULT 'pending',
  stripe_response JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

### API
```
POST /api/admin/tenants/<id>/refunds
  {charge_id, amount_brl_cents, reason, send_email}
  201 → {refund, stripe_status}
  422 → {error: "amount_exceeds_charge"}
  502 → {error: "stripe_api_error"}
```

### Edge cases
- Stripe down: status pending, retry 5min
- Refund parcial somando > original: 422
- Charge > 180d (Stripe rejeita): exibe erro Stripe na UI

### Métricas
- `admin.refund.{initiated|succeeded|failed}` {amount, reason}

---

## 1.8 Suspend/reactivate tenant

### UX
- Menu ⋯ → "Suspender" → modal com efeitos listados + motivo obrigatório + opt-in email
- Suspended → badge vermelho, botão "Reativar"

### Data Model
```sql
ALTER TABLE users ADD COLUMN suspended_at TIMESTAMP;
ALTER TABLE users ADD COLUMN suspended_by INT REFERENCES users(id);
ALTER TABLE users ADD COLUMN suspension_reason TEXT;
```

### Lógica
- `user_loader` retorna user com flag → frontend mostra "conta suspensa"
- `webhook_handler` checa `suspended_at` antes de processar
- Inbound WhatsApp vai pra DLQ (compliance, não perde)

### API
```
POST /api/admin/tenants/<id>/suspend {reason, notify_email}
POST /api/admin/tenants/<id>/reactivate {reason}
```

### Edge cases
- Reativar: DLQ não processado retroativamente (descarta msgs do período)

### Métricas
- `admin.tenant.suspended` {reason_category}
- `admin.tenant.reactivated`

---

## 1.9 Soft-delete + recovery (30d window)

### UX
- Modal com 3 confirmações: digitar email + motivo + checkbox "entendo"
- 30d window pra restaurar em `/admin/tenants?status=deleted`
- Cron diário: hard-delete `WHERE deleted_at < NOW() - 30d`

### Data Model
```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP;
-- TODAS tabelas multi-tenant respeitam deleted_at em JOINs
```

### Hard delete cascata
- leads, mensagens, flow_blueprints (CASCADE FK)
- Stripe: cancel subscription
- Redis: limpa fila do tenant
- Email final ao user

### API
```
POST /api/admin/tenants/<id>/delete {confirm_email, reason}
POST /api/admin/tenants/<id>/restore {reason}
```

### Edge cases
- Stripe ativo: cancel sub antes de deletar
- Sub ativa do user pra leads: bloquear delete

### Métricas
- `admin.tenant.{soft_deleted|hard_deleted|restored}`

---

## 1.10 Feature flags por tenant

### Data Model
```sql
CREATE TABLE feature_flags (
  key VARCHAR(64) PRIMARY KEY,
  description TEXT,
  default_value BOOLEAN DEFAULT FALSE,
  rollout_pct INT DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tenant_feature_flags (
  tenant_id VARCHAR(64) NOT NULL,
  flag_key VARCHAR(64) NOT NULL REFERENCES feature_flags(key),
  enabled BOOLEAN NOT NULL,
  set_by INT REFERENCES users(id),
  set_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (tenant_id, flag_key)
);
```

### Lógica
```python
def is_enabled(tenant_id, key) -> bool:
    o = tenant_override(tenant_id, key)
    if o is not None: return o.enabled
    f = get_flag(key)
    if f.rollout_pct > 0:
        if hash(tenant_id + key) % 100 < f.rollout_pct: return True
    return f.default_value
```

### API
```
GET /api/admin/feature-flags
GET /api/me/features  (resolvido pro user logado)
PATCH /api/admin/feature-flags/<key>
PUT /api/admin/tenants/<id>/feature-flags/<key> {enabled}
DELETE /api/admin/tenants/<id>/feature-flags/<key>
```

### Edge cases
- Flag deletada: fallback `false`
- Hash determinístico (mesmo tenant sempre mesmo resultado)

### Métricas
- `feature_flag.evaluated` (sample 1%)

---

## 1.11 Broadcast in-app

### UX
- `/admin/broadcasts` → form: título, body markdown, severity (info/promo/warn/critical), CTA, audiência (todos/plano/tenants), agendamento, expiry, sticky?
- User vê: banner top + sino 🔔

### Data Model
```sql
CREATE TABLE broadcasts (
  id BIGSERIAL PRIMARY KEY,
  title VARCHAR(200),
  body_md TEXT,
  severity VARCHAR(20),
  cta_text VARCHAR(100),
  cta_url VARCHAR(500),
  audience_type VARCHAR(20),
  audience_filter JSONB,
  starts_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP,
  sticky BOOLEAN DEFAULT FALSE,
  created_by INT REFERENCES users(id)
);
CREATE TABLE broadcast_dismissals (
  user_id INT, broadcast_id BIGINT,
  dismissed_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (user_id, broadcast_id)
);
```

### Métricas
- `broadcast.{created|viewed|cta_clicked|dismissed}`

---

## 1.12 Audit log viewer

### UX
- `/admin/audit` global + tab Audit em tenant detail
- Tabela: timestamp, autor, tipo, target, detalhes JSON expandível
- Filtros: tipo, autor, target_tenant, período
- Search full-text
- Export CSV

### Data Model
- Reutiliza `eventos_audit` + `impersonation_id` (1.2)

### API
```
GET /api/admin/audit
  ?type=&author=&tenant=&since=&until=&search=
  → {events, cursor_next}
```

### Edge cases
- Cresce 1M+ rows: partition por mês, archive em storage frio

---

## 1.13 Live activity feed

### UX
- `/admin/activity` — stream tempo real
- SSE `GET /api/admin/activity/stream` (Last-Event-ID resume)
- Filtros chip: 💰 vendas, 👤 signups, ⚠️ erros, 📨 msgs

### Backend
- Redis pub/sub channel `acassia:activity`
- Cada evento app publica
- Throttle UI: max 10/s renderizado, resto em buffer

### Edge cases
- Reconexão SSE: Last-Event-ID resume sem perder

---

## 1.14 Métricas de negócio

### UX (`/admin/metrics`)
**Cards top (6 grandes):**
- MRR atual + Δ vs mês passado (sparkline 12m)
- Tenants ativos + Δ
- Churn % mensal + tendência
- ARPU
- LTV estimado (cohort 90d)
- New / Expansion / Contraction / Churned MRR (waterfall)

**Gráficos:**
- MRR over time (área stacked por plano)
- Cohort retention heatmap
- Funnel signup → activation → 1st_msg → 1st_sale → renew_30d
- Top 10 tenants MRR
- Top 10 tenants tokens (custo)

**Filtros globais:** período (30d/90d/12m/all), exclude trial

### Backend
- View materializada `mrr_history` (refresh diário)
- Queries cached 1h
- Cohort: tenants signup mês M, % retidos M+1, M+2, ...

### Edge cases
- Cohort < 10: label "low confidence"
- Comp plans: configurável conta como $0 ou shadow MRR

### Open questions
- ChartMogul/Profitwell vs caseiro?

---

## 1.15 Tenant health score

### Componentes (peso)
- **Atividade (40%)**: last_login_days, msgs/week, leads/week
- **Resultado (30%)**: vendas_30d, conversão, sentiment médio
- **Billing (15%)**: plano pago, sem failed_payment recente
- **Engajamento (15%)**: logou Studio? Builder? Inbox?

### Banda
- 80-100: 🟢 healthy
- 50-79: 🟡 at_risk
- < 50: 🔴 critical

### UX
- Coluna na grid (1.3) com cor
- Card no detail com radar chart breakdown
- Filtro "só at-risk"

### Data Model
```sql
CREATE TABLE tenant_health (
  tenant_id VARCHAR(64) PRIMARY KEY,
  score INT,
  band VARCHAR(10),
  components JSONB,
  updated_at TIMESTAMP DEFAULT NOW()
);
```
- Job hourly recalcula

### Métricas
- `tenant.health.{degraded|recovered}` (transições)

---

## 1.16 At-risk auto-flagging

### UX
- `/admin/at-risk` — fila priorizada com playbook sugerido
- Card: tenant + razão + botões ação ("mandar email check-in", "agendar call")
- Histórico de outreaches

### Data Model
```sql
CREATE TABLE at_risk_signals (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  signal_type VARCHAR(40),  -- no_login_21d|drop_msgs_50pct|failed_payment
  severity INT,
  detected_at TIMESTAMP,
  resolved_at TIMESTAMP,
  resolution VARCHAR(40)  -- auto_recovered|admin_action|churned
);
```

### Rollout
- Phase 1: 3 sinais (no_login_21d, drop_msgs_50pct, failed_payment)
- Phase 2: ML/regression model

---

## 1.17 Fraud signals dashboard

### Sinais (job hourly)
- Mesmo Stripe customer card em > 1 tenant
- > 3 signups mesmo IP em 1h
- Tenant > 100 leads em 1h sem interação user
- Tenant nunca logou mas tem leads (proxy bot)

### UX
- `/admin/fraud` — cards por sinal → "investigar / dismiss / banir"
- Histórico de decisões

### Data Model
```sql
CREATE TABLE fraud_signals (
  id BIGSERIAL PRIMARY KEY,
  signal_type VARCHAR(40),
  severity VARCHAR(10),  -- low|medium|high
  payload JSONB,
  related_tenant_ids JSONB,
  status VARCHAR(20) DEFAULT 'open',
  reviewed_by INT,
  resolution_note TEXT,
  detected_at TIMESTAMP DEFAULT NOW(),
  resolved_at TIMESTAMP
);
```

---

## 1.18 Global search admin (Cmd+K)

### UX
- Cmd+K em qualquer página → modal search
- Groups: Tenants, Leads, Flows, Transactions, Audit (top 5 cada)
- ↑↓ navega, Enter abre

### Backend
- `GET /api/admin/search?q=&types=tenants,leads`
- Postgres full-text (`tsvector`) ou Meilisearch

---

## 1.19 Saved views / filtros salvos

### UX
- Em `/admin/tenants` com filtros → "Salvar como vista"
- Sidebar com vistas pessoais + da equipe
- Click → aplica filtros

### Data Model
```sql
CREATE TABLE admin_saved_views (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  name VARCHAR(100),
  resource_type VARCHAR(40),  -- tenants|leads|flows
  filters JSONB,
  is_team_view BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP
);
```

---

## 1.20 Tenant tags & categorias

### Data Model
```sql
CREATE TABLE tenant_tags (
  tenant_id VARCHAR(64),
  tag VARCHAR(40),
  added_by INT,
  added_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (tenant_id, tag)
);
CREATE INDEX ix_tags_tag ON tenant_tags(tag);
```

### UX
- Tab Tags em detail → autocomplete + criar nova
- Filtro tags na grid (1.3)
- Tags coloridas, max 5 chars

---

## 1.21 Notas internas

(coberto em 1.4 tab Notas — `tenant_admin_notes`)

---

## 1.22 Email composer (1:1 + bulk)

### UX
- Em detail → 📧 → modal composer (templates MJML)
- Bulk: grid seleciona N → "Email em lote" → merge tags `{{name}}`
- Templates: "boas-vindas", "trial expirando", "check-in 30d"
- Preview antes de enviar

### Backend
- Provider: Resend ou Mailgun
- `admin_email_log` (recipient, template, subject, body_html, sent_at, opened_at, clicked_at)

### Edge cases
- Bulk > 100: fila + rate limit 60/min
- Recipient unsubscribed: skip + log

---

## 1.23 LGPD data export

### UX
- Detail → ⋯ → "Exportar dados (LGPD)"
- Job assíncrono → email "export pronto: link.zip" (válido 7d)

### Conteúdo ZIP
- `users.json`, `leads.json`, `messages.json`, `flows.json`, `payments.json`
- `audio/`, `media/` directories

### Data Model
```sql
CREATE TABLE data_exports (
  id BIGSERIAL PRIMARY KEY,
  tenant_id VARCHAR(64),
  requested_by INT,
  status VARCHAR(20),  -- queued|generating|ready|expired|failed
  download_url VARCHAR(500),
  expires_at TIMESTAMP,
  size_bytes BIGINT,
  created_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

---

## 1.24 Admin team management

### UX
- `/admin/team` — lista admins + papel + audit summary
- Convidar via email com 2FA setup obrigatório

### Sub-roles do admin
- `admin.founder` — tudo
- `admin.support` — leitura, impersonate, suspend, **sem** financeiro
- `admin.billing` — leitura, refund, plan override, **sem** suspend/delete

### Data Model
```sql
ALTER TABLE users ADD COLUMN admin_subrole VARCHAR(20);
```

---

## Resumo executivo

### Tabelas novas (14)
1. `impersonation_sessions`
2. `tenant_plan_overrides`
3. `tenant_quota_grants`
4. `admin_refunds`
5. `tenant_admin_notes`
6. `feature_flags`
7. `tenant_feature_flags`
8. `broadcasts`
9. `broadcast_dismissals`
10. `tenant_health`
11. `at_risk_signals`
12. `fraud_signals`
13. `admin_saved_views`
14. `tenant_tags`
15. `admin_email_log`
16. `data_exports`

### MVs / views
- `admin_tenant_overview` (refresh 15min)
- `mrr_history` (refresh diário)

### Alterações em tabelas existentes
- `users`: `totp_secret`, `totp_enabled_at`, `totp_recovery_codes`, `suspended_at`, `suspended_by`, `suspension_reason`, `deleted_at`, `admin_subrole`
- `eventos_audit`: `impersonation_id`

### Endpoints novos: ~45 sob `/api/admin/*`

### Frontend: rotas `/admin/*` (12 telas), tema escuro distinto

### Sprints sugeridos
- **Sprint A (sem 1-2)**: 1.1, 1.2, 1.3, 1.4, 1.8, 1.9, 1.21
- **Sprint B (sem 3-4)**: 1.5, 1.6, 1.7, 1.10, 1.12, 1.14, 1.23
- **Sprint C (sem 5-6)**: 1.11, 1.13, 1.15, 1.16, 1.18, 1.19, 1.20, 1.22
- **Sprint D (sem 7+)**: 1.17, 1.24
