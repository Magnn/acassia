# Spec Acássia 360° — Frente 8: Trust, Segurança & Compliance

> Sem isso, não sobrevive ao primeiro vazamento ou multa LGPD.
>
> Status: 📝 spec aprovada, 🚧 implementação não iniciada.
> Última atualização: 2026-04-29

## Inventário

| #    | Feature                                        | Crítico? | Sprint |
|------|------------------------------------------------|----------|--------|
| 8.1  | 2FA TOTP user-side (não só admin)              | 🔴 sim   | A      |
| 8.2  | 2FA WebAuthn/Passkey                           | 🟡 alto  | C      |
| 8.3  | SSO Google/Microsoft (Enterprise)              | 🟢 médio | D      |
| 8.4  | Session management (lista + revogar)           | 🔴 sim   | A      |
| 8.5  | Audit log público pro user                     | 🔴 sim   | A      |
| 8.6  | Login histórico + IP geolocation               | 🔴 sim   | A      |
| 8.7  | Brute force protection (account-level)         | 🔴 sim   | A      |
| 8.8  | Account lockout                                | 🔴 sim   | A      |
| 8.9  | Password reset flow                            | 🔴 sim   | A      |
| 8.10 | Password requirements (policy)                 | 🔴 sim   | A      |
| 8.11 | Email verification (signup)                    | 🔴 sim   | A      |
| 8.12 | Phone verification (opcional)                  | 🟡 alto  | B      |
| 8.13 | LGPD: cookie banner                            | 🔴 sim   | A      |
| 8.14 | LGPD: privacy policy versionado                | 🔴 sim   | A      |
| 8.15 | LGPD: data subject rights (ver/export/delete) | 🔴 sim   | A      |
| 8.16 | LGPD: consent management                       | 🔴 sim   | A      |
| 8.17 | LGPD: lead opt-in/opt-out                      | 🔴 sim   | A      |
| 8.18 | LGPD: data retention policy                    | 🟡 alto  | B      |
| 8.19 | GDPR compliance (preparação)                   | 🟢 médio | D      |
| 8.20 | DPA (Data Processing Agreement) Enterprise     | 🟢 médio | C      |
| 8.21 | Encryption at rest                             | 🔴 sim   | B      |
| 8.22 | Encryption in transit (TLS)                    | 🔴 sim   | A      |
| 8.23 | Secrets rotation                               | 🟡 alto  | B      |
| 8.24 | PII redaction em logs                          | 🔴 sim   | A      |
| 8.25 | Backup automation                              | 🔴 sim   | A      |
| 8.26 | Disaster recovery plan                         | 🟡 alto  | B      |
| 8.27 | SOC 2 prep                                     | 🟢 médio | D      |
| 8.28 | Pentesting agendado                            | 🟡 alto  | C      |
| 8.29 | Bug bounty program                             | 🟢 médio | D      |
| 8.30 | Status page público                            | 🟡 alto  | B      |
| 8.31 | Suspicious activity detection                  | 🟡 alto  | B      |
| 8.32 | API rate limiting per-tenant                   | 🔴 sim   | A      |
| 8.33 | CSRF protection                                | 🔴 sim   | A      |
| 8.34 | XSS / SQL injection hardening                  | 🔴 sim   | A      |
| 8.35 | DDoS protection                                | 🟡 alto  | B      |

---

## 8.1 2FA TOTP user-side

### Por quê
Frente 1.1 já tem 2FA pra admin. Tarólogo (user) também precisa.

### UX (`/settings/security`)
- Card "Autenticação em 2 etapas"
- Status: desativado / ativado
- Botão "Ativar 2FA"
- Wizard:
  1. Mostra QR code TOTP (Google Authenticator, Authy, 1Password)
  2. User escaneia + digita código
  3. Mostra 10 recovery codes (one-time)
  4. Confirma "salvei os códigos"
- Opcional: tornar 2FA obrigatório no workspace (admin)

### Data Model
- Reutiliza `users.totp_secret`, `totp_enabled_at`, `totp_recovery_codes` (já em Frente 1.1)

### Login flow alterado
1. Email + password OK
2. Se `totp_enabled_at`: pedir código TOTP
3. Validar → criar sessão

