# Roadmap — Canvas / Flow Builder (órbita e ordem)

Documento vivo: cada passo depende dos anteriores. Não avançar sem fechar o anterior em **produção** ou **staging** conforme o caso.

---

## Mapa de sistemas (órbita global)

```
dashboard.html  →  serialize JSON (graph)
       ↓
POST /api/flows/validate|compile|simulate  →  flow_builder_runtime.py
       ↓
POST /api/flows/blueprints (body_json)  →  DB FlowBlueprint
       ↓
POST /api/flows/publish  →  FlowPublish (tenant)
       ↓
POST /api/flows/blueprints/<id>/execute  →  flow_executor.document_to_acoes
       ↓
motor._processar_fila  →  engine.py  →  Meta WhatsApp API
```

**Órbita paralela (inbound):** cada mensagem do utilizador entra por `app.py` → triagem → `engine` → `_executar_node` / funil Python em `flows/fase_*`. **O grafo do canvas não governa este caminho** até existir integração explícita (item 8+ abaixo).

---

## Lista mestra (ordem sugerida)

### Fase A — Segurança e verdade do produto

| # | Entrega | Órbita (ligações) |
|---|---------|-------------------|
| **A1** | **Não enviar prompt LLM do canvas como mensagem ao lead** | `flow_executor` gera `Acao(tipo=text, metadata.runtime=llm)` → `engine._processar_fila_corpo` enviava o texto como chat. Corrigir em **engine** (e documentar). |
| **A2** | Documento único “O que o canvas faz hoje vs motor Python” | **`docs/canvas-vs-motor-python.md`** — copy e stakeholders. |
| **A3** | Aviso na UI do bloco GPT/Agente: “inferência ainda não ligada ao Gemini” (ou equivalente) | **`dashboard.html`** — `flowInspectorLlamaPlaceholderNoticeHtml()` + ramo `agente_ia`; subtítulo GPT ajustado. |

### Fase B — Execução fiel ao desenho

| # | Entrega | Órbita |
|---|---------|--------|
| **B1** | **Ramos reais:** `condicao` avalia regras + escolhe aresta `true`/`false` | **`flow_graph_walk.py`** + `document_to_acoes(..., context=...)` em **`POST .../execute`** via `flow_context_from_lead`. Compilação/validate linear mantida; **sem** contexto + fluxo com condição → aviso + plano linear. |
| **B2** | **Divisão A/B** com persistência de braço | **`flow_graph_walk`**: pesos `A:50,B:50` (paridade com simulador), escolha determinística por `(tenant_id, lead_id, node_id, blueprint_id)`; chave `flow_divisao__<node_id>` no contexto/metadata; `execute` grava em `lead.metadata_json`. |
| **B3** | **Variáveis de fluxo** (resultado HTTP → usar no próximo nó) | **`flow_executor`**: nó `api` grava `flow_http__<node_id>` e opcional `save_as`; textos resolvem `{{chave}}`; `execute` persiste em `lead.metadata_json` (`flow_vars_metadata_out`). |
| **B4** | **Anotações internas** (nota no canvas ≠ mensagem ao lead) | **`flow_executor`** marca `Acao` do bloco `anotacao`; **`engine`** ignora envio WhatsApp (`kind: note`), com log. |

### Fase C — Integrações e blocos avançados

| # | Entrega | Órbita |
|---|---------|--------|
| **C1** | HTTP: `FLOW_BLUEPRINT_ALLOW_HTTP` documentado + UI aviso se desligado | **`env.example`**, **`flow_executor`** (`flow_blueprint_allow_http`, log se desligado), **`GET /api/flows/schema`** (`runtime.allow_http`), **`dashboard.html`** (faixa no inspetor API). |
| **C2** | **LLM real** no execute: prompt → chamada Gemini (ou configurável) → texto enviado | **`flow_executor`**: `FLOW_BLUEPRINT_ALLOW_LLM` + `GEMINI_API_KEY` → `generateContent`; `metadata.runtime=llm_gemini`; **`GET /api/flows/schema`** (`allow_llm`, `gemini_configured`); **`dashboard.html`** aviso conforme estado; limites via env. |
| **C3** | **motor_ref** → importar / chamar nó Python real | **`flow_motor_ref`**: `FLOW_BLUEPRINT_ALLOW_MOTOR_REF` + allowlist de prefixos; `module_hint` = `módulo:função` → `list[Acao]`; **`engine`** ignora `motor_ref_pending` / `motor_ref_error`; **`schema`** (`allow_motor_ref`); **`dashboard`** aviso; demo em **`flows.flow_blueprint_motor.demo`**. |

### Fase D — Paridade “plataforma”

| # | Entrega | Órbita |
|---|---------|--------|
| **D1** | Inbound segue **blueprint publicado** (modo opcional por tenant) | `engine._rotear_state_machine` ou gate no início; conflito com nós `node_atual` atuais. |
| **D2** | Tags, audiências, broadcast (nível Manychat) | Modelos DB + UI + filas. |

