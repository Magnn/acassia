# ADR 001 — Sem Chatwoot

**Status:** Aceito
**Data:** 2026-04-28
**Decisor:** Magno Alves
**Tags:** infraestrutura, whatsapp, inbox

## Contexto

A pasta `cigana_tarot/` documenta uma arquitetura paralela onde Chatwoot serve como middleware entre WhatsApp Cloud API e a lógica de negócio (n8n).

O `projeto_cigana` (este repositório) **nunca dependeu de Chatwoot** — `api/whatsapp_api.py` fala direto com `graph.facebook.com/v21.0` e `app.py:3674` tem webhook Meta nativo. Modelos de inbox (`Mensagem`, `Lead.bot_pausado`, `WhatsAppInboundReceipt`) já existem no banco.

A questão era: pra evoluir como SaaS multi-tenant, mantemos Chatwoot como inbox / UI de atendimento humano ou construímos o nosso?

## Decisão

**Não usaremos Chatwoot.** Construiremos inbox próprio dentro do dashboard SaaS.

## Justificativa

1. **Multi-tenant em Chatwoot é dor:** provisionar inbox por cliente, isolar contas, repassar credenciais — gargalo operacional
2. **White-label nativo:** cliente final do SaaS verá só nossa marca, não logo do Chatwoot
3. **Zero dívida atual:** `projeto_cigana` já tem `Mensagem`, `Lead.bot_pausado`, `WhatsAppInboundReceipt` — toda a base de dados de inbox já existe
4. **Custo Chatwoot** cresce por tenant; nosso DB já é multi-tenant
5. **UX específica do funil:** inbox no nosso dashboard pode mostrar fase do funil, score de conversão, próxima ação sugerida — Chatwoot é genérico

## Consequências

**Positivas:**
- Controle total sobre dados e UX
- Sem dependência operacional externa
- White-label desde o dia 1
- Custo previsível (não paga por agente/conversa)

**Negativas:**
- 2-3 semanas de frontend pra inbox (lista conversas, conversa individual, takeover, busca)
- Realtime via WebSocket / SSE precisa ser implementado (Chatwoot dava de graça)
- Manutenção da UI de chat fica com a gente

## Alternativas consideradas

1. **Chatwoot multi-instance** (1 instância por cliente) — descartado: custo linear, complexidade operacional
2. **Chatwoot single-instance multi-account** — descartado: vazamento de dados entre clientes possível, UI não white-label
3. **Inbox próprio** — escolhido

## Implicações operacionais

- Pasta `cigana_tarot/` fica como **referência histórica**, não roda em produção
- Os 10 fluxos n8n não migram literalmente — viram **blueprint do canvas** (template "Tiragem Express")
- `cigana_tarot/DEPLOY.md` fica obsoleto

## Referências

- `cigana_tarot/DEPLOY.md` (arquitetura descartada)
- `db/models.py` (modelos de inbox já existentes)
- `api/whatsapp_api.py` (envio Meta direto)
- `app.py:3674` (webhook Meta nativo)
