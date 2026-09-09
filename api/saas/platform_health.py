"""
api/saas/platform_health.py — Health Check, Rate Limiting & Feature Analytics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints:
  GET  /health                        — Liveness check (k8s/docker)
  GET  /health/ready                  — Readiness check (DB + IA)
  POST /api/telemetry/event           — Feature analytics tracking
  GET  /api/telemetry/feature-usage   — Admin: quais features estão sendo usadas
"""

from __future__ import annotations

import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, request, g
from flask_login import current_user

from db.database import SessionLocal

logger = logging.getLogger(__name__)
health_bp = Blueprint("platform_health", __name__)

# ── In-memory rate limiter (sem Redis - adequado para single-process) ────────
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMITS = {
    "ai_reading": (5, 60),      # 5 per minute
    "ai_palm": (3, 60),         # 3 per minute
    "ai_social": (10, 60),      # 10 per minute
    "ai_ritual": (10, 60),      # 10 per minute
    "ai_dream": (5, 60),        # 5 per minute
    "ai_coach": (10, 60),       # 10 per minute
    "default": (30, 60),        # 30 per minute
}


def rate_limit(category: str = "default"):
    """Decorator para rate limiting por tenant."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            key = f"rl:{category}:{_get_identity()}"
            max_requests, window = RATE_LIMITS.get(category, RATE_LIMITS["default"])
            now = time.time()
            # Clean old entries
            _rate_store[key] = [t for t in _rate_store[key] if now - t < window]
            if len(_rate_store[key]) >= max_requests:
                return jsonify({
                    "error": "rate_limit_exceeded",
                    "message": f"Limite de {max_requests} requisições por minuto excedido. Tente novamente em breve.",
                    "retry_after_seconds": int(window - (now - _rate_store[key][0])) + 1,
                }), 429
            _rate_store[key].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def _get_identity() -> str:
    try:
        if current_user and current_user.is_authenticated:
            return f"user:{current_user.id}"
    except Exception:
        pass
    return f"ip:{request.remote_addr}"


# ── Health Checks ────────────────────────────────────────────────────────────

@health_bp.route("/health", methods=["GET"])
def health_liveness():
    """Liveness probe — app is running."""
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})


@health_bp.route("/health/ready", methods=["GET"])
def health_readiness():
    """Readiness probe — DB + IA are available."""
    checks = {}

    # DB check
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # IA check
    try:
        from personalizer import Personalizer
        p = Personalizer()
        checks["ai"] = "ok" if p.client else "unavailable"
    except Exception as e:
        checks["ai"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return jsonify({
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200 if all_ok else 503


# ── Feature Analytics ────────────────────────────────────────────────────────

_feature_events: list[dict] = []  # In-memory buffer — flush to DB periodically


def track_event():
    """Recebe eventos de analytics do frontend."""
    data = request.get_json(silent=True) or {}
    event = data.get("event", "")
    props = data.get("props", {})

    if not event:
        return jsonify({"ok": True})  # Silently ignore bad events

    tenant_id = None
    user_id = None
    try:
        if current_user and current_user.is_authenticated:
            tenant_id = current_user.tenant_id
            user_id = current_user.id
    except Exception:
        pass

    _feature_events.append({
        "event": event,
        "props": props,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "ip": request.remote_addr,
        "ua": request.headers.get("User-Agent", "")[:200],
        "at": datetime.now(timezone.utc).isoformat(),
    })

    # Keep buffer manageable (max 10k events in memory)
    if len(_feature_events) > 10000:
        _feature_events.pop(0)

    return jsonify({"ok": True})


@health_bp.route("/api/telemetry/feature-usage", methods=["GET"])
def feature_usage():
    """Admin: Quais features estão sendo usadas e com que frequência."""
    try:
        if not current_user or not current_user.is_authenticated:
            return jsonify({"error": "unauthorized"}), 401
    except Exception:
        return jsonify({"error": "unauthorized"}), 401

    # Aggregate by event name
    usage: dict[str, int] = defaultdict(int)
    tenant_filter = request.args.get("tenant_id")

    for evt in _feature_events:
        if tenant_filter and str(evt.get("tenant_id")) != tenant_filter:
            continue
        usage[evt["event"]] += 1

    # Sort by count
    sorted_usage = sorted(usage.items(), key=lambda x: x[1], reverse=True)

    return jsonify({
        "total_events": len(_feature_events),
        "features": [{"event": k, "count": v} for k, v in sorted_usage],
    })
