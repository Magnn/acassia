"""
Endpoint pra frontend emitir eventos de telemetria.
Filtra eventos: só os de uma whitelist conhecida passam (evita log spam).
Rate-limit moderado pra prevenir abuse.
"""

from __future__ import annotations

import logging
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from analytics_telemetry import track
from extensions import limiter

logger = logging.getLogger(__name__)

telemetry_bp = Blueprint("telemetry", __name__, url_prefix="/api/telemetry")

# Whitelist — só estes eventos são aceitos do frontend.
# Eventos servidor-only (ex.: signup_completed, first_message_sent) NÃO entram
# aqui porque são disparados pelo próprio backend.
_ALLOWED_EVENTS = frozenset({
    "onboarding_step_completed",
    "page_viewed",
    "feature_used",
})


@telemetry_bp.route("/event", methods=["POST"])
@login_required
@limiter.limit("60/minute")
def post_event():
    body = request.get_json(silent=True) or {}
    event = (body.get("event") or "").strip()
    props = body.get("props") if isinstance(body.get("props"), dict) else {}

    if event not in _ALLOWED_EVENTS:
        return jsonify({"error": "event_not_allowed"}), 400

    track(
        event,
        tenant_id=getattr(current_user, "tenant_id", None),
        user_id=getattr(current_user, "id", None),
        **props,
    )
    return jsonify({"ok": True})
