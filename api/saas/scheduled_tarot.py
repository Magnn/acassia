"""
API de tiragens agendadas (Frente 4.28).

Endpoints:
    GET    /saas/scheduled-readings                  — lista (filtros)
    POST   /saas/scheduled-readings                  — agenda
    GET    /saas/scheduled-readings/<id>             — detail
    POST   /saas/scheduled-readings/<id>/cancel      — cancela
    POST   /saas/scheduled-readings/<id>/execute-now — admin: roda agora
    GET    /saas/scheduled-readings/preview-when     — calcula proximo
       ?trigger_type=lunar_full → retorna data
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
import scheduled_readings as sr_engine


logger = logging.getLogger(__name__)
sched_bp = Blueprint("saas_scheduled_tarot", __name__, url_prefix="/saas/scheduled-readings")


VALID_TRIGGERS = {"lunar_full", "lunar_new", "date_specific"}
VALID_SPREADS = {"1card", "3card", "cross5", "celtic10"}


def _serialize(sr: models.ScheduledReading) -> dict:
    return {
        "id": sr.id,
        "lead_id": sr.lead_id,
        "scheduled_for": sr.scheduled_for.isoformat() if sr.scheduled_for else None,
        "trigger_type": sr.trigger_type,
        "spread_type": sr.spread_type,
        "deck_id": sr.deck_id,
        "question": sr.question,
        "status": sr.status,
        "warning_sent_at": sr.warning_sent_at.isoformat() if sr.warning_sent_at else None,
        "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
        "reading_id": sr.reading_id,
        "error_message": sr.error_message,
        "created_at": sr.created_at.isoformat(),
    }


@sched_bp.route("", methods=["GET"])
@login_required
def list_scheduled():
    status = (request.args.get("status") or "").strip().lower() or None
    lead_id = request.args.get("lead_id")
    limit = max(1, min(int(request.args.get("limit") or 50), 200))

    db = SessionLocal()
    try:
        q = db.query(models.ScheduledReading).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if status:
            q = q.filter_by(status=status)
        if lead_id and str(lead_id).isdigit():
            q = q.filter_by(lead_id=int(lead_id))
        items = q.order_by(
            models.ScheduledReading.scheduled_for.asc(),
        ).limit(limit).all()
        return jsonify({
            "items": [_serialize(s) for s in items],
            "total": len(items),
        })
    finally:
        db.close()


@sched_bp.route("", methods=["POST"])
@login_required
def create_scheduled():
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    trigger_type = (body.get("trigger_type") or "").strip().lower()
    spread_type = (body.get("spread_type") or "3card").strip().lower()
    deck_id = (body.get("deck_id") or "marselha").strip().lower()
    question = (body.get("question") or "").strip() or None
    when_str = body.get("when")

    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422
    if trigger_type not in VALID_TRIGGERS:
        return jsonify({
            "error": "trigger_type_invalid",
            "valid": sorted(VALID_TRIGGERS),
        }), 422
    if spread_type not in VALID_SPREADS:
        return jsonify({
            "error": "spread_type_invalid",
            "valid": sorted(VALID_SPREADS),
        }), 422

    when_dt = None
    if trigger_type == "date_specific":
        if not when_str:
            return jsonify({"error": "when_required_for_date_specific"}), 422
        try:
            when_dt = datetime.fromisoformat(when_str.replace("Z", "+00:00"))
            if when_dt.tzinfo is None:
                when_dt = when_dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return jsonify({"error": "when_invalid"}), 422
        if when_dt <= datetime.now(timezone.utc):
            return jsonify({"error": "when_must_be_future"}), 422

    try:
        sr = sr_engine.schedule_for_lead(
            tenant_id=current_user.tenant_id,
            lead_id=int(lead_id),
            trigger_type=trigger_type,
            spread_type=spread_type,
            deck_id=deck_id,
            question=question,
            when=when_dt,
        )
    except ValueError as exc:
        return jsonify({"error": "scheduling_failed", "message": str(exc)}), 422
    except Exception as exc:
        logger.exception("[scheduled_tarot.create] erro")
        return jsonify({"error": "internal", "message": str(exc)[:200]}), 500

    return jsonify({"ok": True, "item": _serialize(sr)}), 201


@sched_bp.route("/<int:sr_id>", methods=["GET"])
@login_required
def get_scheduled(sr_id: int):
    db = SessionLocal()
    try:
        sr = db.query(models.ScheduledReading).filter_by(
            id=sr_id, tenant_id=current_user.tenant_id,
        ).first()
        if not sr:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_serialize(sr))
    finally:
        db.close()


@sched_bp.route("/<int:sr_id>/cancel", methods=["POST"])
@login_required
def cancel(sr_id: int):
    ok = sr_engine.cancel_scheduled(sr_id, tenant_id=current_user.tenant_id)
    if not ok:
        return jsonify({"error": "cannot_cancel"}), 422
    return jsonify({"ok": True})


@sched_bp.route("/<int:sr_id>/execute-now", methods=["POST"])
@login_required
def execute_now(sr_id: int):
    """Override admin: roda imediato (util pra teste/dev)."""
    db = SessionLocal()
    try:
        sr = db.query(models.ScheduledReading).filter_by(
            id=sr_id, tenant_id=current_user.tenant_id,
        ).first()
        if not sr:
            return jsonify({"error": "not_found"}), 404
        if sr.status in ("completed", "cancelled"):
            return jsonify({"error": "already_finalized", "status": sr.status}), 422

        lead = db.query(models.Lead).filter_by(id=sr.lead_id).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        ok = sr_engine._execute_reading(sr, lead, db)
        return jsonify({
            "ok": ok,
            "status": sr.status,
            "reading_id": sr.reading_id,
            "error_message": sr.error_message,
        })
    finally:
        db.close()


@sched_bp.route("/preview-when", methods=["GET"])
@login_required
def preview_when():
    """Resolve scheduled_for sem persistir — pra UI mostrar 'agendado pra X'."""
    trigger_type = (request.args.get("trigger_type") or "").strip().lower()
    if trigger_type not in VALID_TRIGGERS:
        return jsonify({"error": "trigger_type_invalid"}), 422
    if trigger_type == "date_specific":
        return jsonify({"error": "preview_only_for_lunar"}), 422
    try:
        dt = sr_engine.resolve_scheduled_for(trigger_type)
        return jsonify({
            "trigger_type": trigger_type,
            "scheduled_for": dt.isoformat(),
            "days_from_now": (dt - datetime.now(timezone.utc)).days,
        })
    except Exception as exc:
        return jsonify({"error": "resolve_failed", "message": str(exc)[:200]}), 500
