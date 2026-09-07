"""
api/routes/dashboard.py — Rotas do Dashboard e KPIs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extraído do app.py monolítico. Contém:
  - /api/health, /api/health/deep, /api/health/multi-tenant-summary
  - /api/stats, /api/dashboard/kpis
  - /api/executive/overview, /api/executive/department/<dep>
  - /api/diagnostics/*
  - /metrics (Prometheus)
  - /api/integrations/summary
"""

import logging
import os
import time

from flask import Blueprint, jsonify, request

from db.database import SessionLocal
from db import models
from sqlalchemy import func
from tenant_context import get_request_tenant_id

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint("dashboard", __name__)


# ── Helpers ──

def _json_safe_for_api(obj):
    """Garante que metadados aninhados serializam em JSON."""
    from decimal import Decimal
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {str(k): _json_safe_for_api(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe_for_api(x) for x in obj]
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    return str(obj)


# ── Health Check ──

@dashboard_bp.route("/api/health", methods=["GET"])
def api_health():
    """Liveness para monitoramento e debug rápido."""
    from app import _APP_STARTED_AT
    return jsonify({
        "ok": True,
        "service": "meumisterio",
        "uptime_s": int(time.time() - _APP_STARTED_AT),
    }), 200


@dashboard_bp.route("/api/health/deep", methods=["GET"])
def api_health_deep():
    """Readiness probe — checa dependências críticas (DB, Redis, Gemini)."""
    from app import _APP_STARTED_AT
    started = time.perf_counter()
    checks: dict[str, dict] = {}

    # DB: SELECT 1
    try:
        from db.database import check_db_health
        checks["database"] = check_db_health()
    except Exception as exc:
        checks["database"] = {"status": "error", "error": str(exc)[:200]}

    # Redis
    if (os.getenv("REDIS_URL") or "").strip():
        try:
            from reliability.redis_inbound import _client as _redis_client_fn
            _r = _redis_client_fn()
            if _r is not None:
                _r.ping()
                checks["redis"] = {"status": "ok"}
            else:
                checks["redis"] = {"status": "error", "error": "client not available"}
        except Exception as exc:
            checks["redis"] = {"status": "error", "error": str(exc)[:200]}
    else:
        checks["redis"] = {"status": "disabled", "reason": "REDIS_URL not set"}

    # Gemini
    if (os.getenv("GEMINI_API_KEY") or "").strip():
        checks["gemini"] = {"status": "ok", "note": "key configured (not pinged)"}
    else:
        checks["gemini"] = {"status": "disabled", "reason": "GEMINI_API_KEY not set"}

    db_ok = checks.get("database", {}).get("status") == "ok"
    overall_ok = db_ok and all(
        c.get("status") in ("ok", "disabled") for c in checks.values()
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    return jsonify({
        "ok": overall_ok,
        "service": "meumisterio",
        "uptime_s": int(time.time() - _APP_STARTED_AT),
        "elapsed_ms": elapsed_ms,
        "checks": checks,
    }), (200 if overall_ok else 503)


@dashboard_bp.route("/metrics", methods=["GET"])
def metrics_endpoint():
    """Prometheus exposition."""
    from app import _APP_STARTED_AT
    try:
        from metrics_exporter import render_metrics, check_metrics_auth
    except Exception as exc:
        return f"# error loading metrics_exporter: {exc}", 500

    if not check_metrics_auth(request.headers.get("Authorization")):
        return "Unauthorized", 401

    body = render_metrics(app_started_at=_APP_STARTED_AT)
    return body, 200, {"Content-Type": "text/plain; version=0.0.4; charset=utf-8"}
