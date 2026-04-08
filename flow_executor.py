"""
Executor ponta-a-ponta: plano compilado do Flow Builder → lista de Acao (schema.py).

- Tipos seguros: message (texto), delay, entry/terminal/note (no-op).
- HTTP opcional: só se FLOW_BLUEPRINT_ALLOW_HTTP=1 (timeout curto).
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Mapping, Optional

import requests

from schema import Acao
from flow_builder_runtime import NODE_SPECS, compile_flow_plan, validate_flow_document

logger = logging.getLogger(__name__)

_MAX_DELAY_S = min(120.0, float(os.getenv("FLOW_BLUEPRINT_MAX_DELAY_S", "120") or 120))
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

        if rk == "message" or rk == "action":
            body = (
                str(cfg.get("body") or cfg.get("question") or cfg.get("payload") or "").strip()
                or str(cfg.get("step_name") or "").strip()
            )
            if body:
                acoes.append(Acao(tipo="text", conteudo=body[:4000], metadata={"source": "flow_builder", "node_type": ntype}))
            continue

        if rk == "delay":
            try:
                sec = float(cfg.get("seconds") or 0)
            except (TypeError, ValueError):
                sec = 0.0
            sec = max(0.0, min(sec, _MAX_DELAY_S))
            if sec > 0:
                acoes.append(
                    Acao(tipo="delay", segundos=int(sec), metadata={"source": "flow_builder"})
                )
            continue

        if rk == "http" and _ALLOW_HTTP:
            url = str(cfg.get("url") or "").strip()
            method = str(cfg.get("method") or "GET").upper()
            if url.startswith("https://") or url.startswith("http://"):
                try:
                    r = requests.request(method, url, timeout=8)
                    preview = (r.text or "")[:280]
                    acoes.append(
                        Acao(
                            tipo="text",
                            conteudo=f"🔧 API {method} {url[:80]}… → HTTP {r.status_code}\n{preview}",
                            metadata={"source": "flow_builder", "http_status": r.status_code},
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

        # branch, split, llm, system, schedule — ignorar no envio direto (documentar no audit)
        logger.info(
            "flow_executor skip runtime=%s type=%s node_id=%s",
            rk,
            ntype,
            st.get("node_id"),
        )

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
