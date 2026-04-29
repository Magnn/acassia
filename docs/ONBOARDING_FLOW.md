# Fluxo de Onboarding — Tarólogo entra na plataforma

> Wireframe textual do wizard de 4 passos e telas pós-ativação. Detalhe pra design de UX e implementação de frontend.

---

## Fluxo geral

```
[Landing /signup]
    ↓
[Cadastro: email + senha + plano Stripe]
    ↓
[Wizard 4 passos]
    ↓
[Painel principal: 4 abas]
    ↓
[Ativação → cigana entra no ar]
```

---

## Passo 0 — Cadastro

**Tela:** form simples (email, senha, nome, CPF / CNPJ)

**Plano:** seletor com 3 cards (Starter R$97 / Pro R$297 / Premium R$497) — Stripe Checkout

**Após confirmação:**
- `tenant_id` gerado (UUID)
- `tenant.status = 'pending_onboarding'`
- `Lead`, `Mensagem`, `StudioAgent` etc tudo isolado por esse tenant_id
- Email de boas-vindas com link pro wizard

---

## Passo 1 — Persona da Cigana

**Tela:** form de 5 campos

| Campo | Exemplo | Onde grava |
|---|---|---|
| Nome | "Madame Eros" | `StudioAgent.name` |
| Foto / avatar | upload ou seletor | `StudioAgent.avatar` |
| Tom de voz | dropdown: acolhedor / direto / místico / sedutor | `StudioAgentVersion.body_json.tone` |
| História de origem | textarea ~200 chars | `StudioAgentVersion.body_json.backstory` |
| Restrições | checkboxes (não promete cura, não fala sobre saúde, etc) | `StudioAgentVersion.body_json.restrictions` |

**Critério de feito:** ao clicar "Próximo", cria `StudioAgent` + `StudioAgentVersion` v1.

---

## Passo 2 — Oferta + pagamento

**Tela:** form de oferta principal + opção de upsell

| Campo | Exemplo |
|---|---|
| Nome do produto | "Tiragem de Emergência" |
| Preço | R$ 19,90 |
| Descrição curta | "3 cartas reveladas por Madame Eros, em até 5 minutos" |
| Stripe Connect | botão "Conectar Stripe" — abre onboarding Express |
| Upsell (opcional) | nome + preço + descrição de produto seguinte |

**Critério de feito:**
- Conta Stripe Express criada e linkada ao tenant
- `TenantFlowVariable` populada com produto + preço
- Status `tenant_stripe_connect.payouts_enabled = true`

---

## Passo 3 — Escolha de template

**Tela:** 3 cards visuais

| Card | Oráculo | Descrição | Indicado pra |
|---|---|---|---|
| **Tiragem Express** | Tarot (78 cartas Marselha) | Funil curto R$19-49, alto volume, recorrência via "Tiragem Mensal" | Quem quer escala |
| **Consulta Premium** | Quiromancia (linhas da mão) | Funil longo R$197+, qualificação profunda, upsell pra mentoria | Quem quer ticket alto |
| **Em branco** | Configurável | Canvas vazio pra montar do zero (qualquer oráculo, qualquer ticket) | Quem já sabe o que faz |

Cada template é um `FlowBlueprint` semente que é **clonado pro tenant** ao escolher.

**Critério de feito:** `FlowBlueprint` clonado, `FlowPublish` apontando pra ele.

Detalhes dos templates:
- [TEMPLATE_TIRAGEM_EXPRESS](templates/TEMPLATE_TIRAGEM_EXPRESS.md)
- [TEMPLATE_CONSULTA_PREMIUM](templates/TEMPLATE_CONSULTA_PREMIUM.md)

---

## Passo 4 — Conectar WhatsApp

Uma das três experiências (depende do estado do App Review — ver [ADR_002](adr/ADR_002_whatsapp_oficial_via_embedded_signup.md)):

### Modo A — Embedded Signup (após App Review aprovado)

Botão "Conectar com Facebook" → popup oficial Meta → callback → grava `phone_number_id`, `waba_id`, `access_token` em `tenant_whatsapp_credentials`.

### Modo B — Manual (durante App Review / primeiros clientes)

Tela mostra:
1. "Adicione `noreply@plataforma.com` como admin no seu Business Manager"
2. "Compartilhe o ID do número do WhatsApp Business" (campo)
3. "Aguarde 1 dia útil — vamos confirmar e te avisar"

