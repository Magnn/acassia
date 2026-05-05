"""
Executor ponta-a-ponta: plano compilado do Flow Builder → lista de Acao (schema.py).

- Tipos seguros: message (texto), delay, entry/terminal/note (no-op).
- HTTP opcional: só se a variável de ambiente **FLOW_BLUEPRINT_ALLOW_HTTP** estiver ativa
  (`1`, `true`, `yes`, `on`). Caso contrário, nós `api` são ignorados na execução (sem pedido HTTP).
  Ver `env.example` e `flow_blueprint_allow_http()`.
- B3: nó `api` grava resultado em variáveis (`save_as` / `flow_http__<node_id>`); textos seguintes
  resolvem `{{chave}}` com o contexto acumulado (metadata do lead + variáveis do run).
- B4: nó `anotacao` gera `Acao` marcada como nota interna; o **engine** não envia ao WhatsApp.
- C2: com **FLOW_BLUEPRINT_ALLOW_LLM** e **GEMINI_API_KEY**, nós GPT/Agente chamam a API Gemini em
  `steps_to_acoes`; o texto devolvido vai em `conteudo` com `metadata.runtime=llm_gemini` (o **engine** envia).
  Sem flag ou sem chave, mantém-se o placeholder `runtime=llm` (não enviado — A1).
- C3: nó **motor_ref** com **FLOW_BLUEPRINT_ALLOW_MOTOR_REF** chama `flow_motor_ref.invoke_flow_motor_ref`
  (`module_hint` = `módulo:função`, allowlist por prefixo). Sem flag, `runtime=motor_ref_pending` (engine não envia).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Tuple

import requests

from schema import Acao
from flow_builder_runtime import NODE_SPECS, compile_flow_plan, validate_flow_document

logger = logging.getLogger(__name__)


def flow_context_from_lead(lead: Any, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Contexto plano para regras do canvas: metadata do lead + campos comuns."""
    meta = getattr(lead, "metadata_json", None) or {}
    if not isinstance(meta, dict):
        meta = {}
    ctx: Dict[str, Any] = {str(k): v for k, v in meta.items()}
    if getattr(lead, "nome", None) is not None:
        ctx["nome"] = lead.nome
    if getattr(lead, "telefone", None) is not None:
        ctx["telefone"] = lead.telefone
    if getattr(lead, "node_atual", None) is not None:
        ctx["node_atual"] = lead.node_atual
    ctx["lead_id"] = str(getattr(lead, "id", "") or "")
    if tenant_id is not None:
        ctx["tenant_id"] = str(tenant_id).strip() or "default"
    return ctx

