"""
api/saas/sequences.py — Motor de Sequências & Drip Campaigns
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paridade 100% com ChatbotX (@chatbotx.io/sequences + @chatbotx.io/sequence-scheduler).

Permite criar réguas de nutrição multi-dias com delays programados (horas/dias),
janelas de envio permitidas (ex: 09h às 18h em dias úteis), métricas por passo
e inscrição automática de leads.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func
from api.channels.base import OutboundMessage
from api.channels.whatsapp import WhatsAppChannelAdapter

from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
sequences_bp = Blueprint("saas_sequences", __name__, url_prefix="/saas/sequences")


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _calculate_next_run_at(step: models.SequenceStep, base_time: Optional[datetime] = None) -> datetime:
    """Calcula a data/hora do próximo disparo baseado nas configurações do passo."""
    now = base_time or _agora_utc()
    if step.delay_unit == "specificTime" and step.specific_date_time:
        return step.specific_date_time

    unit = (step.delay_unit or "days").lower()
    days = step.delay_days or 0
    minutes = step.delay_minutes or 0

    if unit == "minutes":
        delta = timedelta(minutes=minutes if minutes > 0 else 1)
    elif unit == "hours":
        delta = timedelta(hours=hours_val if (hours_val := minutes // 60 or days) else 1)
    else:  # days
        delta = timedelta(days=days if days > 0 else 1, minutes=minutes)

    target_time = now + delta

    # Ajustar janela de horário se anytime for False
    if not step.anytime and step.send_time_start:
        try:
            start_h, start_m = map(int, step.send_time_start.split(":"))
            target_time = target_time.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            if target_time < now:
                target_time += timedelta(days=1)
        except Exception:
            pass

    return target_time


# ═══════════════════════════════════════════════════════════════════════
# ENDPOINTS CRUD DE SEQUÊNCIAS
# ═══════════════════════════════════════════════════════════════════════

@sequences_bp.route("", methods=["GET"])
@sequences_bp.route("/", methods=["GET"])
@login_required
def list_sequences():
    """Lista todas as sequências do tenant com métricas resumidas."""
    db = SessionLocal()
    try:
        tenant_id = current_user.tenant_id
        seqs = db.query(models.Sequence).filter_by(tenant_id=tenant_id).order_by(models.Sequence.created_at.desc()).all()

        results = []
        for s in seqs:
            subscribers_count = db.query(func.count(models.ContactOnSequence.id)).filter(
                models.ContactOnSequence.sequence_id == s.id,
                models.ContactOnSequence.status == "active",
            ).scalar() or 0

            messages_count = db.query(func.count(models.SequenceStep.id)).filter(
                models.SequenceStep.sequence_id == s.id,
            ).scalar() or 0

            results.append({
                "id": s.id,
                "name": s.name,
                "active": s.active,
                "folder_name": s.folder_name,
                "trigger_tag": s.trigger_tag,
                "subscribers": subscribers_count,
                "messages": messages_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            })

        return jsonify({"sequences": results})
    finally:
        db.close()


@sequences_bp.route("", methods=["POST"])
@sequences_bp.route("/", methods=["POST"])
@login_required
@limiter.limit("30/hour")
def create_sequence():
    """Cria uma nova sequência de nutrição."""
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name or len(name) < 2:
        return jsonify({"error": "name_required"}), 422

    db = SessionLocal()
    try:
        seq = models.Sequence(
            tenant_id=current_user.tenant_id,
            name=name[:200],
            folder_name=(body.get("folder_name") or "").strip() or None,
            trigger_tag=(body.get("trigger_tag") or "").strip().lower() or None,
            active=True,
        )
        db.add(seq)
        db.commit()
        db.refresh(seq)

        return jsonify({
            "ok": True,
            "sequence": {
                "id": seq.id,
                "name": seq.name,
                "active": seq.active,
                "folder_name": seq.folder_name,
                "trigger_tag": seq.trigger_tag,
                "subscribers": 0,
                "messages": 0,
            }
        }), 201
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>", methods=["GET"])
@login_required
def get_sequence(sequence_id: int):
    """Retorna detalhes da sequência e seus passos ordenados."""
    db = SessionLocal()
    try:
        seq = db.query(models.Sequence).filter_by(
            id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not seq:
            return jsonify({"error": "not_found"}), 404

        steps_db = db.query(models.SequenceStep).filter_by(
            sequence_id=seq.id,
        ).order_by(models.SequenceStep.order.asc()).all()

        steps = []
        tot_sent = tot_delivered = tot_seen = tot_clicked = tot_failed = 0
        for st in steps_db:
            tot_sent += st.sent_count or 0
            tot_delivered += st.delivered_count or 0
            tot_seen += st.seen_count or 0
            tot_clicked += st.clicked_count or 0
            tot_failed += st.failed_count or 0

            steps.append({
                "id": st.id,
                "order": st.order,
                "delay_days": st.delay_days,
                "delay_minutes": st.delay_minutes,
                "delay_unit": st.delay_unit,
                "specific_date_time": st.specific_date_time.isoformat() if st.specific_date_time else None,
                "is_active": st.is_active,
                "anytime": st.anytime,
                "send_time_start": st.send_time_start,
                "send_time_end": st.send_time_end,
                "send_days": st.send_days or [],
                "flow_id": st.flow_id,
                "message_template": st.message_template,
                "sent_count": st.sent_count,
                "delivered_count": st.delivered_count,
                "seen_count": st.seen_count,
                "clicked_count": st.clicked_count,
                "failed_count": st.failed_count,
            })

        subscribers_count = db.query(func.count(models.ContactOnSequence.id)).filter(
            models.ContactOnSequence.sequence_id == seq.id,
            models.ContactOnSequence.status == "active",
        ).scalar() or 0

        return jsonify({
            "sequence": {
                "id": seq.id,
                "name": seq.name,
                "active": seq.active,
                "folder_name": seq.folder_name,
                "trigger_tag": seq.trigger_tag,
                "subscribers": subscribers_count,
                "messages": len(steps),
                "created_at": seq.created_at.isoformat() if seq.created_at else None,
                "updated_at": seq.updated_at.isoformat() if seq.updated_at else None,
                "steps": steps,
                "stats": {
                    "sent": tot_sent,
                    "delivered": tot_delivered,
                    "seen": tot_seen,
                    "clicked": tot_clicked,
                    "failed": tot_failed,
                }
            }
        })
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>", methods=["PUT"])
@login_required
def update_sequence(sequence_id: int):
    """Atualiza nome, pasta ou status ativo da sequência."""
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        seq = db.query(models.Sequence).filter_by(
            id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not seq:
            return jsonify({"error": "not_found"}), 404

        if "name" in body:
            new_name = str(body["name"]).strip()
            if len(new_name) >= 2:
                seq.name = new_name[:200]
        if "active" in body:
            seq.active = bool(body["active"])
        if "folder_name" in body:
            seq.folder_name = str(body["folder_name"]).strip() or None
        if "trigger_tag" in body:
            seq.trigger_tag = str(body["trigger_tag"]).strip().lower() or None

        seq.updated_at = _agora_utc()
        db.commit()

        return jsonify({
            "ok": True,
            "sequence": {
                "id": seq.id,
                "name": seq.name,
                "active": seq.active,
                "folder_name": seq.folder_name,
            }
        })
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>/rename", methods=["PATCH"])
@login_required
def rename_sequence(sequence_id: int):
    """Renomeia a sequência rapidamente."""
    body = request.get_json(silent=True) or {}
    new_name = (body.get("name") or "").strip()
    if not new_name or len(new_name) < 2:
        return jsonify({"error": "name_required"}), 422

    db = SessionLocal()
    try:
        seq = db.query(models.Sequence).filter_by(
            id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not seq:
            return jsonify({"error": "not_found"}), 404

        seq.name = new_name[:200]
        seq.updated_at = _agora_utc()
        db.commit()
        return jsonify({"ok": True, "id": seq.id, "name": seq.name})
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>", methods=["DELETE"])
@login_required
def delete_sequence(sequence_id: int):
    """Exclui uma sequência e desmatricula todos os leads."""
    db = SessionLocal()
    try:
        seq = db.query(models.Sequence).filter_by(
            id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not seq:
            return jsonify({"error": "not_found"}), 404

        # Cascading deletes
        db.query(models.SequenceDispatch).filter_by(sequence_id=seq.id).delete()
        db.query(models.ContactOnSequence).filter_by(sequence_id=seq.id).delete()
        db.query(models.SequenceStep).filter_by(sequence_id=seq.id).delete()
        db.delete(seq)
        db.commit()
        return jsonify({"ok": True, "message": "Sequência excluída com sucesso."})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# GESTÃO DE PASSOS (STEPS)
# ═══════════════════════════════════════════════════════════════════════

@sequences_bp.route("/<int:sequence_id>/steps", methods=["POST"])
@login_required
def add_sequence_step(sequence_id: int):
    """Adiciona um novo passo na esteira de nutrição."""
    db = SessionLocal()
    try:
        seq = db.query(models.Sequence).filter_by(
            id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not seq:
            return jsonify({"error": "sequence_not_found"}), 404

        body = request.get_json(silent=True) or {}
        existing_count = db.query(func.count(models.SequenceStep.id)).filter_by(sequence_id=seq.id).scalar() or 0

        step = models.SequenceStep(
            sequence_id=seq.id,
            tenant_id=current_user.tenant_id,
            order=int(body.get("order", existing_count)),
            delay_days=int(body.get("delay_days", 1)),
            delay_minutes=int(body.get("delay_minutes", 0)),
            delay_unit=str(body.get("delay_unit", "days")),
            is_active=bool(body.get("is_active", True)),
            anytime=bool(body.get("anytime", True)),
            send_time_start=body.get("send_time_start", "09:00"),
            send_time_end=body.get("send_time_end", "18:00"),
            send_days=body.get("send_days", ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]),
            flow_id=body.get("flow_id"),
            message_template=body.get("message_template"),
        )
        db.add(step)
        seq.updated_at = _agora_utc()
        db.commit()
        db.refresh(step)

        return jsonify({
            "ok": True,
            "step": {
                "id": step.id,
                "order": step.order,
                "delay_days": step.delay_days,
                "delay_minutes": step.delay_minutes,
                "delay_unit": step.delay_unit,
                "is_active": step.is_active,
                "anytime": step.anytime,
                "send_time_start": step.send_time_start,
                "send_time_end": step.send_time_end,
                "send_days": step.send_days,
                "flow_id": step.flow_id,
                "message_template": step.message_template,
            }
        }), 201
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>/steps/<int:step_id>", methods=["PUT"])
@login_required
def update_sequence_step(sequence_id: int, step_id: int):
    """Atualiza configurações de um passo existente."""
    db = SessionLocal()
    try:
        step = db.query(models.SequenceStep).filter_by(
            id=step_id,
            sequence_id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not step:
            return jsonify({"error": "step_not_found"}), 404

        body = request.get_json(silent=True) or {}
        if "order" in body:
            step.order = int(body["order"])
        if "delay_days" in body:
            step.delay_days = int(body["delay_days"])
        if "delay_minutes" in body:
            step.delay_minutes = int(body["delay_minutes"])
        if "delay_unit" in body:
            step.delay_unit = str(body["delay_unit"])
        if "is_active" in body:
            step.is_active = bool(body["is_active"])
        if "anytime" in body:
            step.anytime = bool(body["anytime"])
        if "send_time_start" in body:
            step.send_time_start = body["send_time_start"]
        if "send_time_end" in body:
            step.send_time_end = body["send_time_end"]
        if "send_days" in body:
            step.send_days = body["send_days"]
        if "flow_id" in body:
            step.flow_id = body["flow_id"]
        if "message_template" in body:
            step.message_template = body["message_template"]

        db.commit()
        return jsonify({"ok": True, "step_id": step.id})
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>/steps/<int:step_id>", methods=["DELETE"])
@login_required
def delete_sequence_step(sequence_id: int, step_id: int):
    """Remove um passo da sequência e reordena os demais."""
    db = SessionLocal()
    try:
        step = db.query(models.SequenceStep).filter_by(
            id=step_id,
            sequence_id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not step:
            return jsonify({"error": "step_not_found"}), 404

        db.delete(step)
        db.commit()

        # Reordenar passos restantes
        remaining = db.query(models.SequenceStep).filter_by(
            sequence_id=sequence_id,
        ).order_by(models.SequenceStep.order.asc()).all()

        for idx, s in enumerate(remaining):
            s.order = idx
        db.commit()

        return jsonify({"ok": True, "message": "Passo excluído com sucesso."})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# INSCRIÇÃO & GESTÃO DE LEADS (ENROLLMENT)
# ═══════════════════════════════════════════════════════════════════════

@sequences_bp.route("/<int:sequence_id>/enroll", methods=["POST"])
@login_required
def enroll_lead(sequence_id: int):
    """
    Inscreve um ou múltiplos leads na sequência.
    Body: {"lead_id": 123} ou {"lead_ids": [123, 456]}
    """
    body = request.get_json(silent=True) or {}
    lead_ids = body.get("lead_ids") or ([body["lead_id"]] if "lead_id" in body else [])
    if not lead_ids:
        return jsonify({"error": "lead_id_or_lead_ids_required"}), 422

    db = SessionLocal()
    try:
        seq = db.query(models.Sequence).filter_by(
            id=sequence_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not seq:
            return jsonify({"error": "sequence_not_found"}), 404

        first_step = db.query(models.SequenceStep).filter_by(
            sequence_id=seq.id,
            order=0,
            is_active=True,
        ).first()

        enrolled_count = 0
        now = _agora_utc()

        for lid in lead_ids:
            # Checar se já está inscrito
            existing = db.query(models.ContactOnSequence).filter_by(
                sequence_id=seq.id,
                lead_id=lid,
            ).first()

            if existing:
                if existing.status != "active":
                    existing.status = "active"
                    existing.current_step = 0
                    existing.enrolled_at = now
                    existing.completed_at = None
                    existing.next_run_at = _calculate_next_run_at(first_step, now) if first_step else now
                    enrolled_count += 1
                continue

            next_run = _calculate_next_run_at(first_step, now) if first_step else now
            enrollment = models.ContactOnSequence(
                tenant_id=current_user.tenant_id,
                sequence_id=seq.id,
                lead_id=lid,
                current_step=0,
                status="active",
                next_run_at=next_run,
                enrolled_at=now,
            )
            db.add(enrollment)
            enrolled_count += 1

        db.commit()
        return jsonify({
            "ok": True,
            "enrolled_count": enrolled_count,
            "message": f"{enrolled_count} contatos inscritos com sucesso na sequência.",
        })
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>/unenroll", methods=["POST"])
@login_required
def unenroll_lead(sequence_id: int):
    """Cancela a inscrição de um lead na sequência."""
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422

    db = SessionLocal()
    try:
        enrollment = db.query(models.ContactOnSequence).filter_by(
            sequence_id=sequence_id,
            lead_id=lead_id,
            tenant_id=current_user.tenant_id,
        ).first()
        if not enrollment:
            return jsonify({"error": "not_enrolled"}), 404

        enrollment.status = "cancelled"
        enrollment.next_run_at = None
        db.commit()
        return jsonify({"ok": True, "message": "Inscrição cancelada."})
    finally:
        db.close()


@sequences_bp.route("/<int:sequence_id>/contacts", methods=["GET"])
@login_required
def list_sequence_contacts(sequence_id: int):
    """Lista os contatos inscritos nesta sequência e o status de cada um."""
    db = SessionLocal()
    try:
        enrollments = db.query(
            models.ContactOnSequence,
            models.Lead.nome,
            models.Lead.telefone,
        ).join(
            models.Lead,
            models.Lead.id == models.ContactOnSequence.lead_id,
        ).filter(
            models.ContactOnSequence.sequence_id == sequence_id,
            models.ContactOnSequence.tenant_id == current_user.tenant_id,
        ).order_by(models.ContactOnSequence.enrolled_at.desc()).limit(100).all()

        results = []
        for en, nome, telefone in enrollments:
            results.append({
                "id": en.id,
                "lead_id": en.lead_id,
                "name": nome or "Sem nome",
                "phone": telefone,
                "current_step": en.current_step,
                "status": en.status,
                "enrolled_at": en.enrolled_at.isoformat() if en.enrolled_at else None,
                "next_run_at": en.next_run_at.isoformat() if en.next_run_at else None,
                "completed_at": en.completed_at.isoformat() if en.completed_at else None,
            })

        return jsonify({"contacts": results})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# MOTOR DE DISPARO DE SEQUÊNCIAS (DISPATCH WORKER)
# ═══════════════════════════════════════════════════════════════════════

def process_due_sequence_steps(tenant_id: Optional[str] = None) -> int:
    """
    Executa os disparos devidos de sequências ativas (next_run_at <= agora).
    Pode ser invocado por cronjob ou sob demanda.
    """
    db = SessionLocal()
    processed_count = 0
    now = _agora_utc()

    try:
        query = db.query(models.ContactOnSequence).filter(
            models.ContactOnSequence.status == "active",
            models.ContactOnSequence.next_run_at <= now,
        )
        if tenant_id:
            query = query.filter(models.ContactOnSequence.tenant_id == tenant_id)

        due_enrollments = query.limit(50).all()
        if not due_enrollments:
            return 0

        for en in due_enrollments:
            # Claim the row atomically. A crashed worker releases it after 15 minutes.
            claimed = db.query(models.ContactOnSequence).filter(
                models.ContactOnSequence.id == en.id,
                models.ContactOnSequence.status == "active",
                models.ContactOnSequence.next_run_at <= now,
            ).update({models.ContactOnSequence.next_run_at: now + timedelta(minutes=15)}, synchronize_session=False)
            db.commit()
            if claimed != 1:
                continue
            db.refresh(en)

            step = db.query(models.SequenceStep).filter_by(
                sequence_id=en.sequence_id,
                order=en.current_step,
                is_active=True,
            ).first()

            if not step:
                # Sem passo válido, avança ou completa
                en.status = "completed"
                en.completed_at = now
                en.next_run_at = None
                db.commit()
                continue

            lead = db.query(models.Lead).filter_by(id=en.lead_id).first()
            if not lead or not lead.telefone:
                en.status = "failed"
                en.last_error = "Lead sem telefone"
                db.commit()
                continue

            # A sent dispatch is the durable idempotency marker for this step.
            already_sent = db.query(models.SequenceDispatch).filter_by(
                tenant_id=en.tenant_id, sequence_id=en.sequence_id,
                step_id=step.id, lead_id=en.lead_id, status="sent",
            ).first()

            dispatch_status = "sent"
            error_msg = None
            if not already_sent:
                try:
                    msg = step.message_template or f"Olá {lead.nome or ''}, novidades na sua jornada!"
                    msg = msg.replace("{{nome}}", lead.nome or "").replace("{{telefone}}", lead.telefone or "")
                    result = WhatsAppChannelAdapter(en.tenant_id).send_message(OutboundMessage(
                        recipient_id=lead.telefone, text=msg,
                        metadata={"idempotency_key": f"sequence:{en.id}:step:{step.id}"},
                    ))
                    if not result.ok:
                        raise RuntimeError(result.error or "channel_send_failed")
                    logger.info("[SEQUENCE] Sent step=%s sequence=%s lead=%s", step.order, en.sequence_id, lead.id)
                except Exception as ex:
                    dispatch_status = "failed"
                    error_msg = str(ex)[:200]

            # Registrar histórico
            if not already_sent:
                db.add(models.SequenceDispatch(
                    tenant_id=en.tenant_id, sequence_id=en.sequence_id,
                    step_id=step.id, lead_id=en.lead_id, status=dispatch_status,
                    error_reason=error_msg, dispatched_at=now,
                ))

            if dispatch_status == "sent":
                step.sent_count = (step.sent_count or 0) + 1
            else:
                step.failed_count = (step.failed_count or 0) + 1

            if dispatch_status != "sent":
                en.last_error = error_msg
                en.next_run_at = now + timedelta(minutes=15)
                db.commit()
                processed_count += 1
                continue

            # Calcular próximo passo
            next_step = db.query(models.SequenceStep).filter_by(
                sequence_id=en.sequence_id,
                order=en.current_step + 1,
                is_active=True,
            ).first()

            if next_step:
                en.current_step += 1
                en.next_run_at = _calculate_next_run_at(next_step, now)
            else:
                en.status = "completed"
                en.completed_at = now
                en.next_run_at = None

            db.commit()
            processed_count += 1

        return processed_count
    finally:
        db.close()


@sequences_bp.route("/process-due", methods=["POST"])
@login_required
def trigger_process_due():
    """Aciona verificação de disparos devidos no tenant via fila assíncrona."""
    from api.utils.task_queue import enqueue_sequence_process
    enqueued = enqueue_sequence_process(tenant_id=current_user.tenant_id)
    if not enqueued:
        count = process_due_sequence_steps(tenant_id=current_user.tenant_id)
        return jsonify({"ok": True, "enqueued": False, "processed": count, "mode": "sync_fallback"}), 200
    return jsonify({"ok": True, "enqueued": True, "processed": 0, "mode": "queued"}), 202


def check_and_enroll_by_tags(tenant_id: str, lead_id: int, tags: list[str]) -> int:
    """Verifica se há sequências ativas com trigger_tag presente nas tags do lead e o inscreve automaticamente."""
    if not tags:
        return 0
    clean_tags = [str(t).strip().lower() for t in tags if str(t).strip()]
    db = SessionLocal()
    enrolled = 0
    try:
        matching_seqs = db.query(models.Sequence).filter(
            models.Sequence.tenant_id == tenant_id,
            models.Sequence.active == True,
            models.Sequence.trigger_tag.in_(clean_tags),
        ).all()

        for seq in matching_seqs:
            # Check if already enrolled
            existing = db.query(models.ContactOnSequence).filter_by(
                sequence_id=seq.id, lead_id=lead_id
            ).first()
            if not existing:
                first_step = db.query(models.SequenceStep).filter_by(
                    sequence_id=seq.id, order=0, is_active=True
                ).first()
                now = _agora_utc()
                db.add(models.ContactOnSequence(
                    tenant_id=tenant_id,
                    sequence_id=seq.id,
                    lead_id=lead_id,
                    current_step=0,
                    status="active",
                    next_run_at=_calculate_next_run_at(first_step, now) if first_step else now,
                    enrolled_at=now,
                ))
                enrolled += 1
        if enrolled:
            db.commit()
            logger.info("[SEQUENCES] Lead %d auto-inscrito em %d sequências por tag", lead_id, enrolled)
        return enrolled
    except Exception as exc:
        logger.exception("[SEQUENCES] Erro no auto-enroll: %s", exc)
        return 0
    finally:
        db.close()