---

## Passo em detalhe — **A1** (primeiro)

### Problema

- `flow_executor.steps_to_acoes` para `runtime == "llm"` cria mensagem de texto cujo `conteudo` é o **prompt**.
- `engine._processar_fila_corpo` trata `tipo == "text"` **sem** verificar `metadata.runtime`.
- **Efeito:** “Executar lead” ou fila pode **enviar o prompt ao cliente** como se fosse copy.

### Ligações tocadas

1. `flow_executor.py` — origem das `Acao`.
2. `engine.py` — `_processar_fila_corpo` — ramo `text`.
3. Opcional: `tests/` — um teste que garante que LLM placeholder não passa para envio (mock ou flag).

### Critério de feito

- Com blueprint só com nó GPT, **nenhum** texto do prompt sai pelo WhatsApp neste modo placeholder.
- Log claro no `logger` para debugging.
- Comentário no código apontando para C2 (LLM real).

---

## Passo em detalhe — **A2**

### Entrega

- **`docs/canvas-vs-motor-python.md`** — linguagem não técnica: duas faixas (canvas vs motor), o que já faz, o que não substitui, como conectam, frase para copy (“não é Manychat ainda”).
- Ligações: este roadmap, `checklist-publicacao-fluxo.md`.

### Critério de feito

- Stakeholder consegue ler em **minutos** e alinhar expectativa sem abrir código.

---

## Passo em detalhe — **A3**

### Entrega

- Faixa âmbar no inspetor (**GPT** e **Agente IA**): motor não gera/envia Gemini no WhatsApp; prompt não vai ao lead; simulação no canvas; ponteiro para roadmap C2.
- **GPT:** aviso acima do cartão “Cérebro de IA”; subtítulo do cartão menciona “quando inferência estiver ligada”.
- **Agente IA:** ramo dedicado em `openFlowInspector` com `flowInspectorRenderGeneric(..., { llmPlaceholderNotice: true })` para não depender só do inspetor genérico sem aviso.

### Critério de feito

- Abrir qualquer um dos dois blocos mostra o aviso **antes** dos campos de configuração.

---

## Passo em detalhe — **B1**

### Entrega

- **`flow_graph_walk.py`**: `evaluate_condicao_rules`, `pick_condicao_next_node`, `graph_walk_steps` (DFS a partir de trigger/webhook; nó `condicao` só roteia, não gera placeholder).
- **`flow_executor.py`**: `flow_context_from_lead`, `document_to_acoes(doc, context=None)` — com contexto e grafo contendo `condicao`, usa percurso com ramos.
- **`app.py`**: `execute` blueprint passa `context=flow_context_from_lead(lead)` (metadata + nome, telefone, node_atual, lead_id).
- **`tests/test_flow_graph_walk.py`**: regras `eq`, etiquetas sim/não, `document_to_acoes` ramificado.

### Limites (v1)

- Operadores de regra alinhados ao simulador; `var`/`val` sem `{{}}`: chave em contexto ou literal.
- Vários ramos não-condição: segue **primeira** aresta (igual nota anterior).
- Inbound automático ainda **não** usa o grafo (fase D).

### Critério de feito

- “Executar lead” com blueprint em árvore `trigger → condição → dois conteúdos` envia **só** o ramo coerente com o metadata/nome do lead.

---

## Passo em detalhe — **B2**

### Entrega

- **`flow_graph_walk.py`**: `parse_divisao_weights` (mesma gramática que `flowSimParseDivisaoWeights`), `pick_divisao_next_node`, ramo `divisao` em `graph_walk_steps`; reutiliza `flow_divisao__*` do contexto quando compatível com arestas.
- **`flow_executor.py`**: `document_to_acoes(..., blueprint_id=..., tenant_id=..., divisao_metadata_out=...)`; `flow_context_from_lead(..., tenant_id=...)`.
- **`app.py`**: `execute` funde `divisao_metadata_out` em `lead.metadata_json` com `flag_modified`.

### Critério de feito

- Duas execuções com o mesmo lead/tenant/blueprint escolhem o **mesmo** ramo; metadata passa a conter a escolha para reexecuções coerentes.

---

## Passo em detalhe — **B3**

### Entrega

- **`flow_executor.py`**: contexto mutável `flow_vars` (base = metadata do lead + campos comuns) durante `steps_to_acoes`; após nó `api` (runtime `http`), grava `flow_http__<node_id>` (`status`, `body`) e, se configurado, `save_as` / `output_var` com o corpo da resposta; `apply_flow_template` em textos (`conteudo`, itens, delay, etc.); `flow_vars_metadata_out` para persistência.
- **`app.py`**: `execute` funde `flow_vars_metadata_out` no `metadata_json` do lead (com `flag_modified`), em conjunto com divisão A/B.

### Critério de feito