### Edge cases
- Lost phone: usar recovery code
- All recovery codes used: contato suporte (verificação via email + identidade)
- 2FA bypass (apoio ao user): admin com 2FA pode desabilitar 2FA do user (audit log + email avisa)

### Métricas
- `security.2fa.enabled`
- `security.2fa.disabled`
- `security.2fa.login_success/failed`

---

## 8.2 2FA WebAuthn/Passkey

### Por quê
Mais seguro que TOTP (phishing-resistant). FaceID, TouchID, YubiKey.

### Implementação
- Lib: `webauthn-python` ou similar
- Browser API: `navigator.credentials.create/get`

### UX
- Em `/settings/security`: opção "Adicionar passkey"
- Click → browser pergunta TouchID/FaceID/security key
- Persiste credential pública

### Data Model
```sql
CREATE TABLE webauthn_credentials (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  credential_id BYTEA UNIQUE,
  public_key BYTEA,
  sign_count INT DEFAULT 0,
  device_name VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  last_used_at TIMESTAMP
);
```

### Edge cases
- Multiple devices: lista todas + remover individual
- Browser sem suporte: fallback TOTP

---

## 8.3 SSO Google/Microsoft

### Por quê (Enterprise)
Empresa quer "todos os funcionários logam com Google Workspace".

### Implementação
- OAuth 2.0 / OIDC com Google + Microsoft
- Mapping email → user
- Auto-create user se domínio corporativo permitido (admin config)

### UX
- Login page: "Continuar com Google" / "Continuar com Microsoft" botões
- Workspace settings: "domain auth" — todos `@empresa.com.br` têm acesso

### Edge cases
- Email não cadastrado: cria user automaticamente (se domain permitido)
- SSO desativado depois: users não conseguem logar com SSO + email/pass funciona se setado

---

## 8.4 Session management

### UX (`/settings/security/sessions`)
- Tabela: device, IP, location (geo), last_seen, browser/OS
- Sessão atual marcada
- Botão "Revogar" individual + "Revogar todas exceto essa"

### Data Model
```sql
CREATE TABLE user_sessions (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  session_token_hash VARCHAR(64) UNIQUE,
  ip_address VARCHAR(45),
  user_agent TEXT,
  device_fingerprint VARCHAR(64),
  geo_country VARCHAR(2),
  geo_city VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  last_activity_at TIMESTAMP,
  expires_at TIMESTAMP,
  revoked_at TIMESTAMP,
  revoked_reason VARCHAR(40)
);
CREATE INDEX ix_sessions_user_active ON user_sessions(user_id) 
  WHERE revoked_at IS NULL AND expires_at > NOW();
```

### Backend
- Cada login cria session row
- Cookie cookie session ID (não data) → lookup
- Revoke: marca `revoked_at`
- Cron diário: hard-delete expired > 30d

### Métricas
- `session.created`
- `session.revoked` {by_user|by_admin|by_security}

---

## 8.5 Audit log público pro user

### Por quê
Transparência. User pode auditar a própria conta.

### UX (`/settings/security/audit`)
- Tabela cronológica:
  - Tipo (login, password_change, plan_change, export_data, etc)
  - When
  - IP + location
  - Device
- Filtros: tipo, período
- Export CSV

### Data Model
- Reutiliza `eventos_audit` filtrado por user/tenant

### Tipos relevantes
- `auth.login.success/failed`
- `auth.password_changed`
- `auth.email_changed`
- `auth.2fa.enabled/disabled`
- `auth.session.revoked`
- `billing.plan_changed`
- `billing.payment.refunded`
- `data.export.requested`
- `data.deletion.requested`
- `team.member.invited/removed`
- `flow.published/deleted`
- `lead.deleted`

---

## 8.6 Login histórico + IP geolocation

### Sub-feature de 8.5
- Em settings: highlight loginsuspeito
- "Login do Brasil" / "Login da Rússia ⚠️"
- Email automático: "Novo login detectado de Moscow, Russia — foi você?"

### IP geolocation
- Lib: `geoip2` (MaxMind) ou API IPinfo
- Free tier ok pra escala inicial

### Edge cases
- VPN: pode flagar errado, mas user dismissa
- Same country, different city: ok