_MAX_DELAY_S = min(120.0, float(os.getenv("FLOW_BLUEPRINT_MAX_DELAY_S", "120") or 120))
_ALLOW_HTTP = str(os.getenv("FLOW_BLUEPRINT_ALLOW_HTTP", "") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def flow_blueprint_allow_http() -> bool:
    """Indica se nós `api` executam pedidos HTTP reais em `steps_to_acoes` (C1)."""
    return _ALLOW_HTTP


_ALLOW_LLM = str(os.getenv("FLOW_BLUEPRINT_ALLOW_LLM", "") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)
_DEFAULT_FLOW_LLM_MODEL = (os.getenv("FLOW_BLUEPRINT_LLM_DEFAULT_MODEL") or "gemini-2.5-flash").strip()


def flow_blueprint_allow_llm() -> bool:
    """Indica se blocos GPT/Agente IA resolvem texto via Gemini em `steps_to_acoes` (C2)."""
    return _ALLOW_LLM


def flow_blueprint_gemini_configured() -> bool:
    """True se `GEMINI_API_KEY` está definida (sem expor o segredo)."""
    return bool((os.getenv("GEMINI_API_KEY") or "").strip())


def _llm_max_output_tokens() -> int:
    try:
        n = int(os.getenv("FLOW_BLUEPRINT_LLM_MAX_OUTPUT_TOKENS", "1024") or 1024)
    except ValueError:
        n = 1024
    return max(64, min(n, 8192))


def _sanitize_gemini_model(raw: Optional[str]) -> str:
    s = re.sub(r"[^\w.\-]", "", str(raw or "").strip())[:80]
    return s or _DEFAULT_FLOW_LLM_MODEL


def _parse_llm_temperature(cfg: Mapping[str, Any]) -> float:
    for k in ("ai_temperature", "temperature"):
        v = cfg.get(k)
        if v is not None and str(v).strip() != "":
            try:
                return max(0.0, min(2.0, float(str(v).replace(",", "."))))
            except ValueError:
                pass
    return 0.7


def _gemini_response_text(res_json: Mapping[str, Any]) -> str:
    cands = res_json.get("candidates")
    if not isinstance(cands, list) or not cands:
        return ""
    parts = (cands[0].get("content") or {}).get("parts")
    if not isinstance(parts, list):
        return ""
    chunks: List[str] = []
    for p in parts:
        if isinstance(p, dict) and p.get("text"):
            chunks.append(str(p["text"]))
    return "".join(chunks).strip()


def flow_gemini_generate_text(
    prompt: str,
    *,
    model: str,
    temperature: float,
    api_key: Optional[str],
    system_instruction: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Uma chamada `generateContent` ao Gemini (REST v1beta).
    Devolve (texto, erro). Erro None em sucesso.

    ``system_instruction`` (opcional): conteúdo injetado como
    ``systemInstruction`` no payload — usado para passar a personalidade /
    instruções do agente Studio publicado pra moldar o output sem poluir o
    prompt de turno.
    """
    if not (api_key or "").strip():
        return "", "GEMINI_API_KEY ausente"
    m = _sanitize_gemini_model(model)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key.strip()}"
    payload: Dict[str, Any] = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": float(temperature),
            "maxOutputTokens": _llm_max_output_tokens(),
        },
    }
    if system_instruction and system_instruction.strip():
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction.strip()[:8000]}]
        }
    try:
        to = min(90, max(8, int(os.getenv("FLOW_BLUEPRINT_LLM_TIMEOUT_S", "45") or 45)))
    except ValueError:
        to = 45
    try:
        r = requests.post(url, json=payload, timeout=to)
    except requests.RequestException as e:
        return "", str(e)[:500]
    if r.status_code != 200:
        return "", f"HTTP {r.status_code}: {(r.text or '')[:280]}"
    try:
        data = r.json()
    except json.JSONDecodeError:
        return "", "resposta JSON inválida"
    text = _gemini_response_text(data)
    if not text:
        return "", "resposta vazia ou bloqueada pelo modelo"
    return text[:4000], None


def _coerce_section(value: Any, *, nested_keys: Tuple[str, ...] = ()) -> str:
    """
    Aceita string OU dict aninhado e devolve texto unificado.

    Studio tem 2 shapes em circulação:
      - Plano (frontend AgentStudio.tsx novo): valor é string direta.
      - Aninhado (legacy `_studio_default_data` no app.py): valor é dict com
        sub-campos (ex.: ``{identidade, diretrizes}``).

    ``nested_keys`` define a ordem dos sub-campos a concatenar caso seja dict.
    Strings vazias / chaves ausentes são puladas silenciosamente.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        chunks: List[str] = []
        for k in nested_keys or list(value.keys()):
            v = value.get(k)
            if isinstance(v, str) and v.strip():
                chunks.append(v.strip())
        return "\n\n".join(chunks)
    return ""


def _build_system_instruction_from_studio(snap: Any) -> Optional[str]:
    """
    Constrói o ``systemInstruction`` para o Gemini a partir do snapshot do
    agente Studio publicado (injetado em ``ctx.metadata['__meumisterio_studio__']``
    pelo ``studio_runtime.inject_published_studio_into_metadata``).

    Tolera ambos os shapes do Studio (plano novo e aninhado legado), juntando
    personalidade + instruções + base + FAQ em seções markdown. Retorna None
    se o snapshot estiver vazio ou malformado.
    """
    if not isinstance(snap, dict):
        return None
    data = snap.get("data") if isinstance(snap.get("data"), dict) else snap
    if not isinstance(data, dict):
        return None
    parts: List[str] = []

    persona = _coerce_section(
        data.get("personalidade"),
        nested_keys=("identidade", "diretrizes"),
    )
    if persona:
        parts.append(f"## Personalidade\n{persona}")

    instrucoes = _coerce_section(
        data.get("instrucoes"),
        nested_keys=("gerais", "proibicoes", "formato_saida"),
    )
    if instrucoes:
        parts.append(f"## Instruções operacionais\n{instrucoes}")

    # Base aceita "base_conhecimento" (novo) OR "base" (legado) com sub-campos.
    base = _coerce_section(
        data.get("base_conhecimento"),
    ) or _coerce_section(
        data.get("base"),
        nested_keys=("contexto_empresa", "produtos", "politica_preco"),
    )
    if base:
        parts.append(f"## Base de conhecimento\n{base}")

    # FAQ: array de {q, a} (novo) OR objeto {perguntas: str} (legado)
    faq_lines: List[str] = []
    faqs_new = data.get("faqs")
    if isinstance(faqs_new, list):
        for f in faqs_new:
            if isinstance(f, dict):
                q = str(f.get("q") or "").strip()
                a = str(f.get("a") or "").strip()
                if q and a:
                    faq_lines.append(f"P: {q}\nR: {a}")
    if not faq_lines:
        legacy = data.get("faq")
        if isinstance(legacy, dict):
            perguntas = str(legacy.get("perguntas") or "").strip()
            if perguntas:
                faq_lines.append(perguntas)
    if faq_lines:
        parts.append("## FAQ\n" + "\n\n".join(faq_lines))

    return "\n\n".join(parts) if parts else None


def _flow_http_var_key(node_id: str) -> str:
    safe = re.sub(r"[^\w\-.]+", "_", str(node_id).strip() or "api")
    return f"flow_http__{safe}"


def _format_flow_var_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, dict):
        if "body" in v:
            return str(v.get("body") or "")
        try:
            return json.dumps(v, ensure_ascii=False)[:4000]
        except (TypeError, ValueError):
            return str(v)[:4000]
    return str(v)


def apply_flow_template(template: str, ctx: Mapping[str, Any]) -> str:
    """Substitui `{{chave}}` / `{{ chave }}` usando valores do contexto (B3)."""
    s = str(template or "")
    if "{{" not in s:
        return s
    out = s
    for k, v in ctx.items():
        key = str(k).strip()
        if not key:
            continue
        rep = _format_flow_var_value(v)
        out = out.replace("{{" + key + "}}", rep)
        out = out.replace("{{ " + key + " }}", rep)
    return out


def document_to_acoes(
    doc: Mapping[str, Any],
    context: Optional[Mapping[str, Any]] = None,
    *,
    blueprint_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
    divisao_metadata_out: Optional[Dict[str, Any]] = None,
    flow_vars_metadata_out: Optional[Dict[str, Any]] = None,
) -> List[Acao]:
    """
    Valida documento, compila e converte passos em ações do motor.

    Com `context` e nós `condicao` / `divisao`, usa percurso com ramificação (`flow_graph_walk`).
    Sem contexto ou sem esses nós, mantém plano linear (topológico).

    Com `flow_vars_metadata_out`, grava chaves de variáveis de fluxo (HTTP / `save_as`) para persistir
    no metadata do lead (ex.: `execute` no app).
    """
    from flow_graph_walk import graph_needs_context_walk, graph_walk_steps

    rep = validate_flow_document(doc)
    if not rep.get("ok"):
        raise ValueError("documento inválido: " + str(rep.get("errors") or []))
    norm = rep.get("normalized") or doc

    if context is None and graph_needs_context_walk(norm):
        logger.warning(
            "document_to_acoes: fluxo com condicao/divisao sem context — usando plano linear (ramos não aplicados)"
        )

    flow_vars: Dict[str, Any] = dict(context) if context else {}

    if context is not None and graph_needs_context_walk(norm):
        steps = graph_walk_steps(
            norm,
            context,
            blueprint_id=blueprint_id,
            tenant_id=tenant_id,
            divisao_metadata_out=divisao_metadata_out,
        )
        if not steps:
            logger.warning("graph_walk_steps vazio — fallback ao plano linear (revise o grafo)")
            plan = compile_flow_plan(norm)
            if not plan.get("ok"):
                raise ValueError("compilação falhou: " + str(plan.get("issues") or []))
            steps = plan.get("steps") or []
        if divisao_metadata_out:
            flow_vars.update(divisao_metadata_out)
        return steps_to_acoes(
            steps,
            flow_vars=flow_vars,
            flow_vars_metadata_out=flow_vars_metadata_out,
            blueprint_id=blueprint_id,
            tenant_id=tenant_id,
        )

    plan = compile_flow_plan(norm)
    if not plan.get("ok"):
        raise ValueError("compilação falhou: " + str(plan.get("issues") or []))
    steps = plan.get("steps") or []
    return steps_to_acoes(
        steps,
        flow_vars=flow_vars,
        flow_vars_metadata_out=flow_vars_metadata_out,
        blueprint_id=blueprint_id,
        tenant_id=tenant_id,
    )


_MAX_CONTEUDO_CARDS = 5  # alinhado ao Flow Builder (Meta / WhatsApp + métricas)


def _expand_conteudo_items(cfg: Mapping[str, Any], flow_vars: Mapping[str, Any]) -> List[Acao]:
    """Lista ordenada do bloco Conteúdo (texto, mídia, delay) → ações do motor.

    Cada item pode usar o formato novo do Flow Builder: ``{type, value}`` (texto/delay)
    ou ``{type, value: {url, caption}}`` (mídia). Mantém compat com ``body`` / ``seconds`` / chaves no topo.
    """
    out: List[Acao] = []
    items = cfg.get("contents")
    if not isinstance(items, list):
        return out
    for it in items[:_MAX_CONTEUDO_CARDS]:
        if not isinstance(it, dict):
            continue
        t = str(it.get("type") or "text").lower()
        if t == "text":
            body = apply_flow_template(str(it.get("body") or it.get("value") or "").strip(), flow_vars)
            if body:
                out.append(
                    Acao(
                        tipo="text",
                        conteudo=body[:4000],
                        metadata={"source": "flow_builder", "conteudo_item": "text"},
                    )
                )
        elif t == "delay":
            raw = it.get("seconds")
            if raw is None and it.get("value") is not None:
                raw = it.get("value")
            try:
                sec = float(raw or 0)
            except (TypeError, ValueError):
                sec = 0.0
            sec = max(0.0, min(sec, _MAX_DELAY_S))
            if sec > 0:
                out.append(Acao(tipo="delay", segundos=int(sec), metadata={"source": "flow_builder", "conteudo_item": "delay"}))
        elif t in ("image", "video", "audio", "document"):
            val = it.get("value")
            if isinstance(val, dict):
                url = apply_flow_template(str(val.get("url") or "").strip(), flow_vars)
                cap = apply_flow_template(str(val.get("caption") or "").strip(), flow_vars)
            else:
                url = apply_flow_template(str(it.get("url") or "").strip(), flow_vars)
                cap = apply_flow_template(str(it.get("caption") or "").strip(), flow_vars)
            if not url:
                continue
            meta: Dict[str, Any] = {"source": "flow_builder", "conteudo_item": t}
            if isinstance(val, dict) and t == "audio":
                meta["send_as_voice"] = bool(val.get("send_as_voice", True))
            elif t == "audio":
                meta["send_as_voice"] = True
            if t == "image":
                out.append(Acao(tipo="image", url=url, conteudo=cap[:900], metadata=meta))
            elif t == "video":
                out.append(Acao(tipo="video", url=url, conteudo=cap[:900], metadata=meta))
            elif t == "audio":
                out.append(Acao(tipo="audio", url=url, conteudo=url, metadata=meta))
            else:
                fn = apply_flow_template(str(it.get("filename") or "documento").strip(), flow_vars)[:200]
                out.append(Acao(tipo="document", url=url, conteudo=fn, metadata=meta))
    return out


def steps_to_acoes(
    steps: List[Dict[str, Any]],
    *,
    flow_vars: Optional[Dict[str, Any]] = None,
    flow_vars_metadata_out: Optional[Dict[str, Any]] = None,
    blueprint_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> List[Acao]:
    fv: Dict[str, Any] = flow_vars if flow_vars is not None else {}

    def _persist_flow_var(key: str, value: Any) -> None:
        if flow_vars_metadata_out is None or not key:
            return
        flow_vars_metadata_out[str(key)] = value

    # Guard: timeout global para evitar runaway execution (LLM + HTTP loops)
    _max_exec_s = min(300, max(30, int(os.getenv("FLOW_EXECUTOR_MAX_SECONDS", "120") or 120)))
    _started_at = time.time()

    acoes: List[Acao] = []
    for st in steps:
        # Timeout check a cada step
        if (time.time() - _started_at) > _max_exec_s:
            logger.warning(
                "[FLOW_EXEC] Timeout após %.1fs processando %d steps (max=%ds) — retornando %d ações parciais",
                time.time() - _started_at, len(steps), _max_exec_s, len(acoes),
            )
            break

        ntype = str(st.get("type") or "generic").lower()
        cfg = st.get("config") if isinstance(st.get("config"), dict) else {}
        spec = NODE_SPECS.get(ntype) or NODE_SPECS["generic"]
        rk = str(spec.get("runtime") or "passthrough")

        if rk == "entry":
            continue
        if rk == "terminal":
            continue

        if rk == "note" or ntype == "anotacao":
            note = apply_flow_template(str(cfg.get("note") or cfg.get("body") or "").strip(), fv)
            if note:
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=note[:4000],
                        metadata={
                            "source": "flow_builder",
                            "kind": "note",
                            "runtime": "note_internal",
                        },
                    )
                )
            continue

        if rk == "message" and ntype == "conteudo":
            expanded = _expand_conteudo_items(cfg, fv)
            if expanded:
                acoes.extend(expanded)
                continue
            body = apply_flow_template(
                (
                    str(cfg.get("body") or "").strip()
                    or str(cfg.get("step_name") or "").strip()
                ),
                fv,
            )
            if body:
                acoes.append(Acao(tipo="text", conteudo=body[:4000], metadata={"source": "flow_builder", "node_type": "conteudo"}))
            continue

        if rk == "message" or rk == "action":
            stack = cfg.get("acao_stack")
            if ntype == "acao" and isinstance(stack, list) and len(stack) > 0:
                for raw_step in stack:
                    if not isinstance(raw_step, dict):
                        continue
                    merged = dict(cfg)
                    merged.pop("acao_stack", None)
                    merged.pop("acao_etiqueta_catalog", None)
                    step_only = {
                        k: v
                        for k, v in raw_step.items()
                        if k not in ("acao_stack", "acao_etiqueta_catalog")
                    }
                    merged.update(step_only)
                    body = apply_flow_template(
                        (
                            str(merged.get("body") or merged.get("question") or merged.get("payload") or "").strip()
                            or str(merged.get("step_name") or "").strip()
                        ),
                        fv,
                    )
                    if body:
                        meta: Dict[str, Any] = {"source": "flow_builder", "node_type": ntype}
                        ak = str(merged.get("action_kind") or "").strip()
                        if ak:
                            meta["action_kind"] = ak
                        rm = str(merged.get("reply_mode") or "").strip()
                        if rm:
                            meta["reply_mode"] = rm
                        acoes.append(Acao(tipo="text", conteudo=body[:4000], metadata=meta))
                continue
            body = apply_flow_template(
                (
                    str(cfg.get("body") or cfg.get("question") or cfg.get("payload") or "").strip()
                    or str(cfg.get("step_name") or "").strip()
                ),
                fv,
            )
            if body:
                meta: Dict[str, Any] = {"source": "flow_builder", "node_type": ntype}
                ak = str(cfg.get("action_kind") or "").strip()
                if ak:
                    meta["action_kind"] = ak
                rm = str(cfg.get("reply_mode") or "").strip()
                if rm:
                    meta["reply_mode"] = rm
                acoes.append(Acao(tipo="text", conteudo=body[:4000], metadata=meta))
            continue

        if rk == "delay":
            try:
                sec = float(cfg.get("seconds") or 0)
            except (TypeError, ValueError):
                sec = 0.0
            sec = max(0.0, min(sec, _MAX_DELAY_S))
            if sec > 0:
                dmeta: Dict[str, Any] = {"source": "flow_builder"}
                note = apply_flow_template(str(cfg.get("body") or "").strip(), fv)
                if note:
                    dmeta["delay_note"] = note[:400]
                acoes.append(Acao(tipo="delay", segundos=int(sec), metadata=dmeta))
            continue

        if rk == "http" and _ALLOW_HTTP:
            node_id = str(st.get("node_id") or "api").strip()
            save_as = str(cfg.get("save_as") or cfg.get("output_var") or "").strip()
            url = apply_flow_template(str(cfg.get("url") or cfg.get("api_url") or "").strip(), fv)
            method = str(cfg.get("method") or cfg.get("api_method") or "GET").upper()
            qs = str(cfg.get("query_string") or "").strip().lstrip("?")
            if qs and url and ("https://" in url or "http://" in url):
                url = url + ("&" if "?" in url else "?") + qs
            hdrs: Dict[str, str] = {}
            raw_h = cfg.get("headers")
            if isinstance(raw_h, str) and raw_h.strip():
                try:
                    parsed = json.loads(raw_h.strip())
                    if isinstance(parsed, dict):
                        hdrs = {str(k): str(v) for k, v in parsed.items()}
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            body_raw = apply_flow_template(str(cfg.get("body") or cfg.get("api_body") or "").strip(), fv)
            if url.startswith("https://") or url.startswith("http://"):
                try:
                    req_kw: Dict[str, Any] = {"method": method, "url": url, "timeout": 8}
                    if hdrs:
                        req_kw["headers"] = hdrs
                    if body_raw and method in ("POST", "PUT", "PATCH", "DELETE"):
                        if body_raw.startswith("{"):
                            try:
                                req_kw["json"] = json.loads(body_raw)
                            except (json.JSONDecodeError, TypeError, ValueError):
                                req_kw["data"] = body_raw
                        else:
                            req_kw["data"] = body_raw
                    r = requests.request(**req_kw)
                    text_full = r.text or ""
                    preview = text_full[:280]
                    hmeta: Dict[str, Any] = {
                        "source": "flow_builder",
                        "http_status": r.status_code,
                    }
                    if hdrs:
                        hmeta["http_headers_sent"] = True
                    payload = {"status": r.status_code, "body": text_full[:8000]}
                    http_key = _flow_http_var_key(node_id)
                    fv[http_key] = payload
                    _persist_flow_var(http_key, payload)
                    if save_as:
                        fv[save_as] = text_full[:4000]
                        _persist_flow_var(save_as, fv[save_as])
                    acoes.append(
                        Acao(
                            tipo="text",
                            conteudo=f"🔧 API {method} {url[:96]}… → HTTP {r.status_code}\n{preview}",
                            metadata=hmeta,
                        )
                    )
                except Exception as e:
                    logger.warning("flow_executor http: %s", e)
                    acoes.append(
                        Acao(
                            tipo="text",
                            conteudo=f"🔧 API falhou: {url[:80]}… ({e})"[:900],
                            metadata={"source": "flow_builder", "error": str(e)},
                        )
                    )
            continue

        if rk == "http" and not _ALLOW_HTTP:
            logger.info(
                "event=flow_http_disabled node_id=%s — defina FLOW_BLUEPRINT_ALLOW_HTTP=1 no servidor para executar API HTTP",
                st.get("node_id"),
            )
            continue

        if rk == "notify":
            msg = apply_flow_template(str(cfg.get("message") or "Notificação (flow builder)").strip(), fv)
            ch = str(cfg.get("channel") or "log")
            acoes.append(
                Acao(
                    tipo="text",
                    conteudo=f"🔔 [{ch}] {msg}"[:900],
                    metadata={"source": "flow_builder", "notify": True},
                )
            )
            continue

        if rk == "tts":
            script = apply_flow_template(
                str(cfg.get("script") or cfg.get("body") or cfg.get("step_name") or "").strip(),
                fv,
            )
            if script:
                tmeta: Dict[str, Any] = {"source": "flow_builder", "node_type": ntype}
                vp = str(cfg.get("voice_profile") or "").strip()
                if vp:
                    tmeta["voice_profile"] = vp[:64]
                acoes.append(Acao(tipo="tts", tts_template=script[:2000], metadata=tmeta))
            continue

        if rk == "llm":
            prompt = apply_flow_template(
                str(
                    cfg.get("prompt")
                    or cfg.get("instructions")
                    or cfg.get("body")
                    or cfg.get("step_name")
                    or ""
                ).strip(),
                fv,
            )
            if not prompt:
                continue
            api_key = os.getenv("GEMINI_API_KEY") or ""
            model_raw = ""
            for k in ("ai_model", "model"):
                v = cfg.get(k)
                if v is not None and str(v).strip():
                    model_raw = str(v).strip()
                    break
            temp = _parse_llm_temperature(cfg)
            lmeta: Dict[str, Any] = {"source": "flow_builder", "node_type": ntype}
            for key in ("model", "temperature"):
                v = cfg.get(key)
                if v is not None and str(v).strip() != "":
                    lmeta[key] = str(v).strip()[:64]

            # Agente Studio publicado: vira systemInstruction (personalidade + base + FAQ).
            studio_snap = fv.get("__meumisterio_studio__")
            system_instruction = _build_system_instruction_from_studio(studio_snap)
            if system_instruction:
                lmeta["studio_agent"] = (
                    studio_snap.get("agent_name") if isinstance(studio_snap, dict) else None
                ) or "?"
                vn = studio_snap.get("version_number") if isinstance(studio_snap, dict) else None
                if vn is not None:
                    lmeta["studio_version"] = int(vn) if isinstance(vn, int) else 0

            if _ALLOW_LLM and api_key.strip():
                text, err = flow_gemini_generate_text(
                    prompt,
                    model=model_raw or _DEFAULT_FLOW_LLM_MODEL,
                    temperature=temp,
                    api_key=api_key,
                    system_instruction=system_instruction,
                )
                if err:
                    logger.warning("flow_executor llm: %s", err)
                    lmeta["runtime"] = "llm_gemini"
                    lmeta["llm_error"] = err[:300]
                    fb = "Desculpe, não consegui gerar a mensagem agora. Tente de novo em instantes."
                    acoes.append(Acao(tipo="text", conteudo=fb[:400], metadata=lmeta))
                else:
                    lmeta["runtime"] = "llm_gemini"
                    lmeta["llm_model"] = _sanitize_gemini_model(model_raw or _DEFAULT_FLOW_LLM_MODEL)
                    acoes.append(Acao(tipo="text", conteudo=text[:4000], metadata=lmeta))
            else:
                # Placeholder: engine não envia (runtime=llm) — ver A1 / C2.
                if _ALLOW_LLM and not api_key.strip():
                    logger.info("event=flow_llm_disabled_reason reason=missing_gemini_key")
                lmeta["runtime"] = "llm"
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=prompt[:4000],
                        metadata=lmeta,
                    )
                )
            continue

        if rk == "branch":
            expr = str(cfg.get("expression") or "").strip()
            if expr:
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=f"🔀 Condição: {expr}"[:900],
                        metadata={"source": "flow_builder", "runtime": "branch"},
                    )
                )
            continue

        if rk == "split":
            # ── A/B SPLIT RUNTIME: roleta + rastreamento de exposição ──
            import random
            node_id = str(st.get("node_id") or "").strip()
            wa = max(1, min(99, int(cfg.get("weight_a") or 50)))
            wb = 100 - wa
            roll = random.randint(1, 100)
            variant = "A" if roll <= wa else "B"
            # Salva variante como flow_var para downstream ({{ab_variant}})
            fv["ab_variant"] = variant
            fv[f"ab_{node_id}_variant"] = variant
            _persist_flow_var("ab_variant", variant)
            _persist_flow_var(f"ab_{node_id}_variant", variant)

            # Grava exposição no banco (rastreamento para analytics)
            try:
                _lead_id_val = fv.get("lead_id") or fv.get("_lead_id")
                if _lead_id_val and tenant_id and blueprint_id:
                    from db.database import SessionLocal as _AbSL
                    from db import models as _ab_m
                    _ab_db = _AbSL()
                    try:
                        # UPSERT: se lead já passou por este nó, atualiza variante
                        existing = _ab_db.query(_ab_m.ABTestExposure).filter_by(
                            tenant_id=tenant_id,
                            blueprint_id=blueprint_id,
                            node_id=node_id,
                            lead_id=int(_lead_id_val),
                        ).first()
                        if existing:
                            existing.variant = variant
                            existing.weight_a = wa
                            existing.weight_b = wb
                        else:
                            from datetime import datetime, timezone as _tz
                            _ab_db.add(_ab_m.ABTestExposure(
                                tenant_id=tenant_id,
                                blueprint_id=blueprint_id,
                                node_id=node_id,
                                lead_id=int(_lead_id_val),
                                variant=variant,
                                weight_a=wa,
                                weight_b=wb,
                            ))
                        _ab_db.commit()
                    except Exception as _ab_err:
                        logger.debug("[FLOW_EXEC] AB exposure save failed (non-fatal): %s", _ab_err)
                        _ab_db.rollback()
                    finally:
                        _ab_db.close()
            except Exception:
                pass

            logger.info(
                "event=ab_split node=%s variant=%s weights=%d/%d lead=%s",
                node_id, variant, wa, wb, fv.get("lead_id"),
            )
            continue


        if rk == "schedule":
            tz = str(cfg.get("timezone") or "").strip()
            if tz:
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=f"🕒 Expediente ({tz}) configurado."[:900],
                        metadata={"source": "flow_builder", "runtime": "schedule"},
                    )
                )
            continue

        if ntype == "motor_ref":
            from flow_motor_ref import flow_blueprint_allow_motor_ref, invoke_flow_motor_ref

            hint = apply_flow_template(
                str(cfg.get("module_hint") or cfg.get("body") or "").strip(),
                fv,
            )
            if not hint:
                continue
            nid = str(st.get("node_id") or "").strip()
            if flow_blueprint_allow_motor_ref():
                resolved, err = invoke_flow_motor_ref(
                    hint,
                    fv,
                    node_id=nid,
                    blueprint_id=blueprint_id,
                    tenant_id=tenant_id,
                )
                if err:
                    logger.warning("flow_executor motor_ref: %s", err)
                    acoes.append(
                        Acao(
                            tipo="text",
                            conteudo="Passo do motor indisponível.",
                            metadata={
                                "source": "flow_builder",
                                "runtime": "motor_ref_error",
                                "motor_ref": hint[:220],
                                "motor_error": err[:300],
                            },
                        )
                    )
                else:
                    acoes.extend(resolved)
            else:
                logger.info(
                    "event=flow_motor_ref_disabled node_id=%s — defina FLOW_BLUEPRINT_ALLOW_MOTOR_REF=1",
                    st.get("node_id"),
                )
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=hint[:900],
                        metadata={
                            "source": "flow_builder",
                            "runtime": "motor_ref_pending",
                            "motor_ref": hint[:220],
                        },
                    )
                )
            continue

        if rk == "system":
            hint = str(cfg.get("body") or cfg.get("module_hint") or cfg.get("step_name") or "").strip()
            if hint:
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=f"⚙️ Sistema: {hint}"[:900],
                        metadata={"source": "flow_builder", "runtime": "system"},
                    )
                )
            continue

        logger.info("flow_executor skip runtime=%s type=%s node_id=%s", rk, ntype, st.get("node_id"))

    return acoes