- Fluxo `trigger → API HTTP → mensagem` com `{{save_as}}` ou `{{flow_http__…}}` substituído na mesma execução; metadata atualizado para a próxima execução ler variáveis do lead.

---

## Passo em detalhe — **B4**

### Entrega

- **`flow_executor.py`**: `Acao` de `anotacao` com `metadata.kind = "note"` e `runtime = "note_internal"`.
- **`engine.py`**: ramo `text` — se `source=flow_builder` e `kind=note`, não chama API WhatsApp; `logger.info` com `event=flow_builder_note_skip`.

### Critério de feito

- “Executar lead” com bloco **Anotação** no fluxo: a nota **não** aparece como chat enviado ao número (comportamento distinto de **Conteúdo**).

---

## Passo em detalhe — **C1**

### Entrega

- **`env.example`**: comentário e exemplo `FLOW_BLUEPRINT_ALLOW_HTTP=1`.
- **`flow_executor.py`**: `flow_blueprint_allow_http()`; log `event=flow_http_disabled` quando um nó `api` é ignorado por flag desligada.
- **`app.py`**: resposta de `/api/flows/schema` inclui `runtime: { "allow_http": bool }`.
- **`dashboard.html`**: ao abrir o inspetor do bloco **API Request**, se `allow_http` for falso, mostra faixa âmbar com instruções (`env` + reinício).

### Critério de feito

- Operador vê no canvas que **Executar lead** não fará HTTP enquanto o servidor não tiver a variável ativa; documentação de ambiente alinhada.

---

## Passo em detalhe — **C2**

### Entrega

- **`flow_executor.py`**: `FLOW_BLUEPRINT_ALLOW_LLM` + `GEMINI_API_KEY` → `flow_gemini_generate_text` (REST v1beta); nós `gpt` / `agente_ia` (`runtime` llm) passam a produzir texto com `runtime=llm_gemini`; falha da API → mensagem curta de fallback (nunca o prompt bruto).
- **`engine.py`**: continua a suprimir apenas `runtime=llm` (placeholder); `llm_gemini` segue o envio normal.
- **`app.py`**: `runtime` em `/api/flows/schema` inclui `allow_llm` e `gemini_configured`.
- **`env.example`**: `FLOW_BLUEPRINT_ALLOW_LLM`, modelo/tokens/timeout opcionais.
- **`dashboard.html`**: faixa no inspetor GPT/Agente conforme `allow_llm` + `gemini_configured`.

### Critério de feito

- Com flag e chave ativas, **Executar lead** envia ao WhatsApp o **texto gerado**, não o prompt; sem flag ou sem chave, comportamento A1 (placeholder).

---

## Passo em detalhe — **C3**

### Entrega

- **`flow_motor_ref.py`**: `invoke_flow_motor_ref`, allowlist por prefixo (`FLOW_BLUEPRINT_MOTOR_REF_ALLOWLIST`), importlib + chamada à função; retorno validado como `list[Acao]`.
- **`flow_executor.py`**: ramo `motor_ref` antes de `system`; `FLOW_BLUEPRINT_ALLOW_MOTOR_REF`; passa `blueprint_id` / `tenant_id` a `steps_to_acoes`.
- **`flows/flow_blueprint_motor/demo.py`**: função de exemplo `demo_greeting`.
- **`engine.py`**: não envia `runtime` `motor_ref_pending` nem `motor_ref_error`.
- **`app.py`**: `runtime.allow_motor_ref` no schema; **`env.example`**; **`dashboard.html`** inspetor dedicado com aviso.

### Critério de feito

- Com flag e `module_hint` válido sob a allowlist, **Executar lead** produz as mesmas `Acao` do hook; sem flag, nada de código arbitrário e sem mensagem técnica ao lead.

---

## Histórico

- *2026-04-10:* Criado roadmap + implementação A1 (engine).
- *2026-04-10:* **A2** — `docs/canvas-vs-motor-python.md`.
- *2026-04-10:* **A3** — `dashboard.html` (aviso LLM + ramo `agente_ia`).
- *2026-04-10:* **B1** — `flow_graph_walk.py`, `flow_executor`, `app.py`, testes.
- *2026-04-10:* **B2** — divisão A/B determinística + persistência `flow_divisao__*` em `execute` e testes.
- *2026-04-10:* **B3** — variáveis de fluxo (HTTP + `{{chave}}` + metadata).
- *2026-04-10:* **B4** — anotações do Flow Builder não enviadas ao WhatsApp (`engine`).
- *2026-04-10:* **C1** — `FLOW_BLUEPRINT_ALLOW_HTTP` documentado, `schema` + aviso UI no bloco API.
- *2026-04-10:* **C2** — Gemini no execute (`FLOW_BLUEPRINT_ALLOW_LLM` + `GEMINI_API_KEY`), `llm_gemini`, schema + dashboard.
- *2026-04-10:* **C3** — `motor_ref` com whitelist (`flow_motor_ref`), demo, engine + dashboard.
