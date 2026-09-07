# Estratégia de Frontend — Fase 3 e além

> Decisão pendente do [SAAS_ROADMAP](SAAS_ROADMAP.md) sobre como construir o painel SaaS multi-tenant. Análise + decisão + plano de execução pra Fase 3.

---

## Contexto

A Fase 3 do roadmap precisa entregar:
1. Login / cadastro de tarólogos
2. Wizard de onboarding (4 passos: persona, oferta, template, WhatsApp)
3. Inbox de conversas + takeover humano
4. Métricas básicas por tenant
5. Settings (recovery cadence, oráculo, integração Stripe Connect, etc)

Pergunta: **construir em React/Next.js separado ou estender o `dashboard.html` existente em Jinja/HTML?**

## Inventário do que já existe

[dashboard.html](../dashboard.html) tem **1.1MB** com:
- Flow Builder canvas funcional (sidebar de nós, drag-and-drop, modal de inspetor, undo/redo, versões)
- Estúdio de IA com 3 abas (Personalidade / Conhecimento / Restrições)
- Modal de devices/dispositivos
- Modal de novo fluxo + criação de pasta
- Sistema de toasts e overlays
- Tema dark com Tailwind + ícones FontAwesome

Não tem: login/auth, lista de conversas (inbox), métricas, billing, wizard de onboarding.

## 3 caminhos

### Opção A — Reescrever em Next.js / React

Migrar o dashboard inteiro pra app moderno (Next.js 15 + Tailwind + shadcn/ui).

**Prós:**
- Componentização limpa, devexp moderna
- Integração trivial com Stripe Elements, Embedded Signup Meta (componentes oficiais)
- SSR ajuda SEO da landing/marketing
- Mais fácil contratar dev frontend

**Contras:**
- **Reescrever 1.1MB de canvas funcional = 3-6 meses**
- Bloqueia shipping de SaaS por meses
- Risco real de perder feature parity (canvas está sofisticado)
- Custo de manutenção dual durante migração

### Opção B — Estender HTML/Jinja existente (recomendado)

Adicionar novas páginas em Jinja (login, onboarding, inbox, settings) **mantendo o dashboard.html** como está.

**Prós:**
- Zero risco de regressão no canvas
- Ship em **3-4 semanas** vs 3-6 meses
- Reutiliza Tailwind / FontAwesome / tema dark já no dashboard
- Login e settings são páginas simples — Jinja serve perfeitamente
- Inbox pode usar HTMX ou fetch + DOM partial (sem framework pesado)
- Canvas sofisticado fica intocado durante crescimento

**Contras:**
- Dívida técnica futura (HTML cru envelhece)
- Stripe Elements + Embedded Signup ficam um pouco mais quebrados (precisam JS adhoc)
- Inbox em tempo real fica menos elegante (SSE/polling em vez de WebSocket via React state)

### Opção C — Híbrido: Jinja shell + React islands em pontos críticos

Páginas simples (login/settings) em Jinja. Componentes complexos (Stripe Connect onboarding, Embedded Signup, gráficos de métricas) como ilhas React montadas via `<div id="..."></div>` + bundle isolado.

**Prós:**
- Melhor das duas: simplicidade onde basta + ferramenta certa onde dói
- Migração gradual (dá pra começar Jinja-only e adicionar ilhas depois)

**Contras:**
- Dois tooling no mesmo projeto (Jinja + Vite/esbuild pra ilhas)
- Curva de aprendizado pra colaboradores

---

## Decisão: **Opção B agora, evoluindo pra C nas ilhas críticas**

**Razões:**
1. Time-to-revenue manda: vender pros primeiros 5-10 clientes em 6-8 semanas é mais valioso que arquitetura perfeita
2. Canvas existente é o ativo de produto — reescrever = perder vantagem competitiva por 3+ meses
3. Stripe Elements e Embedded Signup têm integração via `<script>` direto — não exigem React
4. Quando Stripe Connect onboarding for muito frágil em vanilla JS, plugamos uma ilha React isolada (pattern conhecido: Vite `library mode` + 1 bundle por ilha)

**Quando reavaliar:**
- Após 30+ tenants ativos OU 6+ meses de operação contínua
- Se 2+ devs frontend precisarem ser contratados em paralelo (React contrata mais fácil)

---

## Plano da Fase 3 (sob Opção B)

Estrutura nova de templates Jinja:

```
templates/
├── base.html                    # layout common (header, sidebar, theme dark)
├── auth/
│   ├── login.html
│   └── signup.html
├── onboarding/
│   ├── wizard.html              # shell com 4 steps
│   ├── _step_persona.html
│   ├── _step_oferta.html
│   ├── _step_template.html
│   └── _step_whatsapp.html
├── inbox/
│   ├── lista.html               # lista de conversas + filtros
│   └── _conversa.html           # partial pra HTMX swap
├── settings/
│   ├── recovery.html            # cadência por tenant (ADR_005)
│   ├── stripe.html              # status Connect + relink
│   └── whatsapp.html            # phone_number_id, quality rating
└── metricas/
    └── dashboard.html           # KPIs + gráficos
```

