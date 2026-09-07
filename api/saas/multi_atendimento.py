"""
api/saas/multi_atendimento.py — Multi-Atendimento Pro (DevZapp DevChat)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Departamentos, transferência, fila de espera, horário de atendimento,
avaliação NPS, métricas de atendentes.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
multi_bp = Blueprint("multi_atendimento", __name__, url_prefix="/saas/atendimento")


# ═══════ DEPARTMENTS ═══════

@multi_bp.route("/departments", methods=["GET"])
@login_required
def list_departments():
    db = SessionLocal()
    try:
        depts = (
            db.query(models.Department)
            .filter_by(tenant_id=current_user.tenant_id, active=True)
            .order_by(models.Department.sort_order).all()
        )
        return jsonify({"departments": [{
            "id": d.id, "name": d.name, "slug": d.slug, "emoji": d.emoji,
            "description": d.description, "auto_reply": d.auto_reply,
            "sort_order": d.sort_order,
        } for d in depts]})
    finally:
        db.close()


@multi_bp.route("/departments", methods=["POST"])
@login_required
def create_department():
    db = SessionLocal()
    try:
        data = request.json or {}
        d = models.Department(
            tenant_id=current_user.tenant_id,
            name=data["name"],
            slug=data.get("slug", data["name"].lower().replace(" ", "_")),
            emoji=data.get("emoji", "📋"),
            description=data.get("description"),
            auto_reply=data.get("auto_reply"),
            sort_order=data.get("sort_order", 0),
        )
        db.add(d)
        db.commit()
        return jsonify({"ok": True, "department_id": d.id}), 201
    finally:
        db.close()


@multi_bp.route("/departments/<int:dept_id>", methods=["PUT"])
@login_required
def update_department(dept_id):
    db = SessionLocal()
    try:
        d = db.query(models.Department).filter_by(
            id=dept_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not found"}), 404
        data = request.json or {}
        for k in ("name", "slug", "emoji", "description", "auto_reply", "sort_order", "active"):
            if k in data:
                setattr(d, k, data[k])
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@multi_bp.route("/departments/<int:dept_id>", methods=["DELETE"])
@login_required
def delete_department(dept_id):
    db = SessionLocal()
    try:
        d = db.query(models.Department).filter_by(
            id=dept_id, tenant_id=current_user.tenant_id
        ).first()
        if not d:
            return jsonify({"error": "not found"}), 404
        d.active = False
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ CONVERSATION TRANSFER ═══════

@multi_bp.route("/transfer", methods=["POST"])
@login_required
def transfer_conversation():
    db = SessionLocal()
    try:
        data = request.json or {}
        lead_id = data.get("lead_id")
        to_user_id = data.get("to_user_id")
        to_dept_id = data.get("to_department_id")
        reason = data.get("reason", "")

        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id
        ).first()
        if not lead:
            return jsonify({"error": "Lead not found"}), 404

        transfer = models.ConversationTransfer(
            tenant_id=current_user.tenant_id,
            lead_id=lead_id,
            from_user_id=current_user.id,
            to_user_id=to_user_id,
            to_department_id=to_dept_id,
            reason=reason,
        )
        db.add(transfer)
        db.commit()

        logger.info("[transfer] Lead %d: user %d → user %s / dept %s",
                     lead_id, current_user.id, to_user_id, to_dept_id)
        return jsonify({"ok": True, "transfer_id": transfer.id})
    finally:
        db.close()


@multi_bp.route("/transfers", methods=["GET"])
@login_required
def list_transfers():
    db = SessionLocal()
    try:
        transfers = (
            db.query(models.ConversationTransfer)
            .filter_by(tenant_id=current_user.tenant_id)
            .order_by(models.ConversationTransfer.transferred_at.desc())
            .limit(100).all()
        )
        result = []
        for t in transfers:
            lead = db.query(models.Lead).filter_by(id=t.lead_id).first()
            result.append({
                "id": t.id, "lead_id": t.lead_id,
                "lead_name": lead.nome or lead.telefone if lead else "?",
                "from_user_id": t.from_user_id, "to_user_id": t.to_user_id,
                "to_department_id": t.to_department_id,
                "reason": t.reason,
                "transferred_at": t.transferred_at.isoformat() if t.transferred_at else None,
            })
        return jsonify({"transfers": result})
    finally:
        db.close()


# ═══════ QUEUE ═══════

@multi_bp.route("/queue", methods=["GET"])
@login_required
def get_queue():
    db = SessionLocal()
    try:
        entries = (
            db.query(models.QueueEntry)
            .filter_by(tenant_id=current_user.tenant_id, status="waiting")
            .order_by(models.QueueEntry.position).all()
        )
        result = []
        for e in entries:
            lead = db.query(models.Lead).filter_by(id=e.lead_id).first()
            result.append({
                "id": e.id, "lead_id": e.lead_id,
                "lead_name": lead.nome or lead.telefone if lead else "?",
                "position": e.position,
                "department_id": e.department_id,
                "entered_at": e.entered_at.isoformat() if e.entered_at else None,
                "wait_minutes": round((datetime.now(timezone.utc) - e.entered_at).total_seconds() / 60, 1) if e.entered_at else 0,
            })
        return jsonify({"queue": result, "total_waiting": len(result)})
    finally:
        db.close()


@multi_bp.route("/queue/add", methods=["POST"])
@login_required
def add_to_queue():
    db = SessionLocal()
    try:
        data = request.json or {}
        max_pos = db.query(func.max(models.QueueEntry.position)).filter_by(
            tenant_id=current_user.tenant_id, status="waiting"
        ).scalar() or 0
        entry = models.QueueEntry(
            tenant_id=current_user.tenant_id,
            lead_id=data["lead_id"],
            department_id=data.get("department_id"),
            position=max_pos + 1,
        )
        db.add(entry)
        db.commit()
        return jsonify({"ok": True, "position": entry.position}), 201
    finally:
        db.close()


@multi_bp.route("/queue/<int:entry_id>/serve", methods=["POST"])
@login_required
def serve_from_queue(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(models.QueueEntry).filter_by(
            id=entry_id, tenant_id=current_user.tenant_id
        ).first()
        if not entry:
            return jsonify({"error": "not found"}), 404
        entry.status = "serving"
        entry.served_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "lead_id": entry.lead_id})
    finally:
        db.close()


@multi_bp.route("/queue/<int:entry_id>/complete", methods=["POST"])
@login_required
def complete_queue(entry_id):
    db = SessionLocal()
    try:
        entry = db.query(models.QueueEntry).filter_by(
            id=entry_id, tenant_id=current_user.tenant_id
        ).first()
        if not entry:
            return jsonify({"error": "not found"}), 404
        entry.status = "completed"
        entry.completed_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ BUSINESS HOURS ═══════

@multi_bp.route("/business-hours", methods=["GET"])
@login_required
def get_business_hours():
    db = SessionLocal()
    try:
        bh = db.query(models.BusinessHours).filter_by(
            tenant_id=current_user.tenant_id
        ).first()
        if not bh:
            return jsonify({"hours": None, "is_open": True})

        # Check if currently open
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(bh.timezone or "America/Sao_Paulo"))
        day_map = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}
        today_key = day_map.get(now.weekday(), "mon")
        today_sched = (bh.schedule or {}).get(today_key)
        is_open = False
        if today_sched and bh.active:
            start = today_sched.get("start", "00:00")
            end = today_sched.get("end", "23:59")
            current_time = now.strftime("%H:%M")
            is_open = start <= current_time <= end

        return jsonify({
            "hours": {
                "timezone": bh.timezone, "schedule": bh.schedule,
                "away_message": bh.away_message, "active": bh.active,
            },
            "is_open": is_open,
            "current_day": today_key,
        })
    finally:
        db.close()


@multi_bp.route("/business-hours", methods=["POST"])
@login_required
def set_business_hours():
    db = SessionLocal()
    try:
        data = request.json or {}
        bh = db.query(models.BusinessHours).filter_by(
            tenant_id=current_user.tenant_id
        ).first()
        if not bh:
            bh = models.BusinessHours(tenant_id=current_user.tenant_id)
            db.add(bh)
        bh.timezone = data.get("timezone", "America/Sao_Paulo")
        bh.schedule = data.get("schedule", {
            "mon": {"start": "09:00", "end": "18:00"},
            "tue": {"start": "09:00", "end": "18:00"},
            "wed": {"start": "09:00", "end": "18:00"},
            "thu": {"start": "09:00", "end": "18:00"},
            "fri": {"start": "09:00", "end": "18:00"},
        })
        bh.away_message = data.get("away_message",
            "Olá! 💜 Nosso atendimento é de seg-sex 9h-18h. "
            "Recebemos sua mensagem e responderemos no próximo horário útil ✨")
        bh.active = data.get("active", True)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ═══════ SERVICE RATINGS (NPS) ═══════

@multi_bp.route("/ratings", methods=["GET"])
@login_required
def list_ratings():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        ratings = (
            db.query(models.ServiceRating)
            .filter_by(tenant_id=tid)
            .order_by(models.ServiceRating.created_at.desc())
            .limit(100).all()
        )
        avg = db.query(func.avg(models.ServiceRating.rating)).filter_by(tenant_id=tid).scalar()
        distribution = dict(
            db.query(models.ServiceRating.rating, func.count(models.ServiceRating.id))
            .filter_by(tenant_id=tid).group_by(models.ServiceRating.rating).all()
        )
        total = db.query(func.count(models.ServiceRating.id)).filter_by(tenant_id=tid).scalar() or 0
        promoters = db.query(func.count(models.ServiceRating.id)).filter(
            models.ServiceRating.tenant_id == tid, models.ServiceRating.rating >= 4
        ).scalar() or 0
        detractors = db.query(func.count(models.ServiceRating.id)).filter(
            models.ServiceRating.tenant_id == tid, models.ServiceRating.rating <= 2
        ).scalar() or 0
        nps = round((promoters - detractors) / max(total, 1) * 100, 1)

        result = []
        for r in ratings:
            lead = db.query(models.Lead).filter_by(id=r.lead_id).first()
            result.append({
                "id": r.id, "lead_id": r.lead_id,
                "lead_name": lead.nome or lead.telefone if lead else "?",
                "rating": r.rating, "feedback": r.feedback,
                "context": r.context,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return jsonify({
            "ratings": result,
            "average": round(float(avg or 0), 1),
            "nps_score": nps,
            "total": total,
            "distribution": distribution,
        })
    finally:
        db.close()


@multi_bp.route("/ratings", methods=["POST"])
@login_required
def create_rating():
    db = SessionLocal()
    try:
        data = request.json or {}
        r = models.ServiceRating(
            tenant_id=current_user.tenant_id,
            lead_id=data["lead_id"],
            rating=data["rating"],
            feedback=data.get("feedback"),
            context=data.get("context", "atendimento"),
        )
        db.add(r)
        db.commit()
        return jsonify({"ok": True, "rating_id": r.id}), 201
    finally:
        db.close()


# ═══════ ATTENDANT METRICS ═══════

@multi_bp.route("/metrics", methods=["GET"])
@login_required
def attendant_metrics():
    """Metrics per attendant: response times, volume, ratings."""
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        users = db.query(models.User).filter_by(tenant_id=tid).all()
        metrics = []
        for u in users:
            msgs_sent = db.query(func.count(models.Mensagem.id)).filter(
                models.Mensagem.tenant_id == tid,
                models.Mensagem.origem != "lead",
            ).scalar() or 0
            transfers_out = db.query(func.count(models.ConversationTransfer.id)).filter_by(
                tenant_id=tid, from_user_id=u.id
            ).scalar() or 0
            metrics.append({
                "user_id": u.id, "name": u.name or u.email,
                "role": u.role,
                "messages_sent": msgs_sent,
                "transfers_made": transfers_out,
            })
        return jsonify({"metrics": metrics})
    finally:
        db.close()
