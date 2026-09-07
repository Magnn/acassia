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


# ─── Lunar triggers CRUD (Frente 4.2) ─────────────────────────────────


from flask_login import current_user as _current_user
from db import models as _models
from db.database import SessionLocal as _SessionLocal


@lunar_bp.route("/triggers", methods=["GET"])
@login_required
def list_triggers():
    db = _SessionLocal()
    try:
        triggers = db.query(_models.LunarTrigger).filter_by(
            tenant_id=_current_user.tenant_id,
        ).order_by(_models.LunarTrigger.created_at.desc()).all()
        return jsonify({
            "triggers": [
                {
                    "id": t.id,
                    "flow_id": t.flow_id,
                    "flow_slug": t.flow_slug,
                    "trigger_phase": t.trigger_phase,
                    "window_hours_before": t.window_hours_before,
                    "segment_filter": t.segment_filter,
                    "active": t.active,
                    "last_fired_at": t.last_fired_at.isoformat() if t.last_fired_at else None,
                    "fire_count": t.fire_count,
                    "created_at": t.created_at.isoformat(),
                } for t in triggers
            ]
        })
    finally:
        db.close()


@lunar_bp.route("/triggers", methods=["POST"])
@login_required
def create_trigger():
    body = request.get_json(silent=True) or {}
    phase = (body.get("trigger_phase") or "").strip().lower()
    flow_id = body.get("flow_id")
    flow_slug = (body.get("flow_slug") or "").strip() or None
    window = int(body.get("window_hours_before") or 0)

    if phase not in {"nova", "crescente", "cheia", "minguante"}:
        return jsonify({"error": "phase_invalid"}), 422
    if not flow_id and not flow_slug:
        return jsonify({"error": "flow_required"}), 422

    db = _SessionLocal()
    try:
        tr = _models.LunarTrigger(
            tenant_id=_current_user.tenant_id,
            flow_id=int(flow_id) if flow_id else None,
            flow_slug=flow_slug,
            trigger_phase=phase,
            window_hours_before=window,
            segment_filter=body.get("segment_filter"),
            active=bool(body.get("active", True)),
        )
        db.add(tr)
        db.commit()
        db.refresh(tr)
        return jsonify({"ok": True, "id": tr.id}), 201
    finally:
        db.close()


@lunar_bp.route("/triggers/<int:trigger_id>", methods=["PATCH"])
@login_required
def update_trigger(trigger_id: int):
    body = request.get_json(silent=True) or {}
    db = _SessionLocal()
    try:
        tr = db.query(_models.LunarTrigger).filter_by(
            id=trigger_id, tenant_id=_current_user.tenant_id,
        ).first()
        if not tr:
            return jsonify({"error": "not_found"}), 404
        if "active" in body:
            tr.active = bool(body["active"])
        if "trigger_phase" in body:
            phase = body["trigger_phase"].strip().lower()
            if phase in {"nova", "crescente", "cheia", "minguante"}:
                tr.trigger_phase = phase
        if "window_hours_before" in body:
            tr.window_hours_before = int(body["window_hours_before"])
        if "segment_filter" in body:
            tr.segment_filter = body["segment_filter"]
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@lunar_bp.route("/triggers/<int:trigger_id>", methods=["DELETE"])
@login_required
def delete_trigger(trigger_id: int):
    db = _SessionLocal()
    try:
        tr = db.query(_models.LunarTrigger).filter_by(
            id=trigger_id, tenant_id=_current_user.tenant_id,
        ).first()
        if not tr:
            return jsonify({"error": "not_found"}), 404
        db.delete(tr)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
