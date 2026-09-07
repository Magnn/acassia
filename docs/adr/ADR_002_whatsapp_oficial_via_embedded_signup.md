# ADR 002 — WhatsApp oficial via Embedded Signup, sem QR Code

**Status:** Aceito
**Data:** 2026-04-28
**Decisor:** Magno Alves
**Tags:** whatsapp, integração, onboarding

## Contexto

Pra clientes (tarólogos) conectarem o WhatsApp deles à plataforma, há dois caminhos:

1. **WhatsApp Cloud API oficial** (Meta) via Embedded Signup
2. **Soluções não oficiais** (Evolution API, Baileys, Z-API) via QR Code

O proprietário (Magno) é **Meta Developer** e tem App publicada — o que destrava o caminho oficial.

## Decisão

**Cloud API oficial via Embedded Signup**, sem QR Code. Onboarding manual nos primeiros 5-10 clientes enquanto App Review da Meta não aprovar.

## Justificativa

1. **QR Code é WhatsApp Web não oficial** — viola ToS, conta pode ser banida sem aviso
2. **Posicionamento incoerente:** ser dev Meta e usar caminho não oficial enfraquece a marca SaaS séria
3. **Nicho espiritual** já é zona cinza pra Meta — usar canal não oficial multiplica risco de banimento
4. **Cliente que paga R$97-497/mês não tolera "minha cigana caiu"** — uptime é parte do produto
5. **Cloud API tem analytics nativo** (quality rating, delivery, mensagens) — necessário pra cobrar bem
6. **Sem perpetuidade**: QR Code exige sessão sempre online (celular ou emulador) — vira manutenção infinita

## Caminho de execução

| Fase | Estratégia |
|---|---|
| 1-10 clientes (mês 1-2) | **Onboarding manual:** cliente dá acesso à BM dele, eu adiciono o número via dashboard Meta, copio `phone_number_id` no painel admin |
| 10-50 clientes (mês 3+) | **Embedded Signup self-service** após App Review aprovado |
| 50+ clientes | Avaliar virar **BSP / Solution Partner** formal |

## Consequências

**Positivas:**
- Caminho escalável e oficial desde o dia 1
- Sem risco de banimento em massa
- Quality Rating real, tier crescente legítimo
- Marca SaaS séria

**Negativas:**
- App Review Meta demora 2-8 semanas e pode pedir revisão
- Implementação do Embedded Signup tem complexidade (callback OAuth, tokens, BM linking)
- Cliente precisa de CNPJ ou se vincular ao seu BM via System User
- Onboarding manual nos primeiros clientes consome seu tempo

## Alternativas consideradas

1. **QR Code via Evolution API** — descartado: ToS, banimento, posicionamento
2. **Híbrido (QR pro plano starter, Cloud pro Pro)** — descartado: dobra a manutenção, mantém risco em parte da base
3. **Cloud API only com onboarding manual nos primeiros + Embedded depois** — escolhido

## Pré-requisitos técnicos

- [ ] Meta Business App publicada (✅ já existe)
- [ ] App Review pra `whatsapp_business_management`
- [ ] App Review pra `whatsapp_business_messaging`
- [ ] Embedded Signup configurado no Facebook Developer Console
- [ ] Endpoint de callback no backend (`/api/integrations/whatsapp/embedded-signup/callback`)
- [ ] Tabela `tenant_whatsapp_credentials` (phone_number_id, waba_id, access_token, refresh_token)
- [ ] Lookup `phone_number_id → tenant_id` em memória/cache pro webhook rotear

## Política de conteúdo Meta

Clientes que prometem **cura, medicina, garantia financeira absoluta** violam política Meta. Adicionar:
- [ ] Cláusula explícita no termo de uso do tenant
- [ ] Checklist no onboarding: "Você concorda em não prometer X, Y, Z"
- [ ] `response_validator.py` bloqueia output que use essas palavras

## Referências

- [Embedded Signup docs](https://developers.facebook.com/docs/whatsapp/embedded-signup)
- [WhatsApp Business Solution Provider Program](https://developers.facebook.com/docs/whatsapp/solution-providers)
- ADR_001 (sem Chatwoot — implica que somos os donos do canal)
