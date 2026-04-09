"""
Executor ponta-a-ponta: plano compilado do Flow Builder → lista de Acao (schema.py).

- Tipos seguros: message (texto), delay, entry/terminal/note (no-op).
- HTTP opcional: só se FLOW_BLUEPRINT_ALLOW_HTTP=1 (timeout curto).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Mapping, Optional

import requests

from schema import Acao
from flow_builder_runtime import NODE_SPECS, compile_flow_plan, validate_flow_document

logger = logging.getLogger(__name__)

# Delays longos (ex.: 4 min entre mensagens no funil estático) exigem FLOW_BLUEPRINT_MAX_DELAY_S alto o bastante.
_MAX_DELAY_S = min(900.0, float(os.getenv("FLOW_BLUEPRINT_MAX_DELAY_S", "900") or 900))
_ALLOW_HTTP = str(os.getenv("FLOW_BLUEPRINT_ALLOW_HTTP", "") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def document_to_acoes(doc: Mapping[str, Any]) -> List[Acao]:
    """Valida documento, compila e converte passos em ações do motor."""
    rep = validate_flow_document(doc)
    if not rep.get("ok"):
        raise ValueError("documento inválido: " + str(rep.get("errors") or []))
    norm = rep.get("normalized") or doc
    plan = compile_flow_plan(norm)
    if not plan.get("ok"):
        raise ValueError("compilação falhou: " + str(plan.get("issues") or []))
    steps = plan.get("steps") or []
    return steps_to_acoes(steps)


_MAX_CONTEUDO_CARDS = 5  # alinhado ao Flow Builder (Meta / WhatsApp + métricas)


def _expand_conteudo_items(cfg: Mapping[str, Any]) -> List[Acao]:
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
            body = str(it.get("body") or it.get("value") or "").strip()
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
                url = str(val.get("url") or "").strip()
                cap = str(val.get("caption") or "").strip()
            else:
                url = str(it.get("url") or "").strip()
                cap = str(it.get("caption") or "").strip()
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
                fn = str(it.get("filename") or "documento").strip()[:200]
                out.append(Acao(tipo="document", url=url, conteudo=fn, metadata=meta))
    return out


def steps_to_acoes(steps: List[Dict[str, Any]]) -> List[Acao]:
    acoes: List[Acao] = []
    for st in steps:
        ntype = str(st.get("type") or "generic").lower()
        cfg = st.get("config") if isinstance(st.get("config"), dict) else {}
        spec = NODE_SPECS.get(ntype) or NODE_SPECS["generic"]
        rk = str(spec.get("runtime") or "passthrough")

        if rk == "entry":
            continue
        if rk == "terminal":
            continue

        if rk == "note" or ntype == "anotacao":
            note = str(cfg.get("note") or cfg.get("body") or "").strip()
            if note:
                acoes.append(
                    Acao(tipo="text", conteudo=note[:4000], metadata={"source": "flow_builder", "kind": "note"})
                )
            continue

        if rk == "message" and ntype == "conteudo":
            expanded = _expand_conteudo_items(cfg)
            if expanded:
                acoes.extend(expanded)
                continue
            kind = str(cfg.get("content_media_kind") or "").strip().lower()
            url_media = str(cfg.get("content_media_url") or "").strip()
            caption = str(cfg.get("content_text") or cfg.get("body") or "").strip()
            if kind in ("image", "video", "audio", "document") and url_media:
                cmeta: Dict[str, Any] = {
                    "source": "flow_builder",
                    "node_type": "conteudo",
                    "conteudo_item": kind,
                }
                wd = str(cfg.get("whatsapp_delivery") or "").strip()
                if kind == "audio":
                    cmeta["send_as_voice"] = True
                    if wd == "ptt_as_recorded_now":
                        cmeta["whatsapp_delivery"] = wd
                if kind == "image":
                    acoes.append(
                        Acao(tipo="image", url=url_media, conteudo=caption[:900], metadata=cmeta)
                    )
                elif kind == "video":
                    acoes.append(
                        Acao(tipo="video", url=url_media, conteudo=caption[:900], metadata=cmeta)
                    )
                elif kind == "audio":
                    acoes.append(
                        Acao(tipo="audio", url=url_media, conteudo=url_media, metadata=cmeta)
                    )
                else:
                    fn = str(cfg.get("document_filename") or "documento").strip()[:200] or "documento"
                    acoes.append(
                        Acao(tipo="document", url=url_media, conteudo=fn, metadata=cmeta)
                    )
                continue
            body = (
                str(cfg.get("body") or cfg.get("content_text") or "").strip()
                or str(cfg.get("step_name") or "").strip()
            )
            if body:
                acoes.append(Acao(tipo="text", conteudo=body[:4000], metadata={"source": "flow_builder", "node_type": "conteudo"}))
            continue

        if rk == "message" or rk == "action":
            ak_wait = str(cfg.get("action_kind") or "").strip().lower()
            if ntype == "acao" and ak_wait in ("wait_until", "wait_for_input"):
                # Estado interno do builder: não enviar payload JSON como texto ao lead.
                continue
            body = (
                str(cfg.get("body") or cfg.get("question") or "").strip()
                or str(cfg.get("step_name") or "").strip()
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
                note = str(cfg.get("body") or "").strip()
                if note:
                    dmeta["delay_note"] = note[:400]
                acoes.append(Acao(tipo="delay", segundos=int(sec), metadata=dmeta))
            continue

        if rk == "http" and _ALLOW_HTTP:
            url = str(cfg.get("url") or "").strip()
            method = str(cfg.get("method") or "GET").upper()
            qs = str(cfg.get("query_string") or "").strip().lstrip("?")
            if qs and url and ("https://" in url or "http://" in url):
                url = url + ("&" if "?" in url else "?") + qs
            hdrs: Dict[str, str] = {}
            raw_h = cfg.get("headers")
            if isinstance(raw_h, str) and raw_h.strip():
                try:
                    parsed = json.loads(raw_h)
                    if isinstance(parsed, dict):
                        hdrs = {str(k): str(v) for k, v in parsed.items()}
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass
            body_raw = str(cfg.get("body") or "").strip()
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
                    preview = (r.text or "")[:280]
                    hmeta: Dict[str, Any] = {
                        "source": "flow_builder",
                        "http_status": r.status_code,
                    }
                    if hdrs:
                        hmeta["http_headers_sent"] = True
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

        if rk == "notify":
            msg = str(cfg.get("message") or "Notificação (flow builder)").strip()
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
            script = str(cfg.get("script") or cfg.get("body") or cfg.get("step_name") or "").strip()
            if script:
                tmeta: Dict[str, Any] = {"source": "flow_builder", "node_type": ntype}
                vp = str(cfg.get("voice_profile") or "").strip()
                if vp:
                    tmeta["voice_profile"] = vp[:64]
                acoes.append(Acao(tipo="tts", tts_template=script[:2000], metadata=tmeta))
            continue

        if rk == "llm":
            prompt = str(
                cfg.get("prompt")
                or cfg.get("instructions")
                or cfg.get("body")
                or cfg.get("step_name")
                or ""
            ).strip()
            if prompt:
                lmeta: Dict[str, Any] = {"source": "flow_builder", "node_type": ntype, "runtime": "llm"}
                for key in ("model", "temperature"):
                    v = cfg.get(key)
                    if v is not None and str(v).strip() != "":
                        lmeta[key] = str(v).strip()[:64]
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
            weights = str(cfg.get("weights") or "").strip()
            if weights:
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=f"🧪 Divisão A/B: {weights}"[:900],
                        metadata={"source": "flow_builder", "runtime": "split"},
                    )
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
                metadata.pop("__acassia_flow_blueprint__", None)
                return
            bp = db.query(models.FlowBlueprint).filter_by(id=pub.published_blueprint_id, tenant_id=tid).first()
            if not bp:
                return
            body = bp.body_json if isinstance(bp.body_json, dict) else {}
            metadata["__acassia_flow_blueprint__"] = {
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
