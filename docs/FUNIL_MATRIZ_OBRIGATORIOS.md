# Matriz — obrigatórios da fase 1 (nome, contato, foto, desabafo)

Documento vivo: alinhado ao código em `flows/funnel_gates.py` e ao sniffer em `engine.py` (metadata).

## Princípios de produto

1. **Sem nome utilizável** → o bot **pergunta o nome** antes de tratar o lead como identificado (não confundir “sim/ok” com identidade).
2. **Sem contato salvo / declarado** → ritual do **node 2** (vcard + confirmação humana); não assumir que “sim” = gravou na agenda.
3. **Foto da mão + desabafo com substância** → **node 3** (coleta); o sniffer pode antecipar flags quando a mídia/texto já chegaram no mesmo lote.
4. **Burst** (ir direto à coleta sem node 2) só quando **as quatro** condições abaixo são verdadeiras — ver `pode_burst_coleta_sem_node2()`.

## Tabela de predicados (fonte de verdade: `funnel_gates`)

| Predicado | Chave(s) em `metadata` / texto | Função |
|-----------|--------------------------------|--------|
| Nome útil | `nome_lead` / `ctx.nome_lead` fora de placeholders e ruído (`sim`, `ok`, …) | `nome_util_para_checklist_fase1()` (pré-flight + anti-redundância); burst node 1 continua com `nome_eh_placeholder()` |
| Contato | `lead_contato_salvo_declarado` **ou** `node2_vcard_despachado` **ou** texto com padrão node 2 | `contato_salvo_ou_declarado()` (alinhado ao burst em `fase_1_preflight`) |
| Foto | `foto_recebida` | `meta_tem_foto()` |
| Desabafo | `desabafo_recebido` | `meta_tem_desabafo()` |

## Vocativo quando ainda não há nome

- **`VOCATIVO_SEM_NOME`** em `flows/funnel_gates.py` (hoje `"meu bem"`) é o default único quando o campo nome está vazio ou é placeholder.
- **`nome_lead_para_exibicao`** e **`primeiro_nome_exibicao`** em `copy_sanitizer` usam esse contrato; nodes e recovery não devem hardcodar `"meu anjo"` / `"minha estrela"` como fallback de nome.

## Onde isto entra no código hoje

- **Engine (sniffer):** chama `sniffer_aplicar_fase1_flags()` em `flows/funnel_gates.py`, que preenche `foto_recebida`, `desabafo_recebido`, `lead_contato_salvo_declarado`, etc., antes do node (logs continuam no `engine`).
- **Guardrail pós-sniffer:** `sanear_lead_contato_sem_evento_sniffer()` — se `lead_contato_salvo_declarado` passar a `True` **sem** evento `contato_atual` / `contato_historico` do sniffer neste turno, reverte (defesa contra metadata “mágica” antes de evidência).
- **Pré-flight fase 1 (`flows/fase_1_preflight.py`):** após o sniffer, o `engine` junta texto (`concat_texto_usuario`), marca Instagram (`sniffer_instagram_meta`), burst longo (`promover_burst_fase1_meta`) e avanço só para frente (`resolver_avanco_node_fase1`). `flows/fase_1_saudacao/sniffer_fase1.py` só reexporta símbolos para compatibilidade.
- **Node 1:** burst para `3_coleta_profunda` chama `pode_burst_coleta_sem_node2()` (mesma lógica que antes, centralizada).
- **Node 2:** confirmação + vcard quando o funil exige o passo explícito.
- **Node 3:** bypass por tentativas na camada 1 usa `meta_node3_forcar_camada1_completa()` em `funnel_gates` (escrita única).

## API (suporte / dashboard)

- **`GET /api/leads/<lead_id>/funnel-snapshot`** — devolve `snapshot` (`snapshot_fase1_coleta`) e `pendencias` (`pendencias_fase1`). Query opcional: **`texto_turno`** (texto da última mensagem do user para o mesmo critério de contato no texto que o motor usa no turno).

## CI local / GitHub Actions

- **`python scripts/verificar_funil_ci.py`** — unittest + guardrails + `teste_funnel_sequencias` + `simular_funil_e2e`.
- Workflow **`.github/workflows/funil-ci.yml`** (push/PR em `main`/`master`).

## Camadas que ainda podem “lutar” com isto

- **`copy_sanitizer.motivo_redundancia_texto` + engine:** `extrair_evidencias_conversa` inclui **`contato_ritual_ok`** (`contato_salvo_ou_declarado`, alinhado ao funil, com vCard). Regex de supressão deve ser **estreita** para não cortar perguntas legítimas (ex.: “Conseguiu salvar, meu bem?”).
- **NLU / outros escritores de metadata:** “sim” sozinho **não** liga `lead_contato_salvo_declarado` via sniffer; o guardrail acima impede que essa flag apareça “do nada” sem evento de contato do sniffer no turno.

## Testes

- `tests/test_funnel_gates.py` — predicados e burst.
- `tests/test_funnel_sniffer_writes.py` — sniffer, guardrail de contato, `meta_node3_forcar_camada1_completa`.
- `tests/test_sqlite_lead_metadata_e2e.py` — SQLite em memória + `Lead.metadata_json` após sniffer.
- `tests/test_fase_1_preflight.py` — checklist, avanço de nó, burst longo.
- `tests/test_engine_processar_sniffer_e2e.py` — `Engine.processar_mensagem` com DB em memória e dependências mockadas.
- `scripts/teste_funnel_sequencias.py` — corre a suíte agregada dos módulos acima.
- `scripts/teste_node1_guardrails.py` — limites de balões no node 1 (fallback).
- `scripts/verificar_funil_ci.py` — agregado para CI (local ou GitHub Actions).
