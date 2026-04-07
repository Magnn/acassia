# Checklist por etapa (funil Cigana — validação)

Use ao revisar um nó ou ao portar o modelo para outro negócio. Marque o que já está coberto no código/config.

| Etapa (node) | Objetivo da mensagem | Pré-requisitos | Próximo nó típico | Fallback se IA falhar | Pausar bot? |
|----------------|----------------------|----------------|--------------------|------------------------|-------------|
| `1_apresentacao` | Rapport + frame; captar nome | — | `2_...` | Texto curto pedindo nome | Não |
| `2_salvar_contato` | Identidade + contato salvo | Nome mínimo | `3_...` | Repetir pedido sem pressa | Não |
| `3_coleta_profunda` | Contexto emocional / foto / desabafo | Contato ok | `4_...` | Uma pergunta por vez | Não |
| `4_instagram` | Prova social leve | Contexto mínimo | `5_...` | Link fixo da config | Não |
| `5_processa_leitura` | Processar leitura | Dados da etapa anterior | `6`/`7` | Mensagem “processando” genérica | Não |
| `6` / `7` | Aprofundar desejo / tensão | Leitura entregue | `8_...` | Ancorar em etapa sem inventar preço | Não |
| `8_oferta_principal` | Oferta + valor + CTA | Funil maduro | `aguardando_pagamento` / `9` | Copy com preços da `CONFIG_CLIENTE` | Opcional |
| `9_recuperacao` | Recuperar abandono pós-oferta | Recovery stage | Variável | Templates registry | Não |
| `aguardando_pagamento` | Silêncio + ACK se lead escrever | PIX/link enviado | — | ACK curto (engine) | Não |
| `14_confirmacao_entrega` | Pós-compra | `convertido` | `15`/`16` | ACK curto (engine) | Opcional |
| `99_*` / `fluxo_encerrado` | Encerramento / opt-out | — | — | Uma linha de despedida | Sim se handoff |

**Histórico no Personalizer:** usar `slice_historico_para_ia(ctx)` (nunca `historico_lista=[]` se o engine já carregou mensagens) — senão a IA “esquece” o diálogo.

**Múltiplas perguntas no mesmo turno:** `stage_intel.varias_perguntas_detectadas` + Personalizer com prioridade na última mensagem — a IA deve endereçar todos os tópicos antes de só empurrar o roteiro.

**Métricas:** transições em `eventos_audit` (`funnel.node_transition`); silent ack em `funnel.silent_ack_user_text`. Scripts: `python scripts/metricas_semanais.py`, `python scripts/funnel_health_report.py --json relatorio.json`, `python scripts/lead_journey.py <lead_id>`.

**Pontes & posicionamento:** textos-base em `CONFIG_CLIENTE["pontes_copy"]` (env `PONTE_*`); promessa/para quem não é em `perfil_negocio`; guardrails em `copy_guardrails`. Glossário: `docs/GLOSSARIO_UBIQUO.md`.

**Config:** dados gerais do negócio em `CONFIG_CLIENTE["perfil_negocio"]` (`config_cliente.py` + variáveis `NEGOCIO_*` no `.env`).