Status do tenant: `pending_whatsapp_link`. Admin (você) recebe email, valida no Meta, atualiza credenciais no painel admin, libera tenant.

### Modo C — Sandbox de teste (opcional)

Permite testar todo o fluxo num número de teste da plataforma antes de conectar o número real. Útil pra cliente experimentar antes de fazer KYC do Connect.

**Critério de feito:** webhook `/webhook` recebe mensagem do número configurado e roteia pro `tenant_id` correto via lookup `phone_number_id → tenant_id`.

---

## Painel principal (pós-ativação)

**Layout:** 4 abas no topo + sidebar com persona + status

### Aba 1 — Inbox

- Lista de conversas (filtros: ativas / pausadas / convertidas / perdidas)
- Ao clicar: histórico da conversa + botão "humano assume" (toggle `Lead.bot_pausado`)
- Busca por telefone / nome
- Indicadores: fase do funil, score, última intenção, sentimento

### Aba 2 — Canvas (Flow Builder)

- Já existe em `dashboard.html`, falta só conectar ao `tenant_id` real
- Carrega o blueprint clonado do template escolhido no passo 3
- Cliente edita, publica nova versão
- Botão "Testar com lead fictício"

### Aba 3 — Agente IA

- 3 sub-abas: **Personalidade / Conhecimento (FAQ) / Restrições**
- Já existe em `dashboard.html` (linhas ~8662-8715), falta `tenant_id` real
- Botão "Treinar / Republicar" → cria `StudioAgentVersion` nova e ativa

### Aba 4 — Métricas

- KPIs por dia: leads novos, conversas ativas, conversões, GMV, ticket médio, LTV estimado
- Gráficos: funil (saudação → leitura → oferta → checkout → entrega), drop-off por etapa
- **Custo de IA por tenant** (Gemini tokens) — pra cliente ver e pra você medir margem

---

## Ativação final

Botão **"Publicar Cigana"** no header (visível em todas as abas):

1. Valida: persona completa, oferta com Stripe ok, blueprint publicado, WhatsApp conectado
2. Marca `tenant.status = 'live'`
3. Envia mensagem de teste do bot pro próprio celular do tarólogo
4. Email de confirmação
5. A partir desse momento: webhook Meta encaminha mensagens daquele `phone_number_id` pro engine deste tenant

---

## Estados do tenant (state machine)

```
pending_onboarding
    ↓ (passos 1-3 concluídos)
pending_whatsapp_link
    ↓ (Modo A automático ou Modo B manual aprovado)
ready_to_publish
    ↓ (botão "Publicar Cigana")
live
    ↓ (inadimplência ou cancelamento)
suspended → cancelled (após 30 dias) → deleted (após 90 dias, conforme LGPD)
```

---

## Pontos de atenção UX

1. **Zero conhecimento técnico** — tarólogo é profissional espiritual, não dev. Linguagem evita jargão (não falar "blueprint", "tenant_id", "API")
2. **Salvamento automático** — wizard pode ser interrompido, retomar de onde parou
3. **Skip pra power user** — quem já entende, pula templates e vai direto pro canvas em branco
4. **Onboarding tour** após primeira ativação — mostra cada aba em 90s
5. **Suporte 1-clique** — botão "Falar com a equipe" sempre visível durante onboarding
6. **Idioma:** PT-BR por padrão; EN/ES no roadmap pra Fase 6

---

## Implementação técnica — esqueleto de endpoints

```
POST /api/auth/signup            → cria tenant + Stripe Customer
POST /api/auth/login             → JWT com tenant_id

POST /api/onboarding/persona     → passo 1 (cria StudioAgent)
POST /api/onboarding/offer       → passo 2 (cria oferta + Stripe Connect link)
POST /api/onboarding/template    → passo 3 (clona blueprint)
POST /api/onboarding/whatsapp    → passo 4 (Modo A: callback Embedded; Modo B: queue admin)

POST /api/tenant/publish         → ativação final
GET  /api/tenant/status          → state machine

POST /webhook                    → Meta WhatsApp (já existe, adicionar lookup phone_id→tenant)
POST /webhook/stripe             → Stripe events (subscription, payment, connect)
```
