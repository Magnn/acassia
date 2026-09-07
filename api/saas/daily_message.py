"""
Mensagem do dia personalizada — config + run-now + history (Frente 4.27).

Endpoints:
    GET  /saas/daily-message/config            — config do tenant + stats
    PATCH /saas/daily-message/config           — toggle enabled/hour/tz
    POST /saas/daily-message/preview           — gera preview pra um lead
    POST /saas/daily-message/run-now           — dispara fanout agora
    GET  /saas/daily-message/recent            — historico de envios
"""

from __future__ import annotations

import logging
from datetime import date as DateT, datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
daily_msg_bp = Blueprint("saas_daily_message", __name__, url_prefix="/saas/daily-message")


def _get_var(db, tenant_id: str, key: str, default=None):
    row = db.query(models.TenantFlowVariable).filter_by(
        tenant_id=tenant_id, key=key,
    ).first()
    if not row:
        return default
    return row.value_json if row.value_json is not None else default


def _set_var(db, tenant_id: str, key: str, value) -> None:
    row = db.query(models.TenantFlowVariable).filter_by(
        tenant_id=tenant_id, key=key,
    ).first()
    if row:
        row.value_json = value
    else:
        db.add(models.TenantFlowVariable(
            tenant_id=tenant_id, key=key, value_json=value,
        ))


@daily_msg_bp.route("/config", methods=["GET"])
@login_required
def get_config():
    db = SessionLocal()
    try:
        enabled = bool(_get_var(db, current_user.tenant_id, "daily_message.enabled", False))
        hour = int(_get_var(db, current_user.tenant_id, "daily_message.hour_local", 8))
        tz = _get_var(db, current_user.tenant_id, "daily_message.timezone", "America/Sao_Paulo")
        last_run = _get_var(db, current_user.tenant_id, "daily_message.last_run_date", None)

        # Stats: leads opt-in + msgs ultimas 7d
        from sqlalchemy import or_
        total_leads = db.query(func.count(models.Lead.id)).filter(
            models.Lead.tenant_id == current_user.tenant_id,
            models.Lead.opt_out == False,  # noqa: E712
        ).scalar() or 0

        # SQLite specific JSON access
        opted_in = db.query(func.count(models.Lead.id)).filter(
            models.Lead.tenant_id == current_user.tenant_id,
            models.Lead.opt_out == False,  # noqa: E712
            func.json_extract(models.Lead.consents, "$.daily_personal_message") == 1,
        ).scalar() or 0

        cutoff = DateT.today() - timedelta(days=7)
        sent_7d = db.query(func.count(models.DailyPersonalMessage.id)).filter(
            models.DailyPersonalMessage.tenant_id == current_user.tenant_id,
            models.DailyPersonalMessage.status == "sent",
            models.DailyPersonalMessage.date >= cutoff,
        ).scalar() or 0
        failed_7d = db.query(func.count(models.DailyPersonalMessage.id)).filter(
            models.DailyPersonalMessage.tenant_id == current_user.tenant_id,
            models.DailyPersonalMessage.status == "failed",
            models.DailyPersonalMessage.date >= cutoff,
        ).scalar() or 0

        return jsonify({
            "config": {
                "enabled": enabled,
                "hour_local": hour,
                "timezone": tz,
                "last_run_date": last_run,
            },
            "stats": {
                "total_leads": int(total_leads),
                "opted_in": int(opted_in),
                "sent_7d": int(sent_7d),
                "failed_7d": int(failed_7d),
            },
        })
    finally:
        db.close()


@daily_msg_bp.route("/config", methods=["PATCH"])
@login_required
def update_config():
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        if "enabled" in body:
            _set_var(db, current_user.tenant_id,
                     "daily_message.enabled", bool(body["enabled"]))
        if "hour_local" in body:
            try:
                hr = int(body["hour_local"])
                if 0 <= hr <= 23:
                    _set_var(db, current_user.tenant_id,
                             "daily_message.hour_local", hr)
            except (TypeError, ValueError):
                return jsonify({"error": "hour_invalid"}), 422
        if "timezone" in body:
            tz = (body["timezone"] or "").strip() or None
            if tz:
                _set_var(db, current_user.tenant_id,
                         "daily_message.timezone", tz[:60])
        db.commit()

        try:
            from api.tenant_config import clear_cache
            clear_cache(current_user.tenant_id)
        except Exception:
            pass

        return jsonify({"ok": True})
    finally:
        db.close()


@daily_msg_bp.route("/preview", methods=["POST"])
@login_required
def preview():
    """Gera (sem persistir/enviar) mensagem pra um lead. Custos quota."""
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422

    try:
        import quota
        allowed, _, _ = quota.consume_quota(
            current_user.tenant_id, "gemini_tokens_month", 300,
        )
        if not allowed:
            return jsonify({"error": "quota_exceeded"}), 402
    except Exception:
        pass

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=int(lead_id), tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        try:
            import daily_personal_message as dpm
            text = dpm._gemini_for_lead(lead) or dpm._fallback_for_lead(lead)
            return jsonify({
                "ok": True,
                "lead_id": lead.id,
                "lead_name": lead.nome,
                "lead_signo": lead.signo,
                "text": text,
                "source": "gemini" if text and len(text) > 80 else "fallback",
            })
        except Exception as exc:
            return jsonify({"error": "generation_failed", "message": str(exc)[:200]}), 500
    finally:
        db.close()


@daily_msg_bp.route("/run-now", methods=["POST"])
@login_required
def run_now():
    """Dispara fanout agora — admin only no fim das contas (rate-limit)."""
    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get("dry_run"))

    try:
        import daily_personal_message as dpm
        stats = dpm.fanout_for_tenant(
            current_user.tenant_id, DateT.today(), dry_run=dry_run,
        )
        return jsonify({"ok": True, "dry_run": dry_run, "stats": stats})
    except Exception as exc:
        logger.exception("[daily_message.run_now] falha")
        return jsonify({"error": "fanout_failed", "message": str(exc)[:200]}), 500


@daily_msg_bp.route("/recent", methods=["GET"])
@login_required
def recent():
    days = max(1, min(int(request.args.get("days") or 7), 30))
    cutoff = DateT.today() - timedelta(days=days)

    db = SessionLocal()
    try:
        rows = db.query(models.DailyPersonalMessage).filter(
            models.DailyPersonalMessage.tenant_id == current_user.tenant_id,
            models.DailyPersonalMessage.date >= cutoff,
        ).order_by(
            models.DailyPersonalMessage.created_at.desc(),
        ).limit(200).all()

        return jsonify({
            "messages": [
                {
                    "id": m.id,
                    "lead_id": m.lead_id,
                    "date": m.date.isoformat(),
                    "text": m.text,
                    "source": m.source,
                    "status": m.status,
                    "chars_count": m.chars_count,
                    "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                    "error_message": m.error_message,
                    "created_at": m.created_at.isoformat(),
                } for m in rows
            ],
            "total": len(rows),
        })
    finally:
        db.close()
