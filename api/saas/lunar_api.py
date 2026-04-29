"""
Lunar calendar endpoints (Frente 4.1).

GET /saas/lunar/today              — fase atual
GET /saas/lunar/calendar           — range de datas
GET /saas/lunar/next/<phase>       — próxima ocorrência de fase
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import login_required


lunar_bp = Blueprint("saas_lunar", __name__, url_prefix="/saas/lunar")


@lunar_bp.route("/today", methods=["GET"])
@login_required
def today():
    import lunar
    return jsonify(lunar.phase_for_date())


@lunar_bp.route("/calendar", methods=["GET"])
@login_required
def calendar():
    """Query: ?from=YYYY-MM-DD&to=YYYY-MM-DD (default últimos 30d + próximos 30d)."""
    import lunar
    from_str = request.args.get("from")
    to_str = request.args.get("to")

    now = datetime.now(timezone.utc)
    if from_str:
        try:
            from_dt = datetime.fromisoformat(from_str).replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "from_invalid"}), 422
    else:
        from_dt = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

    if to_str:
        try:
            to_dt = datetime.fromisoformat(to_str).replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "to_invalid"}), 422
    else:
        to_dt = (now + timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)

    if (to_dt - from_dt).days > 365:
        return jsonify({"error": "range_too_large", "max_days": 365}), 422

    items = lunar.calendar_range(from_date=from_dt, to_date=to_dt)
    return jsonify({"items": items, "from": from_dt.isoformat(), "to": to_dt.isoformat()})


@lunar_bp.route("/next/<phase>", methods=["GET"])
@login_required
def next_occurrence(phase):
    import lunar
    valid = {"nova", "crescente", "cheia", "minguante"}
    if phase not in valid:
        return jsonify({"error": "phase_invalid", "valid": sorted(valid)}), 422
    next_dt = lunar.next_phase(phase)
    days = (next_dt - datetime.now(timezone.utc)).days
    return jsonify({
        "phase": phase,
        "next_date": next_dt.strftime("%Y-%m-%d"),
        "days_until": days,
    })
