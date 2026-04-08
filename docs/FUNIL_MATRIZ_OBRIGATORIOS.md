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
| Nome útil | `nome_lead` / `ctx.nome_lead` fora de `PLACEHOLDER_NOMES` | `nome_eh_placeholder()` → False |
| Contato | `lead_contato_salvo_declarado` OU texto com padrão node 2 | `contato_salvo_ou_declarado()` |
| Foto | `foto_recebida` | `meta_tem_foto()` |
| Desabafo | `desabafo_recebido` | `meta_tem_desabafo()` |

## Vocativo quando ainda não há nome

- **`VOCATIVO_SEM_NOME`** em `flows/funnel_gates.py` (hoje `"meu bem"`) é o default único quando o campo nome está vazio ou é placeholder.
- **`nome_lead_para_exibicao`** e **`primeiro_nome_exibicao`** em `copy_sanitizer` usam esse contrato; nodes e recovery não devem hardcodar `"meu anjo"` / `"minha estrela"` como fallback de nome.

## Onde isto entra no código hoje

- **Engine (sniffer):** chama `sniffer_aplicar_fase1_flags()` em `flows/funnel_gates.py`, que preenche `foto_recebida`, `desabafo_recebido`, `lead_contato_salvo_declarado`, etc., antes do node (logs continuam no `engine`).
- **Node 1:** burst para `3_coleta_profunda` chama `pode_burst_coleta_sem_node2()` (mesma lógica que antes, centralizada).
- **Node 2:** confirmação + vcard quando o funil exige o passo explícito.
- **Node 3:** camadas de coleta assumem as flags acima; visão Gemini valida mão quando chega imagem no turno.

## Camadas que ainda podem “lutar” com isto

- **`copy_sanitizer.motivo_redundancia_texto` + engine:** podem remover balões; regex deve ser **estreita** para não cortar perguntas legítimas (ex.: “Conseguiu salvar, meu bem?”).
- **NLU:** “sim” genérico não deve substituir `lead_contato_salvo_declarado` sem evidência.

## Testes

- `tests/test_funnel_gates.py` — predicados e burst.
- `tests/test_funnel_sniffer_writes.py` — escritas do sniffer (`sniffer_aplicar_*`).
- `tests/test_sqlite_lead_metadata_e2e.py` — SQLite em memória + `Lead.metadata_json` após sniffer.
- `scripts/teste_funnel_sequencias.py` — corre a suíte `test_funnel_gates` (e pode crescer com cenários integrados).
- `scripts/teste_node1_guardrails.py` — limites de balões no node 1 (fallback).
