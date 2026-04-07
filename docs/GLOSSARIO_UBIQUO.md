# Glossário ubíquo (negócio ↔ código)

Termo de negócio | No código / banco | Significado
---|---|---
Etapa / fase | `node_atual`, `flows/` `node_*` | Um passo da FSM; arquivo `node_X_*.py` implementa.
Mensagem do lead | `Mensagem` remetente `user` | Texto (ou tipo mídia); histórico limitado no engine.
Intenção (IA) | `ctx.intencao`, `Lead.ultima_intencao` | Classificador Gemini; não muda nó sozinho.
Roteiro da etapa | `stage_intel.bloco_instrucao` | Instruções para o Personalizer; integra depois de responder ao lead.
Pontes de copy | `CONFIG_CLIENTE["pontes_copy"]` | Frases-base configuráveis (preço cedo, desconfiança, multi-tópico).
Guardrails | `copy_guardrails` | Tom e promessas a evitar (lista + `nao_prometer`).
Perfil de negócio | `perfil_negocio` | Quem é, oferta, promessa, para quem não é, prova curta.
Recuperação | `recovery_stage`, `RecoveryEngine` | Sequência 5/60/180 min; evento `recovery_disparado`.
Transição de funil | `EventoAudit` `funnel.node_transition` | De → para nó, sem PII no JSON.
Estado silencioso | `aguardando_pagamento`, etc. | Engine não roda node; pode mandar ACK; evento `funnel.silent_ack_user_text`.
Experimento | `experiments/registry.py` | Hipótese + métrica alvo (registro manual; não liga A/B automático ainda).
Histórico para IA | `slice_historico_para_ia(ctx, limite)` em `schema.py` | Últimas mensagens passadas ao Personalizer (nunca lista vazia se houver histórico).

Atualize este ficheiro quando criar novos nós ou nomes de evento.