---

## 8.7 Brute force protection

### Lógica
- 5 falhas em 15min na mesma conta → lockout 15min
- 10 falhas em 1h do mesmo IP → block IP 1h
- Email user: "5 tentativas falhas — alguém tentou entrar?"

### Implementação
- Já temos rate limit (Frente 1 implementação Sprint 1)
- Adicionar: rate limit por user_id (não só IP)
- Redis counter `auth_fail:{user_id}` com TTL

---

## 8.8 Account lockout

### Conditions
- 5 falhas seguidas em 15min
- 3 attempts wrong recovery code

### UX após lockout
- Página "Conta bloqueada por 15min — tente em 14min"
- Email: "Sua conta foi bloqueada por 15min por tentativas de login. Não foi você? [Resetar senha]"
- Após 15min: desbloqueio automático

### Bypass (admin)
- Admin pode unlock manual via `/admin/users/<id>` botão "Desbloquear"

---

## 8.9 Password reset flow

### Fluxo
1. Login page → "Esqueci senha"
2. Email input → POST `/auth/password-reset/request`
3. Email com link único: `/reset?token=xxx&email=xxx`
4. Token válido 1h, single-use
5. Click → form nova senha + confirm
6. Submit → password atualizada + revogate todas sessions ativas + email "senha alterada"

