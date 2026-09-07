"""
api/saas/subscriptions.py — Motor de Assinaturas/Pacotes do Cliente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: pacotes mensais de terapia, acompanhamento semanal, planos de sessões.

Ex: "Pacote Mensal 4 Sessões de Terapia" → R$800/mês → 4 sessões agendáveis.

Endpoints:
  GET    /saas/subscriptions/               — lista assinaturas
  POST   /saas/subscriptions/               — cria assinatura
  GET    /saas/subscriptions/<id>           — detalhe + sessões usadas
  PUT    /saas/subscriptions/<id>           — edita
  POST   /saas/subscriptions/<id>/pause     — pausa
  POST   /saas/subscriptions/<id>/resume    — reativa
  POST   /saas/subscriptions/<id>/cancel    — cancela
  POST   /saas/subscriptions/<id>/renew     — renova período (reset sessões)
  GET    /saas/subscriptions/<id>/appointments — agendamentos vinculados
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
subscriptions_bp = Blueprint("saas_subscriptions", __name__, url_prefix="/saas/subscriptions")

FREQUENCY_DAYS = {
    "weekly": 7,
    "biweekly": 14,
    "monthly": 30,
    "quarterly": 90,
}


@subscriptions_bp.route("/", methods=["GET"])
@login_required
def list_subscriptions():
    status = request.args.get("status")
    db = SessionLocal()
    try:
        q = db.query(models.ClientSubscription).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if status:
            q = q.filter_by(status=status)
        subs = q.order_by(models.ClientSubscription.created_at.desc()).limit(100).all()
        return jsonify({
            "subscriptions": [_sub_to_dict(s) for s in subs]
        })
    finally:
        db.close()


@subscriptions_bp.route("/", methods=["POST"])
@login_required
def create_subscription():
    """
    Body: {lead_id?, client_name?, client_phone?, service_id?,
           plan_name, frequency?, sessions_per_period?,
           price_cents?, starts_at?, preferred_day?, preferred_time?,
           payment_method?, notes?}
    """
    body = request.get_json(silent=True) or {}
    plan_name = (body.get("plan_name") or "").strip()
    if not plan_name or len(plan_name) < 3:
        return jsonify({"error": "plan_name_required"}), 422

    frequency = body.get("frequency", "monthly")
    if frequency not in FREQUENCY_DAYS:
        return jsonify({"error": "invalid_frequency", "valid": list(FREQUENCY_DAYS.keys())}), 422

    starts_at = _parse_dt(body.get("starts_at")) or datetime.now(timezone.utc)
    period_days = FREQUENCY_DAYS[frequency]
    period_end = starts_at + timedelta(days=period_days)

    # Resolver lead info
    lead_id = body.get("lead_id")
    client_name = (body.get("client_name") or "").strip() or None
    client_phone = (body.get("client_phone") or "").strip() or None

    db = SessionLocal()
    try:
        if lead_id and not client_name:
            lead = db.query(models.Lead).filter_by(
                id=int(lead_id), tenant_id=current_user.tenant_id,
            ).first()
            if lead:
                client_name = client_name or lead.nome
                client_phone = client_phone or lead.telefone

        sub = models.ClientSubscription(
            tenant_id=current_user.tenant_id,
            lead_id=lead_id,
            service_id=body.get("service_id"),
            client_name=client_name,
            client_phone=client_phone,
            plan_name=plan_name[:128],
            frequency=frequency,
            sessions_per_period=int(body.get("sessions_per_period", 4)),
            price_cents=int(body.get("price_cents", 0)),
            status="active",
            starts_at=starts_at,
            current_period_start=starts_at,
            current_period_end=period_end,
            payment_method=body.get("payment_method"),
            preferred_day=body.get("preferred_day"),
            preferred_time=body.get("preferred_time"),
            notes=body.get("notes"),
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

        return jsonify({"ok": True, "id": sub.id}), 201
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>", methods=["GET"])
@login_required
def get_subscription(sub_id: int):
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404

        # Contar agendamentos no período
        appts = db.query(models.Appointment).filter_by(
            subscription_id=sub_id,
        ).all()

        result = _sub_to_dict(s)
        result["appointments_summary"] = {
            "total": len(appts),
            "completed": sum(1 for a in appts if a.status == "completed"),
            "upcoming": sum(1 for a in appts if a.status in ("pending", "confirmed")),
            "cancelled": sum(1 for a in appts if a.status == "cancelled"),
        }
        return jsonify(result)
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>", methods=["PUT"])
@login_required
def update_subscription(sub_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404

        editable = [
            "plan_name", "sessions_per_period", "price_cents",
            "preferred_day", "preferred_time", "notes",
            "client_name", "client_phone", "payment_method",
        ]
        for field in editable:
            if field in body:
                setattr(s, field, body[field])

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>/pause", methods=["POST"])
@login_required
def pause_subscription(sub_id: int):
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404
        if s.status != "active":
            return jsonify({"error": "not_active"}), 409
        s.status = "paused"
        db.commit()
        return jsonify({"ok": True, "status": "paused"})
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>/resume", methods=["POST"])
@login_required
def resume_subscription(sub_id: int):
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404
        if s.status != "paused":
            return jsonify({"error": "not_paused"}), 409
        s.status = "active"
        db.commit()
        return jsonify({"ok": True, "status": "active"})
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>/cancel", methods=["POST"])
@login_required
def cancel_subscription(sub_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404
        s.status = "cancelled"
        s.cancelled_at = datetime.now(timezone.utc)
        s.notes = (s.notes or "") + f"\nMotivo: {body.get('reason', 'N/A')}"
        db.commit()
        return jsonify({"ok": True, "status": "cancelled"})
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>/renew", methods=["POST"])
@login_required
def renew_subscription(sub_id: int):
    """
    Renova período: reseta sessões usadas, avança datas.
    Chamado manualmente ou por webhook de pagamento.
    """
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404

        period_days = FREQUENCY_DAYS.get(s.frequency, 30)
        now = datetime.now(timezone.utc)

        s.current_period_start = now
        s.current_period_end = now + timedelta(days=period_days)
        s.sessions_used = 0
        s.status = "active"
        db.commit()

        return jsonify({
            "ok": True,
            "sessions_used": 0,
            "sessions_per_period": s.sessions_per_period,
            "current_period_end": s.current_period_end.isoformat(),
        })
    finally:
        db.close()


@subscriptions_bp.route("/<int:sub_id>/appointments", methods=["GET"])
@login_required
def subscription_appointments(sub_id: int):
    db = SessionLocal()
    try:
        s = db.query(models.ClientSubscription).filter_by(
            id=sub_id, tenant_id=current_user.tenant_id,
        ).first()
        if not s:
            return jsonify({"error": "not_found"}), 404

        appts = db.query(models.Appointment).filter_by(
            subscription_id=sub_id,
        ).order_by(models.Appointment.scheduled_at.desc()).limit(50).all()

        return jsonify({
            "appointments": [
                {
                    "id": a.id,
                    "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
                    "status": a.status,
                    "appointment_type": a.appointment_type,
                    "client_name": a.client_name,
                    "notes_after": a.notes_after,
                } for a in appts
            ],
            "sessions_used": s.sessions_used,
            "sessions_per_period": s.sessions_per_period,
            "sessions_remaining": max(0, s.sessions_per_period - s.sessions_used),
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _sub_to_dict(s: models.ClientSubscription) -> dict:
    return {
        "id": s.id,
        "lead_id": s.lead_id,
        "client_name": s.client_name,
        "client_phone": s.client_phone,
        "plan_name": s.plan_name,
        "frequency": s.frequency,
        "sessions_per_period": s.sessions_per_period,
        "sessions_used": s.sessions_used,
        "sessions_remaining": max(0, s.sessions_per_period - s.sessions_used),
        "price_cents": s.price_cents,
        "price_brl": s.price_cents / 100,
        "status": s.status,
        "starts_at": s.starts_at.isoformat() if s.starts_at else None,
        "current_period_start": s.current_period_start.isoformat() if s.current_period_start else None,
        "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
        "preferred_day": s.preferred_day,
        "preferred_time": s.preferred_time,
        "payment_method": s.payment_method,
        "notes": s.notes,
        "created_at": s.created_at.isoformat(),
    }


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None
