# Checklist — validação em staging (Flow Builder + Executar lead)

Objetivo: testar **num número real** um fluxo que use **condição**, **divisão A/B**, **API HTTP**, **GPT/Agente IA**, **`motor_ref`** e o botão **Executar lead**, com as **flags de ambiente** corretas. Serve para apanhar lacunas de copy, timing, erros e custo de API **antes** de investir na fase D (inbound no grafo).

Complementa `docs/checklist-publicacao-fluxo.md` (publicar versão); aqui o foco é **execute** + motor de fila.

---

## 1. Ambiente (staging)

- [ ] Processo do servidor com o **mesmo tenant** que o dashboard (`X-Acassia-Tenant` / `ACASSIA_TENANT_ID` alinhados).
- [ ] **`GEMINI_API_KEY`** definida no processo (C2).
- [ ] Flags do Flow Builder no `.env` do processo (reiniciar após alterar):

```env
FLOW_BLUEPRINT_ALLOW_HTTP=1
FLOW_BLUEPRINT_ALLOW_LLM=1
FLOW_BLUEPRINT_ALLOW_MOTOR_REF=1
FLOW_BLUEPRINT_MOTOR_REF_ALLOWLIST=flows.flow_blueprint_motor
```

Opcional: `FLOW_BLUEPRINT_LLM_TIMEOUT_S`, `FLOW_BLUEPRINT_LLM_MAX_OUTPUT_TOKENS` (ver `env.example`).

- [ ] Para o nó **API**: URL **HTTPS** pública (ex. `https://httpbin.org/get` ou o vosso endpoint de teste). Pedidos locais `http://127.0.0.1` só funcionam se o servidor conseguir alcançar esse host.

---

## 2. Lead de teste

- [ ] Lead com **telefone** associado ao número de teste (WhatsApp Cloud API já configurado).
- [ ] **Metadata** com campos que as regras do bloco **Condição** esperam (ex.: se a regra for `nome` = `Maria`, o lead deve ter `nome` / metadata coerente — ver `flow_context_from_lead`).
- [ ] Anotar o **`lead_id`** para usar em **Executar lead**.

---

## 3. Grafo sugerido (um ramo único após ramificações)

Monte no canvas uma cadeia **num único caminho “feliz”** (o execute percorre um ramo de cada vez):

1. **Gatilho** → **Condição** (regra alinhada ao metadata do lead acima).
2. Saída **sim** → **Divisão A/B** (`A:50,B:50` ou equivalente).
3. **Uma** das saídas da divisão → **API HTTP** (GET simples).
4. → **GPT** (prompt curto, modelo Flash).
5. → **Referência motor Python** (`module_hint`: `flows.flow_blueprint_motor.demo:demo_greeting`).
6. → **Conteúdo** com texto final (e opcionalmente `{{variável}}` para B3).

Ordem lógica: primeiro ramos (**condição** / **divisão**), depois integrações (**API**, **GPT**, **motor**), depois copy ao lead (**Conteúdo**).

- [ ] **Validar** e **Servidor** (guardar blueprint).
- [ ] **Simular** no canvas (dry-run) — não substitui o teste real na fila.

---

## 4. Executar lead (API ou dashboard)

- [ ] No dashboard: Fluxos → abrir o blueprint → **Executar lead** → introduzir o `lead_id`.
- [ ] Ou `POST /api/flows/blueprints/<id>/execute` com `{ "lead_id": <int> }` e cabeçalho de tenant correto.

---

## 5. O que observar no telefone e nos logs

| Área | O que verificar |
|------|------------------|
| **Condição / Divisão** | Só uma linha de mensagens coerente com o ramo esperado (B1/B2 + metadata). |
| **API** | Mensagem de debug `🔧 API …` com preview (C1); variáveis `flow_http__*` / `save_as` no passo seguinte se configurado (B3). |
| **GPT** | Texto **gerado** pelo modelo, **não** o prompt bruto (C2 + skip A1 no engine). |
| **`motor_ref`** | Texto do demo `[motor_ref demo] Olá, …` ou erro controlado (C3). |
| **Anotação** | Não deve aparecer como chat ao lead (B4). |
| **Logs** | `event=flow_http_disabled`, `flow_builder_llm_skip`, `flow_builder_motor_ref_skip` **não** devem aparecer quando as flags e chaves estão corretas. |

---

## 6. Go / no-go para “subir” investimento em D

- [ ] **Go** — uma execução completa sem surpresas; limites de custo/latência Gemini aceitáveis; copy aprovada.
- [ ] **No-go** — falha intermitente, prompt a vazar, ou HTTP bloqueado: corrigir `.env`, URLs, tenant ou blueprint antes de desenhar D1.

---

## Ver também

- `docs/roadmap-canvas-orbita.md` — fases B–D.
- `env.example` — variáveis `FLOW_BLUEPRINT_*`.
