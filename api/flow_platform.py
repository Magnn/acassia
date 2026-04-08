"""
Rotas da plataforma de fluxos: versões, locks, comentários, runs, secrets,
variáveis, ACL, agendamentos, export/import, diff, quotas e lint.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from flask import Flask, jsonify, request

from db import models
from db.database import SessionLocal
from tenant_context import get_request_tenant_id

logger = logging.getLogger(__name__)

_MAX_BODY_PREVIEW = 400_000
_SAFE_WEBHOOK_TEST_HOSTS = {
    h.strip().lower()
    for h in (os.getenv("FLOW_WEBHOOK_TEST_ALLOWED_HOSTS", "") or "").split(",")
    if h.strip()
}


def _secret_master_bytes() -> bytes:
    k = (os.getenv("ACASSIA_FLOW_SECRETS_KEY") or "").strip()
    if not k:
        # Fail-safe para evitar segredo previsível em produção.
        raise RuntimeError("ACASSIA_FLOW_SECRETS_KEY ausente")
    raw = k.encode("utf-8")
    return hashlib.sha256(raw).digest()


def encrypt_flow_secret(plain: str) -> str:
    k = _secret_master_bytes()
    b = plain.encode("utf-8")
    out = bytes(b[i] ^ k[i % len(k)] for i in range(len(b)))
    return base64.urlsafe_b64encode(out).decode("ascii")


def decrypt_flow_secret(cipher_b64: str) -> str:
    k = _secret_master_bytes()
    raw = base64.urlsafe_b64decode(cipher_b64.encode("ascii"))
    out = bytes(raw[i] ^ k[i % len(k)] for i in range(len(raw)))
    return out.decode("utf-8")


def _mask_secret_tail(plain: str) -> str:
    s = plain or ""
    if len(s) <= 4:
        return "****"
    return "****" + s[-4:]


def _json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        if isinstance(obj, dict):
            return {str(k): _json_safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_json_safe(x) for x in obj]
        return str(obj)


def _parse_positive_int(raw: Any, default: int, min_v: int, max_v: int) -> int:
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    return max(min_v, min(v, max_v))


def _is_blocked_webhook_host(hostname: str) -> bool:
    h = (hostname or "").strip().lower()
    if not h:
        return True
    if h in {"localhost", "127.0.0.1", "::1"}:
        return True
    if _SAFE_WEBHOOK_TEST_HOSTS and h not in _SAFE_WEBHOOK_TEST_HOSTS:
        return True
    try:
        ip = ipaddress.ip_address(h)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved)
    except ValueError:
        return False


def _bp_row(db, tid: str, bid: int) -> Optional[models.FlowBlueprint]:
    return db.query(models.FlowBlueprint).filter_by(id=bid, tenant_id=tid).first()


def _next_version_number(db, bid: int) -> int:
    m = (
        db.query(models.FlowBlueprintVersion)
        .filter(models.FlowBlueprintVersion.blueprint_id == bid)
        .order_by(models.FlowBlueprintVersion.version_number.desc())
        .first()
    )
    return int((m.version_number if m else 0) + 1)


def json_diff(a: Any, b: Any, path: str = "") -> List[Dict[str, Any]]:
    """Diff superficial JSON (paths com mudança de tipo / valor escalar / chaves)."""
    out: List[Dict[str, Any]] = []
    if type(a) != type(b) and not (isinstance(a, (dict, list)) and isinstance(b, (dict, list))):
        out.append({"path": path or "/", "kind": "type_change", "from": type(a).__name__, "to": type(b).__name__})
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys, key=lambda x: str(x)):
            p = f"{path}.{k}" if path else str(k)
            if k not in a:
                out.append({"path": p, "kind": "added"})
            elif k not in b:
                out.append({"path": p, "kind": "removed"})
            else:
                out.extend(json_diff(a[k], b[k], p))
        return out
    if isinstance(a, list) and isinstance(b, list):
        n = max(len(a), len(b))
        for i in range(n):
            p = f"{path}[{i}]"
            if i >= len(a):
                out.append({"path": p, "kind": "added"})
            elif i >= len(b):
                out.append({"path": p, "kind": "removed"})
            else:
                out.extend(json_diff(a[i], b[i], p))
        return out
    if a != b:
        out.append({"path": path or "/", "kind": "changed", "from": a, "to": b})
    return out


def record_execute_flow_run(tenant_id: str, blueprint_id: int, lead_id: int) -> Optional[int]:
    """Cria run + eventos ao disparar execute (melhor esforço; não falha o request)."""
    db = SessionLocal()
    try:
        run = models.FlowRun(
            tenant_id=tenant_id,
            blueprint_id=blueprint_id,
            lead_id=lead_id,
            status="queued",
            meta_json={"source": "api_execute"},
        )
        db.add(run)
        db.flush()
        seq = 1
        db.add(
            models.FlowRunEvent(
                run_id=run.id,
                seq=seq,
                event_type="execute_queued",
                payload_json={"blueprint_id": blueprint_id, "lead_id": lead_id},
            )
        )
        db.commit()
        return int(run.id)
    except Exception as e:
        logger.warning("[flow_platform] record_execute_flow_run: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return None
    finally:
        db.close()


def register_flow_platform_routes(app: Flask) -> None:
    """Registra rotas /api/flows/* da plataforma."""

    @app.route("/api/flows/blueprints/<int:bid>/versions", methods=["GET", "POST"])
    def api_flow_bp_versions(bid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            if request.method == "GET":
                rows = (
                    db.query(models.FlowBlueprintVersion)
                    .filter_by(blueprint_id=bid)
                    .order_by(models.FlowBlueprintVersion.version_number.desc())
                    .all()
                )
                return (
                    jsonify(
                        {
                            "ok": True,
                            "versions": [
                                {
                                    "id": r.id,
                                    "version_number": r.version_number,
                                    "note": r.note,
                                    "created_at": r.criado_em.isoformat() if r.criado_em else "",
                                }
                                for r in rows
                            ],
                        }
                    ),
                    200,
                )
            body = request.get_json(silent=True) or {}
            note = (body.get("note") or "").strip() or None
            snap = body.get("body") if isinstance(body.get("body"), dict) else None
            if snap is None:
                snap = bp.body_json if isinstance(bp.body_json, dict) else {}
            vn = _next_version_number(db, bid)
            row = models.FlowBlueprintVersion(
                blueprint_id=bid,
                version_number=vn,
                body_json=snap,
                note=note,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return (
                jsonify(
                    {
                        "ok": True,
                        "version": {
                            "id": row.id,
                            "version_number": row.version_number,
                            "note": row.note,
                            "created_at": row.criado_em.isoformat() if row.criado_em else "",
                        },
                    }
                ),
                201,
            )
        except Exception as e:
            logger.error("[API] versions %s: %s", bid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/<int:bid>/versions/<int:vid>", methods=["GET"])
    def api_flow_bp_version_one(bid: int, vid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            row = (
                db.query(models.FlowBlueprintVersion)
                .filter_by(id=vid, blueprint_id=bid)
                .first()
            )
            if not row:
                return jsonify({"ok": False, "error": "versão não encontrada"}), 404
            body = row.body_json if isinstance(row.body_json, dict) else {}
            return (
                jsonify(
                    {
                        "ok": True,
                        "version": {
                            "id": row.id,
                            "version_number": row.version_number,
                            "note": row.note,
                            "body": body,
                            "created_at": row.criado_em.isoformat() if row.criado_em else "",
                        },
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("[API] version get %s/%s: %s", bid, vid, e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/<int:bid>/versions/<int:vid>/restore", methods=["POST"])
    def api_flow_bp_version_restore(bid: int, vid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            row = (
                db.query(models.FlowBlueprintVersion)
                .filter_by(id=vid, blueprint_id=bid)
                .first()
            )
            if not row:
                return jsonify({"ok": False, "error": "versão não encontrada"}), 404
            bp.body_json = row.body_json if isinstance(row.body_json, dict) else {}
            db.commit()
            return jsonify({"ok": True, "restored_from_version": row.version_number}), 200
        except Exception as e:
            logger.error("[API] version restore %s/%s: %s", bid, vid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/<int:bid>/lock", methods=["GET", "POST", "DELETE"])
    def api_flow_bp_lock(bid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            now = datetime.now(timezone.utc)
            lock = db.query(models.FlowBlueprintLock).filter_by(blueprint_id=bid).first()
            if request.method == "GET":
                if not lock or lock.expires_at < now:
                    return jsonify({"ok": True, "locked": False}), 200
                return (
                    jsonify(
                        {
                            "ok": True,
                            "locked": True,
                            "holder": lock.lock_holder,
                            "expires_at": lock.expires_at.isoformat(),
                        }
                    ),
                    200,
                )
            if request.method == "DELETE":
                body = request.get_json(silent=True) or {}
                holder = (body.get("holder") or request.headers.get("X-Lock-Holder") or "").strip()
                if lock:
                    if lock.lock_holder != holder:
                        return jsonify({"ok": False, "error": "holder não confere"}), 409
                    db.delete(lock)
                    db.commit()
                return jsonify({"ok": True}), 200
            body = request.get_json(silent=True) or {}
            holder = (body.get("holder") or request.headers.get("X-Lock-Holder") or "").strip()
            if not holder:
                return jsonify({"ok": False, "error": "holder obrigatório"}), 400
            ttl = int(body.get("ttl_sec") or 120)
            ttl = max(10, min(ttl, 3600))
            exp = now + timedelta(seconds=ttl)
            if lock:
                if lock.expires_at >= now and lock.lock_holder != holder:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "já bloqueado",
                                "holder": lock.lock_holder,
                                "expires_at": lock.expires_at.isoformat(),
                            }
                        ),
                        409,
                    )
                lock.lock_holder = holder
                lock.expires_at = exp
                lock.tenant_id = tid
            else:
                lock = models.FlowBlueprintLock(
                    blueprint_id=bid,
                    tenant_id=tid,
                    lock_holder=holder,
                    expires_at=exp,
                )
                db.add(lock)
            db.commit()
            return jsonify({"ok": True, "expires_at": exp.isoformat(), "holder": holder}), 200
        except Exception as e:
            logger.error("[API] lock %s: %s", bid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/<int:bid>/comments", methods=["GET", "POST"])
    def api_flow_bp_comments(bid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            if request.method == "GET":
                rows = (
                    db.query(models.FlowBlueprintComment)
                    .filter_by(blueprint_id=bid, tenant_id=tid)
                    .order_by(models.FlowBlueprintComment.criado_em.desc())
                    .limit(200)
                    .all()
                )
                return (
                    jsonify(
                        {
                            "ok": True,
                            "comments": [
                                {
                                    "id": r.id,
                                    "node_ref": r.node_ref,
                                    "body": r.body,
                                    "author_label": r.author_label,
                                    "created_at": r.criado_em.isoformat() if r.criado_em else "",
                                }
                                for r in rows
                            ],
                        }
                    ),
                    200,
                )
            body = request.get_json(silent=True) or {}
            text = (body.get("body") or "").strip()
            if not text:
                return jsonify({"ok": False, "error": "body obrigatório"}), 400
            node_ref = (body.get("node_ref") or "").strip() or None
            author = (body.get("author_label") or "").strip() or None
            row = models.FlowBlueprintComment(
                blueprint_id=bid,
                tenant_id=tid,
                node_ref=node_ref,
                body=text[:20000],
                author_label=author,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return jsonify({"ok": True, "id": row.id}), 201
        except Exception as e:
            logger.error("[API] comments %s: %s", bid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/runs", methods=["GET"])
    def api_flow_runs_list():
        tid = get_request_tenant_id()
        blueprint_id = request.args.get("blueprint_id")
        limit = _parse_positive_int(request.args.get("limit"), default=50, min_v=1, max_v=200)
        db = SessionLocal()
        try:
            q = db.query(models.FlowRun).filter(models.FlowRun.tenant_id == tid)
            if blueprint_id is not None and str(blueprint_id).strip() != "":
                try:
                    q = q.filter(models.FlowRun.blueprint_id == int(blueprint_id))
                except ValueError:
                    pass
            rows = q.order_by(models.FlowRun.started_at.desc()).limit(limit).all()
            return (
                jsonify(
                    {
                        "ok": True,
                        "runs": [
                            {
                                "id": r.id,
                                "blueprint_id": r.blueprint_id,
                                "lead_id": r.lead_id,
                                "status": r.status,
                                "started_at": r.started_at.isoformat() if r.started_at else "",
                                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                            }
                            for r in rows
                        ],
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("[API] runs list: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/runs/<int:rid>", methods=["GET"])
    def api_flow_run_one(rid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            r = db.query(models.FlowRun).filter_by(id=rid, tenant_id=tid).first()
            if not r:
                return jsonify({"ok": False, "error": "run não encontrado"}), 404
            return (
                jsonify(
                    {
                        "ok": True,
                        "run": {
                            "id": r.id,
                            "blueprint_id": r.blueprint_id,
                            "lead_id": r.lead_id,
                            "status": r.status,
                            "meta": r.meta_json if isinstance(r.meta_json, dict) else {},
                            "started_at": r.started_at.isoformat() if r.started_at else "",
                            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                        },
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("[API] run %s: %s", rid, e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/runs/<int:rid>/events", methods=["GET"])
    def api_flow_run_events(rid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            r = db.query(models.FlowRun).filter_by(id=rid, tenant_id=tid).first()
            if not r:
                return jsonify({"ok": False, "error": "run não encontrado"}), 404
            rows = (
                db.query(models.FlowRunEvent)
                .filter_by(run_id=rid)
                .order_by(models.FlowRunEvent.seq.asc())
                .all()
            )
            return (
                jsonify(
                    {
                        "ok": True,
                        "events": [
                            {
                                "seq": x.seq,
                                "event_type": x.event_type,
                                "payload": x.payload_json if isinstance(x.payload_json, dict) else {},
                                "timestamp": x.timestamp.isoformat() if x.timestamp else "",
                            }
                            for x in rows
                        ],
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("[API] run events %s: %s", rid, e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/<int:bid>/runs", methods=["POST"])
    def api_flow_bp_runs_create(bid: int):
        tid = get_request_tenant_id()
        body = request.get_json(silent=True) or {}
        lead_id = body.get("lead_id")
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            lid = None
            if lead_id is not None:
                try:
                    lid = int(lead_id)
                except (TypeError, ValueError):
                    return jsonify({"ok": False, "error": "lead_id inválido"}), 400
                lead = db.get(models.Lead, lid)
                if not lead or str(getattr(lead, "tenant_id", "default") or "default") != tid:
                    return jsonify({"ok": False, "error": "lead não encontrado"}), 404
            run = models.FlowRun(
                tenant_id=tid,
                blueprint_id=bid,
                lead_id=lid,
                status="created",
                meta_json={"source": "manual_run_stub"},
            )
            db.add(run)
            db.flush()
            db.add(
                models.FlowRunEvent(
                    run_id=run.id,
                    seq=1,
                    event_type="run_created",
                    payload_json={"blueprint_id": bid},
                )
            )
            db.commit()
            db.refresh(run)
            return jsonify({"ok": True, "run_id": run.id}), 201
        except Exception as e:
            logger.error("[API] blueprint run create %s: %s", bid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/webhooks/test", methods=["POST"])
    def api_flow_webhook_test():
        body = request.get_json(silent=True) or {}
        url = (body.get("url") or "").strip()
        if not url or not (url.startswith("http://") or url.startswith("https://")):
            return jsonify({"ok": False, "error": "url http(s) obrigatória"}), 400
        pu = urlparse(url)
        if pu.scheme not in {"http", "https"}:
            return jsonify({"ok": False, "error": "apenas http/https permitido"}), 400
        if _is_blocked_webhook_host(pu.hostname or ""):
            return jsonify({"ok": False, "error": "host bloqueado para webhook test"}), 403
        method = (body.get("method") or "POST").upper()
        if method not in ("GET", "POST", "PUT", "PATCH"):
            method = "POST"
        headers = body.get("headers") if isinstance(body.get("headers"), dict) else {}
        payload = body.get("payload")
        try:
            timeout = float(body.get("timeout_sec") or 8)
        except (TypeError, ValueError):
            timeout = 8.0
        timeout = max(1.0, min(timeout, 30.0))
        try:
            if method == "GET":
                r = requests.get(url, headers=headers, timeout=timeout)
            else:
                r = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=payload if isinstance(payload, (dict, list)) else None,
                    data=None if isinstance(payload, (dict, list)) else payload,
                    timeout=timeout,
                )
            text = (r.text or "")[:8000]
            return (
                jsonify(
                    {
                        "ok": True,
                        "status_code": r.status_code,
                        "response_preview": text,
                    }
                ),
                200,
            )
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 502

    @app.route("/api/flows/schedules", methods=["GET", "POST"])
    def api_flow_schedules():
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            if request.method == "GET":
                rows = (
                    db.query(models.FlowSchedule)
                    .filter_by(tenant_id=tid)
                    .order_by(models.FlowSchedule.criado_em.desc())
                    .all()
                )
                return (
                    jsonify(
                        {
                            "ok": True,
                            "schedules": [
                                {
                                    "id": r.id,
                                    "blueprint_id": r.blueprint_id,
                                    "cron_expr": r.cron_expr,
                                    "timezone": r.timezone,
                                    "active": bool(r.active),
                                    "meta": r.meta_json if isinstance(r.meta_json, dict) else {},
                                }
                                for r in rows
                            ],
                        }
                    ),
                    200,
                )
            body = request.get_json(silent=True) or {}
            try:
                bid = int(body.get("blueprint_id"))
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "blueprint_id obrigatório"}), 400
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            cron = (body.get("cron_expr") or "").strip()
            if not cron:
                return jsonify({"ok": False, "error": "cron_expr obrigatório"}), 400
            tz = (body.get("timezone") or "America/Sao_Paulo").strip()[:64]
            meta = body.get("meta") if isinstance(body.get("meta"), dict) else {}
            row = models.FlowSchedule(
                tenant_id=tid,
                blueprint_id=bid,
                cron_expr=cron[:120],
                timezone=tz,
                active=bool(body.get("active", True)),
                meta_json=meta,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return jsonify({"ok": True, "id": row.id}), 201
        except Exception as e:
            logger.error("[API] schedules: %s", e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/schedules/<int:sid>", methods=["PATCH", "DELETE"])
    def api_flow_schedule_one(sid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            row = db.query(models.FlowSchedule).filter_by(id=sid, tenant_id=tid).first()
            if not row:
                return jsonify({"ok": False, "error": "agendamento não encontrado"}), 404
            if request.method == "DELETE":
                db.delete(row)
                db.commit()
                return jsonify({"ok": True}), 200
            body = request.get_json(silent=True) or {}
            if "cron_expr" in body:
                row.cron_expr = str(body.get("cron_expr") or "")[:120]
            if "timezone" in body:
                row.timezone = str(body.get("timezone") or "")[:64]
            if "active" in body:
                row.active = bool(body.get("active"))
            if "meta" in body and isinstance(body.get("meta"), dict):
                row.meta_json = body["meta"]
            db.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error("[API] schedule %s: %s", sid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/tenant/secrets", methods=["GET", "POST"])
    def api_flow_tenant_secrets():
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            if not (os.getenv("ACASSIA_FLOW_SECRETS_KEY") or "").strip():
                return jsonify({"ok": False, "error": "configure ACASSIA_FLOW_SECRETS_KEY"}), 503
            if request.method == "GET":
                rows = db.query(models.TenantFlowSecret).filter_by(tenant_id=tid).all()
                items = []
                for r in rows:
                    try:
                        plain = decrypt_flow_secret(r.value_cipher)
                        mask = _mask_secret_tail(plain)
                    except Exception:
                        mask = "****"
                    items.append({"key": r.key, "masked": mask, "updated_at": r.atualizado_em.isoformat() if r.atualizado_em else ""})
                return jsonify({"ok": True, "secrets": items}), 200
            body = request.get_json(silent=True) or {}
            key = (body.get("key") or "").strip()
            val = body.get("value")
            if not key or not re.match(r"^[a-zA-Z0-9_.-]{1,128}$", key):
                return jsonify({"ok": False, "error": "key inválida"}), 400
            if val is None or str(val) == "":
                return jsonify({"ok": False, "error": "value obrigatório"}), 400
            cipher = encrypt_flow_secret(str(val))
            row = db.query(models.TenantFlowSecret).filter_by(tenant_id=tid, key=key).first()
            if row:
                row.value_cipher = cipher
            else:
                row = models.TenantFlowSecret(tenant_id=tid, key=key, value_cipher=cipher)
                db.add(row)
            db.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error("[API] tenant secrets: %s", e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/tenant/secrets/<string:key>", methods=["DELETE"])
    def api_flow_tenant_secret_delete(key: str):
        tid = get_request_tenant_id()
        k = (key or "").strip()
        db = SessionLocal()
        try:
            row = db.query(models.TenantFlowSecret).filter_by(tenant_id=tid, key=k).first()
            if row:
                db.delete(row)
                db.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error("[API] secret delete: %s", e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/tenant/variables", methods=["GET", "POST"])
    def api_flow_tenant_variables():
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            if request.method == "GET":
                rows = db.query(models.TenantFlowVariable).filter_by(tenant_id=tid).all()
                return (
                    jsonify(
                        {
                            "ok": True,
                            "variables": [
                                {
                                    "key": r.key,
                                    "value": r.value_json,
                                    "updated_at": r.atualizado_em.isoformat() if r.atualizado_em else "",
                                }
                                for r in rows
                            ],
                        }
                    ),
                    200,
                )
            body = request.get_json(silent=True) or {}
            key = (body.get("key") or "").strip()
            if not key or not re.match(r"^[a-zA-Z0-9_.-]{1,128}$", key):
                return jsonify({"ok": False, "error": "key inválida"}), 400
            val = body.get("value")
            row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tid, key=key).first()
            if row:
                row.value_json = val
            else:
                row = models.TenantFlowVariable(tenant_id=tid, key=key, value_json=val)
                db.add(row)
            db.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error("[API] tenant variables: %s", e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/tenant/variables/<string:key>", methods=["DELETE"])
    def api_flow_tenant_variable_delete(key: str):
        tid = get_request_tenant_id()
        k = (key or "").strip()
        db = SessionLocal()
        try:
            row = db.query(models.TenantFlowVariable).filter_by(tenant_id=tid, key=k).first()
            if row:
                db.delete(row)
                db.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error("[API] variable delete: %s", e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/catalog/nodes", methods=["GET"])
    def api_flow_catalog_nodes():
        from flow_builder_runtime import ALLOWED_NODE_TYPES, NODE_SPECS

        nodes = []
        for t in sorted(ALLOWED_NODE_TYPES):
            spec = NODE_SPECS.get(t) or {}
            nodes.append(
                {
                    "type": t,
                    "label": spec.get("label") or t,
                    "runtime": spec.get("runtime"),
                    "required_config": list(spec.get("required_config") or []),
                    "optional_keys": list(spec.get("optional_keys") or []),
                }
            )
        return jsonify({"ok": True, "nodes": nodes}), 200

    @app.route("/api/flows/blueprints/<int:bid>/export", methods=["GET"])
    def api_flow_bp_export(bid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            body = bp.body_json if isinstance(bp.body_json, dict) else {}
            doc = {
                "exportVersion": 1,
                "exportedAt": datetime.now(timezone.utc).isoformat(),
                "tenant_id": tid,
                "blueprint": {
                    "id": bp.id,
                    "slug": bp.slug,
                    "title": bp.title,
                    "body": body,
                },
            }
            return jsonify(_json_safe(doc)), 200
        except Exception as e:
            logger.error("[API] export %s: %s", bid, e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/import", methods=["POST"])
    def api_flow_bp_import():
        tid = get_request_tenant_id()
        body = request.get_json(silent=True) or {}
        inner = body.get("blueprint") if isinstance(body.get("blueprint"), dict) else body
        title = (inner.get("title") or "").strip()
        slug = (inner.get("slug") or "").strip().lower()
        doc = inner.get("body") if isinstance(inner.get("body"), dict) else {}
        if not title:
            return jsonify({"ok": False, "error": "title obrigatório"}), 400
        if not slug:
            slug = re.sub(r"[^a-z0-9_]+", "_", title.lower()).strip("_")[:120] or "fluxo"
        db = SessionLocal()
        try:
            clash = db.query(models.FlowBlueprint).filter_by(tenant_id=tid, slug=slug[:128]).first()
            if clash:
                return jsonify({"ok": False, "error": "slug já existe neste tenant"}), 409
            row = models.FlowBlueprint(tenant_id=tid, slug=slug[:128], title=title[:300], body_json=doc)
            db.add(row)
            db.commit()
            db.refresh(row)
            return (
                jsonify(
                    {
                        "ok": True,
                        "blueprint": {
                            "id": row.id,
                            "slug": row.slug,
                            "title": row.title,
                            "created_at": row.criado_em.isoformat() if row.criado_em else "",
                        },
                    }
                ),
                201,
            )
        except Exception as e:
            logger.error("[API] import: %s", e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/blueprints/diff", methods=["POST"])
    def api_flow_bp_diff():
        body = request.get_json(silent=True) or {}
        a = body.get("a")
        b = body.get("b")
        if not isinstance(a, dict) or not isinstance(b, dict):
            return jsonify({"ok": False, "error": "a e b devem ser objetos JSON"}), 400
        changes = json_diff(a, b)
        chg = changes[:5000]
        return jsonify({"ok": True, "changes": chg, "truncated": len(changes) > 5000}), 200

    @app.route("/api/flows/blueprints/<int:bid>/acl", methods=["GET", "PUT"])
    def api_flow_bp_acl(bid: int):
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            bp = _bp_row(db, tid, bid)
            if not bp:
                return jsonify({"ok": False, "error": "fluxo não encontrado"}), 404
            if request.method == "GET":
                rows = (
                    db.query(models.FlowBlueprintAclEntry)
                    .filter_by(blueprint_id=bid, tenant_id=tid)
                    .all()
                )
                return (
                    jsonify(
                        {
                            "ok": True,
                            "acl": [
                                {"principal": r.principal, "role": r.role, "created_at": r.criado_em.isoformat() if r.criado_em else ""}
                                for r in rows
                            ],
                        }
                    ),
                    200,
                )
            body = request.get_json(silent=True) or {}
            entries = body.get("entries")
            if not isinstance(entries, list):
                return jsonify({"ok": False, "error": "entries deve ser lista"}), 400
            db.query(models.FlowBlueprintAclEntry).filter_by(blueprint_id=bid, tenant_id=tid).delete()
            for e in entries[:200]:
                if not isinstance(e, dict):
                    continue
                pr = (e.get("principal") or "").strip()[:200]
                role = (e.get("role") or "").strip().lower()[:32]
                if not pr or role not in ("owner", "editor", "viewer"):
                    continue
                db.add(
                    models.FlowBlueprintAclEntry(
                        blueprint_id=bid,
                        tenant_id=tid,
                        principal=pr,
                        role=role,
                    )
                )
            db.commit()
            return jsonify({"ok": True}), 200
        except Exception as e:
            logger.error("[API] acl %s: %s", bid, e)
            db.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/quotas", methods=["GET"])
    def api_flow_quotas():
        tid = get_request_tenant_id()
        db = SessionLocal()
        try:
            from sqlalchemy import func

            n_bp = db.query(func.count(models.FlowBlueprint.id)).filter_by(tenant_id=tid).scalar() or 0
            bp_ids = [x[0] for x in db.query(models.FlowBlueprint.id).filter_by(tenant_id=tid).all()]
            n_ver = 0
            if bp_ids:
                n_ver = (
                    db.query(func.count(models.FlowBlueprintVersion.id))
                    .filter(models.FlowBlueprintVersion.blueprint_id.in_(bp_ids))
                    .scalar()
                    or 0
                )
            n_runs = db.query(func.count(models.FlowRun.id)).filter_by(tenant_id=tid).scalar() or 0
            n_sched = db.query(func.count(models.FlowSchedule.id)).filter_by(tenant_id=tid).scalar() or 0
            return (
                jsonify(
                    {
                        "ok": True,
                        "quotas": {
                            "blueprints": int(n_bp),
                            "versions": int(n_ver),
                            "runs": int(n_runs),
                            "schedules": int(n_sched),
                        },
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("[API] quotas: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            db.close()

    @app.route("/api/flows/lint", methods=["POST"])
    def api_flow_lint():
        from flow_builder_runtime import validate_flow_document

        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            return jsonify({"ok": False, "error": "documento inválido"}), 400
        raw = json.dumps(body)
        if len(raw) > _MAX_BODY_PREVIEW:
            return jsonify({"ok": False, "error": "documento muito grande"}), 413
        rep = validate_flow_document(body)
        extra = []
        nodes = body.get("nodes") if isinstance(body.get("nodes"), list) else []
        edges = body.get("edges") if isinstance(body.get("edges"), list) else []
        if len(nodes) > 500:
            extra.append({"level": "warning", "code": "too_many_nodes", "message": "Mais de 500 nós."})
        if len(edges) > 2000:
            extra.append({"level": "warning", "code": "too_many_edges", "message": "Mais de 2000 arestas."})
        return (
            jsonify(
                _json_safe(
                    {
                        "ok": True,
                        "validation": rep,
                        "lint": extra,
                    }
                )
            ),
            200,
        )