### Data Model
```sql
CREATE TABLE password_reset_tokens (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  token_hash VARCHAR(64) UNIQUE,
  expires_at TIMESTAMP,
  used_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Edge cases
- Email não cadastrado: silent (não revelar se email existe — security)
- Token expirado: erro genérico "link inválido — solicitar novo"
- Reset via email comprometido (atacante): user pode "revogar reset" se ainda tem acesso

---

## 8.10 Password requirements (policy)

### Política
- Mínimo 8 caracteres
- Pelo menos 1 maiúscula, 1 minúscula, 1 dígito
- Não pode ser senha comum (top 1000 list)
- Não pode ser igual a últimas 5 senhas (history)

### Implementação
- Lib: `zxcvbn` pra strength meter (visual feedback)
- Hash bcrypt cost 12 (já implementado)
- History: tabela `password_history`:
```sql
CREATE TABLE password_history (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,
  password_hash VARCHAR(255),
  changed_at TIMESTAMP DEFAULT NOW()
);
-- keep last 5 only via cron
```

### UX
- Strength meter no signup/reset
- "Sua senha está fraca" warning
- Sugestão "use uma frase com 4+ palavras"

---

## 8.11 Email verification (signup)

### Por quê
Bloquear signup com emails temporários / inválidos.

### Fluxo
1. Signup → user criado mas `is_verified=false`
2. Email com link verification (token válido 24h)
3. Click → marca verified
4. Login funciona mesmo sem verify, mas funcionalidades limitadas até verify (não publica fluxo, não envia broadcast)

### Edge cases
- Email não chegou: botão "Reenviar"
- Email digitado errado: contato suporte
- 24h expirado: gera novo automaticamente

---

## 8.12 Phone verification

### Casos
- Verify trial farming (mesmo phone = um trial só)
- Recovery 2FA via SMS (fallback TOTP)

### Implementação
- Provider: Twilio Verify ou Vonage
- 6-digit code SMS
- Rate limit: 3 SMS/hora/phone

### Edge cases
- Phone inválido: skip (não obrigatório fora de specific flows)
- SMS não chega: opção voice call

---

## 8.13 LGPD: cookie banner

### Compliance
- Aparece pra novos visitantes (não logados)
- Categorias: essencial (sempre), analytics (opt-in), marketing (opt-in)
- "Aceitar todos" / "Configurar" / "Rejeitar não-essenciais"
- Persiste choice em cookie + DB se logado

### Implementação
- Componente `<CookieBanner>` no root
- API `POST /api/consent {analytics: true, marketing: false}`

### Data Model
```sql
CREATE TABLE consent_records (
  id BIGSERIAL PRIMARY KEY,
  user_id INT,  -- pode ser null pra visitor anônimo
  visitor_id VARCHAR(64),  -- cookie
  consents JSONB,
  ip VARCHAR(45),
  user_agent TEXT,
  policy_version VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 8.14 LGPD: privacy policy versionado

### Por quê
Política muda? User precisa concordar com nova versão.

### Implementação
- Tabela `privacy_policy_versions`:
```sql
CREATE TABLE privacy_policy_versions (
  version VARCHAR(20) PRIMARY KEY,
  content_md TEXT,
  effective_at TIMESTAMP,
  is_current BOOLEAN
);
```
- User concorda → registra `policy_version` no `consent_records`
- Mudança de versão: ao logar, modal "atualizamos a política — leia + concorde"
- Não concordar → bloqueia uso (mostra política até concordar)

---

## 8.15 LGPD: data subject rights

### Direitos garantidos
- **Direito de acesso**: ver todos os dados (já em Frente 1.23 export)
- **Direito de portabilidade**: export ZIP com seus dados (idem)
- **Direito de retificação**: editar dados pessoais (já existe)
- **Direito de eliminação**: deletar conta com confirmação
- **Direito de oposição**: opt-out de marketing/analytics

### UX (`/settings/privacy`)
- Card "Seus direitos LGPD"
- Botões:
  - "Baixar meus dados" → solicita export
  - "Excluir minha conta" → soft-delete 30d (Frente 1.9)
  - "Gerenciar consentimentos"
  - "Contato DPO": email link

### DPO (Data Protection Officer)
- Responsável legal pelo tratamento
- Email público: dpo@acassia.com.br
- Resposta SLA 15 dias (lei)

---

## 8.16 LGPD: consent management

### UX (`/settings/privacy/consents`)
- Lista de finalidades:
  - "Comunicação por email marketing" toggle
  - "Análise de uso" toggle
  - "Personalização IA" toggle
  - "Compartilhamento com parceiros" (sempre off por default)
- Cada toggle: data de aceite, versão de política

### Backend
- Mudança de consent → audit log
- Sistema respeita: se user opt-out marketing, não recebe email broadcast

---

## 8.17 LGPD: lead opt-in/opt-out

### Lead também tem direitos
- Bot pergunta no início: "Aceito receber mensagens da [tarólogo]?"
- Lead responde "STOP" → opt-out automático (compliance WhatsApp)
- Lead responde "PARAR" → idem
- Lead pode pedir delete: "esquece meus dados" → fluxo deleção

### Backend
- Detect keywords stop em msg inbound
- Marca `lead.opted_out=true`
- Não envia mais nada pra esse lead
- Lead pode opt-in de volta com palavra-chave

### Data Model
```sql
ALTER TABLE leads ADD COLUMN opted_out BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN opted_out_at TIMESTAMP;
ALTER TABLE leads ADD COLUMN opt_in_consent_at TIMESTAMP;
```

---

## 8.18 LGPD: data retention policy

### Política
- Lead inativo > 2 anos: anonimizado (mantém estatística, remove PII)
- Mensagens > 5 anos: arquivadas em storage frio
- Audit log > 7 anos: hard delete
- Backups > 90 dias: rotacionados

### Implementação
- Cron mensal: aplica políticas
- Anonimização: substitui `name`, `phone`, `email` por hashes

---

## 8.19 GDPR compliance

### Por quê (V2)
Caso queira expandir UE.

### Diferenças vs LGPD
- Right to be forgotten mais agressivo
- Privacy by design obrigatório
- DPIA (Data Protection Impact Assessment)
- Contato com supervisory authority

### Não MVP — preparar arquitetura compatível.

---

## 8.20 DPA Enterprise

### Por quê
Cliente Enterprise grande (corporações) exige contrato assinado.

### Implementação
- Template DPA padrão
- E-sign via DocuSign ou Acordo
- Customizável (negociação)

---

## 8.21 Encryption at rest

### Banco
- Postgres com TDE (Transparent Data Encryption) ou disk-level encryption (LUKS)
- Hostinger VPS suporta disk encryption no setup

### Mídia (S3/R2)
- AWS SSE-S3 ou Cloudflare encryption (default ativo)

### Secrets (env vars)
- Não em código. `.env` em servidor com chmod 600.
- Rotation: a cada 90d (Frente 8.23)

### PII em DB
- Campos sensíveis (CPF, CNPJ, etc): encrypted column-level com AES-256
- Lib: `cryptography` Python + key em secrets manager

---

## 8.22 Encryption in transit (TLS)

### Padrão
- HTTPS only (HSTS header)
- TLS 1.2+ (1.3 preferido)
- Cert via Let's Encrypt (auto renew)
- Caddy ou Nginx termina TLS

### Edge cases
- Mixed content: zero (forçar https em todos os assets)
- HTTP fallback: redirect 301 → https

---

## 8.23 Secrets rotation

### Lista de secrets
- DB password
- Redis password
- Stripe API keys
- Gemini API key
- Resend API key
- ElevenLabs API key
- OAuth client secrets
- Webhook secrets
- JWT signing keys
- Encryption keys

### Política
- Rotation a cada 90d
- Cron lembrança / playbook documentado
- Some keys (Stripe webhook): rotate via UI provider

### Storage
- 1Password Business ou HashiCorp Vault
- Não em git (óbvio)

---

## 8.24 PII redaction em logs

### Por quê
Logs vão pro Sentry, file logs, etc. PII vazando em log = LGPD breach.

### Implementação
- Logger filter custom: regex pra detectar email, phone, CPF, cartão → mask
- Pre-prod: scan logs por PII patterns
- Sentry: scrub config strict

```python
PII_PATTERNS = [
    (r'\b[\w.+-]+@[\w-]+\.[\w.-]+\b', '[EMAIL]'),
    (r'\b\+?55\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b', '[PHONE]'),
    (r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '[CPF]'),
    # ... 
]

class PIIRedactingFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        for pattern, replace in PII_PATTERNS:
            msg = re.sub(pattern, replace, msg)
        record.msg = msg
        return True
```

### Sentry config
- `before_send` hook redact
- `send_default_pii=False`

---

## 8.25 Backup automation

### Política
- Daily full backup do DB
- Hourly incremental
- 7 daily + 4 weekly + 12 monthly retidos
- Off-site (S3 ou Backblaze, encrypted)

### Implementação
- pg_dump diário via cron
- Upload S3 com encryption-at-rest
- Test restore mensal (DR drill)

### UX (admin)
- `/admin/backups` — lista backups + last verified

---

## 8.26 Disaster recovery plan

### Documento
- Runbook: o que fazer se DB corrompe / VPS morre / Stripe down / Gemini down
- RTO (Recovery Time Objective): 4h
- RPO (Recovery Point Objective): 1h (incremental backup)

### Drills
- Trimestral: restaurar backup em ambiente staging
- Documentar tempo gasto

---

## 8.27 SOC 2 prep

### Por quê (V2)
Vender pra empresa grande precisa SOC 2.

### Trabalho
- Documentar policies (security, incident response, change management)
- Implementar controles
- Auditoria externa (Vanta, Drata pra automação)
- Custo: $20-50k inicial, $10k/ano

### Não MVP — preparar quando atingir 100+ tenants Enterprise.

---

## 8.28 Pentesting agendado

### Cadence
- Anual com firma reputável (Bishop Fox, Trail of Bits, ou local: Tempest, ConvisoLabs)
- Foco: web app + API + auth

### Process
- Receber relatório
- Triagem por severidade (CVSS)
- Fix critical em 7 dias, high em 30, medium em 90
- Re-test após fix

---

## 8.29 Bug bounty program

### Implementação (V2)
- HackerOne ou self-hosted
- Scope: app.acassia.com.br + API
- Bounty:
  - Critical: R$2k-5k
  - High: R$500-2k
  - Medium: R$100-500
- Hall of Fame público

---

## 8.30 Status page público

### Por quê
"O Acássia tá fora?" → status.acassia.com.br responde.

### Implementação
- Provider: Statuspage.io ou self-hosted (Cachet, Uptime Kuma)
- Componentes monitorados:
  - API
  - WhatsApp Cloud
  - Stripe
  - Gemini
  - Database
  - Redis
- Incidents: criar/atualizar manual ou auto via Sentry alerts

---

## 8.31 Suspicious activity detection

### Sinais
- Login de país novo (geoIP diff)
- Login horário incomum (3am quando user usa só 9-17h)
- Mudança de email/password
- Export de dados massivo
- API key gerada após muito tempo inativo

### Ação
- Email + push: "atividade suspeita detectada — foi você?"
- Force re-auth pra ações críticas
- Lock account temporário se múltiplos sinais

---

## 8.32 API rate limiting per-tenant

### Por quê
Tenant comprometido pode floodar API → outros tenants sofrem (noisy neighbor).

### Limites por tenant
- API geral: 60 req/s
- Auth endpoints: 10 req/min (já tem)
- Webhook receivers (Cakto/Stripe): 100/s (alta tolerância)
- Pixel events: 1000/min (maior, é high-volume)

### Implementação
- Flask-Limiter por tenant_id (key_func custom)
- Storage Redis
- Headers X-RateLimit-*

### Edge cases
- Burst legítimo (TikTok viral): admin pode aumentar via override
- 429 response: tenant vê msg amigável "muitas requisições — aguarde 30s"

---

## 8.33 CSRF protection

### Implementação
- Flask-WTF CSRF token em forms
- Frontend SPA: token via cookie + header X-CSRF-Token
- SameSite=Strict cookies

### Edge cases
- API JSON-only (sem forms): SameSite cookie + Origin check ok
- Webhooks externos (Stripe, Meta): verify signature ao invés de CSRF

---

## 8.34 XSS / SQL injection hardening

### XSS
- React por default escapa (good)
- `dangerouslySetInnerHTML` apenas com sanitize (DOMPurify)
- CSP header strict
- User-generated content (nome lead, msgs): sempre escape ao renderizar

### SQL injection
- SQLAlchemy ORM (parameterized queries) ✓
- Raw SQL: sempre `text()` + bind params, nunca f-string
- Audit code base por padrões `f"... WHERE x = '{var}'"` → flag em CI

### Headers de segurança
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: microphone=(self), camera=(self), geolocation=()
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

---

## 8.35 DDoS protection

### Camadas
- **Cloudflare** na frente: anti-DDoS gratuito + WAF rules básicas
- **Rate limiting** (8.32): proteção app-level
- **Caddy/Nginx** com fail2ban: ban IP após X errors

### Edge case
- Legitimate traffic spike (TikTok viral): adjustar Cloudflare rules manualmente
- L7 attacks: Cloudflare Pro ou Bot Management ($)

---

## Resumo executivo Frente 8

### Tabelas novas (8)
1. `webauthn_credentials`
2. `user_sessions`
3. `password_reset_tokens`
4. `password_history`
5. `consent_records`
6. `privacy_policy_versions`

### Alterações em existentes
- `users`: `is_verified`, `phone`, `phone_verified_at`, `last_password_change_at`
- `leads`: `opted_out`, `opted_out_at`, `opt_in_consent_at`
- `eventos_audit`: campos para enriquecer (ip, user_agent, geo)

### Endpoints novos: ~20 sob `/api/auth/*`, `/api/security/*`, `/api/consent`, `/api/privacy/*`

### Frontend
- `/settings/security` (sessions, 2FA, password)
- `/settings/privacy` (consents, LGPD rights)
- Cookie banner global
- Privacy policy modal versionado
- 2FA wizard
- Password reset flow
- Email verification flow

### Infra
- TLS via Caddy/Let's Encrypt
- Cloudflare na frente
- Backups automatizados off-site
- Sentry com PII scrubbing
- 1Password ou Vault pra secrets
- Status page setup

### Compliance docs
- Privacy Policy versionada (legal advice)
- Terms of Service
- DPA template (Enterprise)
- LGPD policy interno
- Incident response plan
- DR runbook

### Sprints
- **A (sem 1-2)**: 8.1, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11, 8.13, 8.14, 8.15, 8.16, 8.17, 8.22, 8.24, 8.25, 8.32, 8.33, 8.34 — security + auth + LGPD core
- **B (sem 3-4)**: 8.12, 8.18, 8.21, 8.23, 8.26, 8.30, 8.31, 8.35 — encryption + DR + status page
- **C (sem 5+)**: 8.2, 8.20, 8.28 — passkey + DPA + pentest
- **D (sem 7+)**: 8.3, 8.19, 8.27, 8.29 — SSO, GDPR, SOC 2, bug bounty