Endpoints novos em `api/saas/` (substituindo escopo do app.py monolítico):

```
api/saas/
├── auth.py                      # /signup, /login, /logout
├── onboarding.py                # /onboarding/* (4 passos)
├── inbox.py                     # /inbox/lista, /inbox/{id}, /inbox/{id}/takeover
├── settings.py                  # /settings/* (read/write TenantFlowVariable)
└── metricas.py                  # /metricas/dashboard
```

Tudo registrado como Flask Blueprint (não vai pro app.py monolítico).

### Tarefas e estimativas

| Tarefa | Estimativa | Status |
|---|---|---|
| Auth (signup/login/logout via flask-login + bcrypt) | 3 dias | ✅ feito (~1h, 32 testes) |
| Wizard onboarding (4 passos + validação) | 4 dias | ✅ feito (~1.5h, 29 testes) |
| Stripe Subscriptions (planos Starter/Pro/Premium + webhook) | 3 dias | ✅ feito (~2h, 30 testes) |
| Stripe Connect Express (onboarding KYC + return) | 2 dias | ✅ feito (~1h, 6 testes) |
| Inbox UI + takeover (refresh-based, polling em V2) | 4 dias | ✅ feito (~1.5h, 9 testes) |
| Settings (recovery + Stripe + WhatsApp) | 3 dias | ✅ feito (~1h, 7 testes) |
| Métricas com KPIs + node distribution | 3 dias | ✅ feito (~1h, 5 testes) |
| Stripe Connect Express (onboarding link + callback) | 2 dias | 🔴 pendente |
| **Total estimado** | **~22 dias úteis (~4-5 semanas)** | **7/7 feito 🎉** |

### Dependências bloqueantes

- [ ] [tenant_config.py](../api/tenant_config.py) já existe ✅
- [ ] Migração [config_cliente.py](MIGRACAO_CONFIG_CLIENTE.md) Fase 1-2 (consumidores migrarem) — pode rodar em paralelo
- [ ] [ENGINE_QUEUE_INTEGRATION.md](ENGINE_QUEUE_INTEGRATION.md) Opção A executada (fecha Fase 2) ✅
- [ ] App Review Meta pra Embedded Signup — paralelo, não bloqueia Modo B (manual) do passo 4

---

## Tooling decidido

| Stack | Escolha |
|---|---|
| Templates | Jinja2 (já no Flask) |
| CSS | Tailwind CSS via CDN (mantém parity com dashboard.html) |
| Ícones | FontAwesome via CDN (parity) |
| Interatividade | HTMX 2.0 (substitui maioria do JS adhoc; partials Jinja swappable) |
| Gráficos | Chart.js (CDN) |
| Stripe UI | Stripe.js v3 (vanilla, sem React) |
| Realtime inbox | Polling 3s via HTMX (V1); migração pra SSE em V2 |
| Forms | WTForms (validação serverside) |

Sem build step. Adicionar `flask-wtf` (CSRF + WTForms) como única dep nova.

---

## Migração futura pra ilhas React (V2, opcional)

Quando algum componente vira inviável em vanilla JS (ex: Stripe Connect KYC com upload de documento, ou um gráfico de funil interativo complexo), plugamos uma ilha React isolada:

```
frontend_islands/
├── stripe_connect_onboarding/   # 1 componente, 1 bundle
│   ├── index.tsx
│   └── package.json
├── funnel_chart/
│   └── ...
└── shared/
    └── api_client.ts
```

Build via Vite library mode. Cada bundle ~30KB. Mount via:
```html
<div id="stripe-connect-island" data-tenant="{{ tenant.id }}"></div>
<script type="module" src="/static/islands/stripe_connect_onboarding.js"></script>
```

**Nota:** isso é V2 — não fazer agora.

---

## Definições pra começar

- [ ] Criar `templates/base.html` com layout shell que combina com [dashboard.html](../dashboard.html) (mesmo tema, sidebar)
- [ ] Adicionar `flask-wtf` ao [requirements.txt](../requirements.txt)
- [ ] Adicionar HTMX 2 e Chart.js ao layout base (CDN)
- [ ] Decidir biblioteca de auth: built-in (cookie + bcrypt + JWT) ou `flask-login` + `bcrypt`
  - **Sugestão:** `flask-login` + `bcrypt` (padrão da indústria, pouca code, fácil testar)

## Próximos passos sugeridos

1. Aprovar essa estratégia
2. Atacar Auth como primeiro componente (3 dias)
3. Wizard onboarding em paralelo
4. Inbox por último (depende de auth + tenant_id no contexto)
