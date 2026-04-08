# Contratos de Nao Regressao do Funil

Objetivo: impedir que atualizacoes futuras apaguem comportamentos vitais ja estabilizados.

## Regra geral de evolucao

- Nao remover comportamento existente sem substituir por mecanismo equivalente ou melhor.
- Nao apagar funcoes de protecao sem adicionar outra com a mesma finalidade.
- Toda mudanca em copy deve preservar os contratos operacionais abaixo.
- Se um contrato for alterado, atualizar este documento e o script `scripts/verificar_guardrails_funil.py`.

## Contratos por arquivo

### `conversation_policy.py` (camada central)

- Deve manter detector unico de problema de entrega (`lead_reportou_problema_entrega`).
- Deve manter resposta padrao de reparo (`acoes_reparo_entrega_padrao`).
- Mudanca de copy de reparo deve ser feita aqui primeiro, nao em cada node isolado.

### `app.py` (fila e debounce)

- Deve existir `LeadInboxManager`.
- Deve existir grace pos-texto com bypass para:
  - confirmacao curta (`ok/sim/salvo/...`);
  - feedback de entrega (`cortada/atropelando/card/...`).
- Deve logar `Batch pronto` com `silence_s`, `grace_extra` e `chars`.

### `engine.py` (orquestracao e entrega)

- Deve existir detector de problema de entrega do lead:
  - `_lead_reportou_problema_entrega`.
- Deve existir resposta de reparo:
  - `_acoes_reparo_entrega`.
- Deve existir pausa real apos pergunta:
  - `_ultima_fala_do_bot_e_pergunta`.
  - bloqueio de encadeamento para `6_atencao_dinamica` quando ultima fala for pergunta.
- Deve existir anti-corte final:
  - `_blindar_texto_final_anti_corte`.
- Deve existir cadencia anti-atropelo:
  - pausa antes de `vcard` apos texto;
  - pausa antes de `image/video` apos texto.
- Deve registrar telemetria de execucao de cada node:
  - evento `node_exec_timing` com `node`, `elapsed_s`, `acoes`, `prox`;
  - warning de SLA quando `elapsed_s` ultrapassa `node_exec_sla_warn_seconds` (default 6s em `CONFIG_CLIENTE`, override `NODE_EXEC_SLA_WARN_SECONDS`; engine fallback 3.5s se chave ausente).
- Deve injetar `node_atual_exec` em `ctx.metadata` antes de executar node para roteamento de economia de IA.

### `personalizer.py` (controle de custo)

- Deve aplicar guardrail de custo por lead (`_ia_tokens_gastos_aprox`) com modo economico progressivo.
- Deve respeitar teto de `max_output_tokens` por node quando `ia_economia.max_output_tokens_por_node` existir.
- Deve registrar consumo aproximado por chamada IA para evitar ciclo caro de retries.

### `flows/fase_2_leitura/node_5_processa_leitura.py`

- Deve coletar tentativas previas (`node5_tentativas_previas`) antes de seguir.
- Se faltarem tentativas, deve perguntar explicitamente e permanecer no `5_processa_leitura`.
- Deve salvar dado concreto (`node5_dado_concreto`) para eco nos proximos nodes.
- Deve tratar relato de entrega quebrada (corte/atropelo/travou) com reparo curto e retorno ao proprio node.

### `flows/fase_1_saudacao/node_1_apresentacao.py`

- Deve manter limite e saneamento final de baloes no inicio.
- Deve evitar repeticao de instituicao/vaga no mesmo turno.
- Deve manter pergunta final quando nome ainda nao estiver claro.
- Burst para coleta sem node 2 deve seguir `flows/funnel_gates.pode_burst_coleta_sem_node2` (ver `docs/FUNIL_MATRIZ_OBRIGATORIOS.md`).

### `flows/fase_1_saudacao/node_2_salvar_contato.py`

- Deve tratar feedback de entrega (mensagem cortada/atropelo/card) com reparo curto.
- Deve manter fast-track quando contato ja foi salvo.
- Deve manter cadencia sem textao e sem duplicar instrucao de salvar.

### `flows/fase_1_saudacao/node_4_instagram.py`

- Deve tratar link quebrado com fallback de @handle.
- Deve tratar feedback de entrega (cortada/atropelo) antes de continuar.
- Deve manter handoff para node 5 sem perder contexto.

### `flows/fase_2_leitura/node_6_atencao_dinamica.py`

- Prompt deve receber `dado_concreto`.
- Regra de bloco deve exigir uso de dado concreto no diagnostico (blocos centrais).
- Deve manter xeque-mate no bloco final com pergunta.
- Deve tratar relato de entrega quebrada com reparo curto e retomada do node.

### `flows/fase_2_leitura/node_7_interesse_desejo.py`

- Deve reagir ao ultimo input do lead no inicio:
  - `_reacao_curta_ao_input`.
- Deve ter fallback que nao ignora confirmacao/duvida do lead.
- Deve tratar relato de entrega quebrada com reparo curto e retomada do node.

### `flows/fase_3_oferta/node_8_oferta_principal.py`

- Deve exigir FIRMO/confirmacao antes do link.
- Deve manter escada de negociacao:
  - `130 -> 100 -> 50`
  - `65 -> 40 -> 30`
- Deve inserir ponte emocional antes do preco quando necessario:
  - `_eh_bloco_preco`
  - `_ponte_emocional_preco`.
- Deve tratar relato de entrega quebrada com reparo curto e retomada do node.

### `flows/fase_3_oferta/node_9_recuperacao.py`

- Deve manter linguagem simples e humana (sem texto literario longo).
- Deve manter 3 tentativas com tom progressivo (acolhimento -> urgencia honesta -> fechamento limpo).
- Deve manter link e contexto de dor/gatilho sem prometer milagre.

## Politica de seguranca anti-limbo

- Nao subir alteracao de node sem rodar:
  - `py -m py_compile` nos arquivos alterados;
  - `py scripts/verificar_guardrails_funil.py`.
- Antes de release, rodar simulacao ponta a ponta:
  - `py scripts/simular_funil_e2e.py`.
- Para release de producao, rodar gate consolidado:
  - `py scripts/release_gate_funil.py`
  - opcional com QA manual: `py scripts/release_gate_funil.py --qa-score-json scripts/qa_copy_score_template.json`
- Para monitorar custo/beneficio de IA por lead:
  - `py scripts/custo_ia_por_lead.py --dias 30`
- Se o guardrail falhar, corrigir antes de novo teste real.

