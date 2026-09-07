# ADR 003 — Stripe (Subscriptions + Connect Express)

**Status:** Aceito
**Data:** 2026-04-28
**Decisor:** Magno Alves
**Tags:** pagamentos, billing, split

## Contexto

A plataforma SaaS tem **dois fluxos de pagamento distintos**:

1. **Assinatura SaaS** — tarólogos pagam mensalidade (R$97-497/mês) pra usar a plataforma
2. **Pagamento end-user** — leads dos tarólogos pagam pelas consultas (R$19,90 a R$197+) processado pela plataforma com **split automático** (% pra plataforma, restante pro tarólogo)

Atualmente a `cigana_tarot/` usa **Cakto** para o fluxo end-user. **Asaas** foi considerado por ser Brasil-first com Pix recorrente nativo.

## Decisão

**Stripe** para ambos os fluxos:
- **Stripe Subscriptions** pra cobrança SaaS recorrente
- **Stripe Connect Express** com `application_fee_amount` pra split automático no pagamento end-user

## Justificativa

1. **DX e dashboard superiores** — observabilidade, analytics, refunds, disputas tudo num só lugar
2. **Stripe Connect Express é o split mais maduro do mercado** — onboarding KYC do tarólogo simplificado, payout direto na conta dele
3. **Internacional** — futuro de vender pra clientes em Portugal, EUA, etc, vira só ligar moedas
4. **API e webhooks rock-solid** — menos lógica de retry/idempotência manual
5. **Stripe Tax / Invoicing** facilita conformidade fiscal quando crescer
6. **Decisão do dono** — solicitada explicitamente

## Consequências

**Positivas:**
- Plataforma unificada de pagamentos
- KYC e compliance terceirizados pra Stripe
- Split sem reconciliar manualmente
- Cliente Stripe = perfil mais "tech maduro"

**Negativas:**
- **Pix recorrente nativo Stripe** ainda não é primeira-classe no Brasil. Pix one-shot funciona. Mitigação: cartão pra recorrência da assinatura SaaS, Pix pra cobrança end-user one-shot
- **Taxas mais altas no Brasil** — Stripe ~3.99% + R$ 0.39 por Pix vs Asaas R$ 1.99 fixo. Em GMV alto pesa
- Onboarding do tarólogo via Connect exige **KYC mais rigoroso** (CPF, foto documento, dados bancários)
- Categorias **espiritualidade / tarot** podem entrar em revisão extra do Stripe Risk

## Plano de implementação

### Fase 3 — Assinatura SaaS

- [ ] Conta Stripe (live + test) configurada
- [ ] Produtos: Starter R$97/mês, Pro R$297/mês, Premium R$497/mês
- [ ] Webhook `customer.subscription.*` → atualiza `tenant.status`
- [ ] Inadimplência: tenant perde acesso ao dashboard, dados ficam preservados por 30 dias
- [ ] Customer Portal pra tarólogo gerenciar plano

### Fase 4 — Split end-user

- [ ] Stripe Connect Express por tenant
- [ ] Onboarding link gerado na ativação do tenant (passo 2 do wizard)
- [ ] Tabela `tenant_stripe_connect` (account_id, status, payouts_enabled)
- [ ] Cobrança end-user via PaymentIntent com `application_fee_amount` (% configurável por plano)
- [ ] Webhook `payment_intent.succeeded` → libera entrega da consulta

## Riscos específicos

1. **Categoria de risco no Stripe** — espiritual / tarot pode receber chargebacks acima da média.
   **Mitigação:** descrição clara do produto ("consulta de aconselhamento espiritual"), termo de aceite registrado, política de reembolso clara, prova de entrega
2. **Pix recorrente** — solução: cartão default na assinatura SaaS, Pix one-shot pra cobrança end-user
3. **Taxa Stripe vs Asaas** — em GMV de R$ 100k/mês, diferença é ~R$ 2k/mês a mais com Stripe. Avaliar migração ou stack híbrido se margem apertar
4. **Connect Onboarding KYC** — alguns tarólogos podem desistir no fluxo. **Mitigação:** explicar passo a passo no wizard, suporte 1-clique, opção de upload manual de documento

## Coexistência com Cakto (legado, transição)

A `cigana_tarot/` original já usa Cakto e há `api/cakto_api.py` funcional. Pra não bloquear os primeiros betas com KYC do Stripe Connect:

### Política de gateway por fase

| Fase | Política |
|---|---|
| Beta 1-5 | Tenant escolhe entre Stripe Connect ou Cakto. Quem já tem conta Cakto pode continuar pra ganhar velocidade |
| Beta 6-10 | Stripe vira default; Cakto continua possível mas marcado como "legado" |
| Beta 11+ | Stripe único pra clientes novos; tenants antigos com Cakto seguem normal (grandfathering) |
| GA público | Cakto removido do onboarding; só Stripe |

### Implementação técnica

**Templates de funil são gateway-agnósticos.** O nó "enviar link de pagamento" no blueprint lê `TenantFlowVariable.gateway_padrao`:

```python
gateway = get_tenant_var(tenant_id, "gateway_padrao", default="stripe")
if gateway == "stripe":
    link = stripe_connect.create_payment_intent(...)
elif gateway == "cakto":
    link = cakto_api.resolve_checkout_url(...)
```

Webhook handlers vivem em paralelo:
- `app.py:/webhook/stripe` → eventos Stripe (Subscriptions + Connect)
- `app.py:/webhook/cakto` → eventos Cakto (já existe rota — completar handler conforme G4 do GAP doc)

### Benefícios da coexistência temporária

- Tira fricção de KYC do MVP
- Permite migração gradual de clientes legados sem quebrar conversão deles
- Templates ficam mais robustos (gateway-agnóstico é boa prática mesmo a longo prazo)

## Alternativas consideradas

1. **Asaas (Brasil-first)** — descartado: solicitação do dono pra Stripe, internacionalização futura
2. **Cakto único** — descartado: fraco em recorrência e split, Brasil-only; mantido só como legado/transição
3. **Mercado Pago + Pagar.me** — descartado: DX inferior, integração mais quebradiça
4. **Híbrido Stripe (SaaS) + Asaas (end-user)** — possível trocar futuramente se taxa apertar

## Segurança operacional

- **Chaves secretas** (`sk_live_*`) **nunca** em código, chat, Slack, GitHub, screenshots
- Variável de ambiente em `.env` (já no `.gitignore`)
- Em produção: secret manager (Supabase Vault, AWS Secrets Manager, ou similar)
- Rotação de chaves a cada 6 meses ou imediatamente se exposta
- Webhook signing secret obrigatório (`Stripe-Signature` header)

## Referências

- [Stripe Connect Express](https://stripe.com/docs/connect/express-accounts)
- [Stripe Subscriptions](https://stripe.com/docs/billing/subscriptions/overview)
- [Stripe Brazil pricing](https://stripe.com/br/pricing)
- ADR_001 (sem Chatwoot — pagamento integrado ao nosso dashboard)