def tenant_has_published_content(tenant_id: Optional[str]) -> bool:
    """
    Retorna True se o tenant tem flow OU studio agent publicado.

    Usado pelo engine pra decidir se pode rodar funil estatico legado
    ou se deve mandar fallback "Ainda configurando" (multi-tenant safe).
    """
    if not tenant_id:
        return False
    try:
        from db.database import SessionLocal
        from db import models
        tid = (tenant_id or "default").strip() or "default"
        db = SessionLocal()
        try:
            flow_pub = db.query(models.FlowPublish).filter_by(tenant_id=tid).first()
            if flow_pub and flow_pub.published_blueprint_id:
                return True
            try:
                # StudioPublish é opcional — V1 pode não estar registrado
                studio_pub = db.query(models.StudioPublish).filter_by(tenant_id=tid).first()
                if studio_pub and getattr(studio_pub, "published_agent_id", None):
                    return True
            except Exception:
                pass
            return False
        finally:
            db.close()
    except Exception:
        return False


def inject_published_flow_metadata(metadata: Optional[dict], tenant_id: Optional[str]) -> None:
    """Anexa snapshot do blueprint publicado ao metadata do contexto (somente leitura)."""
    if not isinstance(metadata, dict):
        return
    try:
        from db.database import SessionLocal
        from db import models

        tid = (tenant_id or "default").strip() or "default"
        db = SessionLocal()
        try:
            pub = db.query(models.FlowPublish).filter_by(tenant_id=tid).first()
            if not pub or not pub.published_blueprint_id:
                metadata.pop("__meumisterio_flow_blueprint__", None)
                return
            bp = db.query(models.FlowBlueprint).filter_by(id=pub.published_blueprint_id, tenant_id=tid).first()
            if not bp:
                return
            body = bp.body_json if isinstance(bp.body_json, dict) else {}
            metadata["__meumisterio_flow_blueprint__"] = {
                "blueprint_id": bp.id,
                "slug": bp.slug,
                "title": bp.title,
                "summary": {
                    "nodes": len((body.get("graph") or {}).get("nodes") or []),
                    "edges": len((body.get("graph") or {}).get("edges") or []),
                },
            }
        finally:
            db.close()
    except Exception as e:
        logger.debug("inject_published_flow_metadata: %s", e)
