# ADR 006 — Sub-fluxo de pós-pagamento: híbrido (Python core + blueprint editável)

**Status:** Aceito
**Data:** 2026-04-28
**Decisor:** Magno Alves
**Tags:** pagamentos, blueprints, arquitetura

## Contexto

Quando Stripe ou Cakto confirma pagamento via webhook, o sistema precisa:

1. **Validar e registrar** (signature, idempotência, audit) — responsabilidade técnica
2. **Marcar lead como convertido** — responsabilidade técnica
3. **Executar entrega** (mensagem confirmação, tiragem completa, upsell, recorrência) — responsabilidade de **experiência**

A questão era: tudo isso vive em Python hardcoded, tudo no blueprint do canvas, ou separado?

## Decisão

**Híbrido.** Webhook handler em Python faz o core técnico (blindado, não-editável). Em seguida dispara um **blueprint editável** chamado `post_payment` que o cliente customiza no canvas.

## Justificativa

1. **Idempotência e segurança não podem ser editáveis** — se cliente quebra (sem querer ou não), processa duplicado, vaza dado, gera reembolso indevido
2. **Experiência tem que ser editável** — entrega genérica é o oposto do que SaaS de funil entrega como valor
3. **Reuso do canvas que já existe** — o flow_executor compila e executa blueprints; reaproveitar
4. **Versionamento natural** — `FlowBlueprintVersion` versiona alterações do cliente, com rollback
5. **Separação de responsabilidades** — Python cuida do "técnico"; canvas cuida do "experiência". Linha clara

## Implementação concreta

### Fluxo end-to-end

```
[Stripe/Cakto webhook]
        ↓
[app.py:/webhook/{provider}]
        ↓
1. Valida signature (Stripe-Signature ou x-cakto-signature)
2. Idempotência (PaymentEventReceipt.event_id)
3. Carrega Lead (lookup por customer_email/phone/metadata)
4. Update: Lead.convertido=True, produto_comprado, data_pagamento
5. EventoAudit.evento="payment_approved"
6. flow_executor.execute_blueprint(slug="post_payment", lead_id=lead.id)
        ↓
[Blueprint "post_payment" — editável pelo cliente]
   ├─ Trigger: webhook.payment.approved
   ├─ Mensagem confirmação ("Pagamento confirmado, suas cartas estão sendo preparadas...")
   ├─ Aguarda 30s
   ├─ Nó motor_ref: enviar tiragem completa (chama função Python validada)
   ├─ Aguarda configurável (padrão 1h)
   ├─ Mensagem de upsell / recorrência
   └─ Marca lead com tag "convertido_express"
```

### Modelo novo necessário

`PaymentEventReceipt` (análogo ao `WhatsAppInboundReceipt`):

```python
class PaymentEventReceipt(Base):
    __tablename__ = "payment_event_receipts"
    __table_args__ = (UniqueConstraint("tenant_id", "provider", "event_id"),)

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(32), nullable=False)  # 'stripe' | 'cakto'
    event_id = Column(String(128), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    raw_payload = Column(JSON)
    processed_at = Column(DateTime(timezone=True), default=_agora_utc)
```

### Validador obrigatório do blueprint `post_payment`

Pra proteger o cliente de si mesmo, ao publicar um blueprint do tipo `post_payment` o `flow_builder_runtime.py` valida:

| Validação | Critério |
|---|---|
| Trigger correto | Único trigger é `webhook.payment.approved` |
| Confirmação obrigatória | Pelo menos 1 nó de mensagem nos primeiros 60s |
| Sem loop infinito | Não permitir trigger se referindo a si mesmo |
| Sem chamada externa não-autorizada | HTTP só com `FLOW_BLUEPRINT_ALLOW_HTTP=1` |
| Tag de conversão | Pelo menos 1 nó marcando lead como `convertido` (audit) |

Se falhar, publish é rejeitado com mensagem de erro UX-friendly ("Seu fluxo precisa de uma mensagem de confirmação nos primeiros 60 segundos").

### Defaults por template

Cada template ao ser clonado também cria um blueprint `post_payment` semente:

| Template | Blueprint pós-pagamento padrão |
|---|---|
| Tiragem Express | `post_payment_express`: confirmação → tiragem completa em 30s → recorrência mensal em 24h |
| Consulta Premium | `post_payment_premium`: confirmação → link de agendamento → nutrição em 3 dias → upsell mentoria em 7 dias |
| Em branco | sem blueprint pós-pagamento (cliente desenha do zero) |

## Consequências

**Positivas:**
- Cliente diferencia experiência sem mexer em código
- Core técnico blindado contra erro humano
- Reuso da infra do canvas
- Versionamento e rollback grátis (`FlowBlueprintVersion`)

**Negativas:**
- Linha cinza entre "core" e "experiência" exige documentação clara pro cliente entender o que pode editar
- Mais peças interligadas — debug pode ficar mais difícil
- Validador do blueprint é trabalho extra (~1 dia)
- Implementação total maior (~5 dias vs 2 da opção hardcoded)

## Limites do escopo (o que NÃO entra no blueprint editável)

Cliente **não pode** mexer em:
- Validação de signature do webhook
- Marcação de `Lead.convertido` (acontece no Python antes do dispatch)
- Idempotência (PaymentEventReceipt)
- EventoAudit
- Atualização de campos `produto_comprado`, `data_pagamento`

Cliente **pode** mexer em:
- Mensagens enviadas pós-pagamento
- Timing entre mensagens
- Upsell e recorrência
- Tags adicionais
- Ramos condicionais (ex: cliente novo vs recorrente)

## Alternativas consideradas

1. **A. Tudo em blueprint canvas** — descartado: idempotência e signature não podem ser editáveis
2. **B. Tudo hardcoded em Python** — descartado: cliente não customiza, desperdiça canvas que já existe (~50% do valor SaaS)
3. **C. Híbrido (escolhido)** — equilíbrio entre blindagem técnica e flexibilidade UX
4. **D. Blueprint imutável por tenant** (Python dispara, mas não editável) — descartado: equivalente à opção B mas com complexidade extra

## Impacto no GAP

G5 do [GAP_ENGINE_VS_CIGANA_TAROT.md](../GAP_ENGINE_VS_CIGANA_TAROT.md) cresce de 2 dias pra **5 dias**:

- G5a (2 dias): webhook handler core (validação, idempotência, audit, dispatch)
- G5b (2 dias): blueprints semente (`post_payment_express`, `post_payment_premium`) + clone no onboarding
- G5c (1 dia): trigger `webhook.payment.approved` no flow_executor + validador de blueprint

Total da Fase 2 sobe de **2-3 semanas pra ~3 semanas**.

## Referências

- `flow_executor.py` — onde o execute_blueprint é chamado
- `flow_builder_runtime.py` — onde o validador do tipo `post_payment` será adicionado
- `db/models.py` — receberá `PaymentEventReceipt`
- ADR_001 (sem Chatwoot — somos donos do webhook)
- ADR_003 (Stripe + Cakto coexistem — webhook handler é por provider)
- [GAP_ENGINE_VS_CIGANA_TAROT.md](../GAP_ENGINE_VS_CIGANA_TAROT.md) — G5 detalhado
