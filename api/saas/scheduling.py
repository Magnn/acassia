"""
api/saas/scheduling.py — Motor de Agendamento & Calendário do Terapeuta
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: agenda de consultas, sessões de terapia, leituras presenciais/online.

Endpoints — Slots (disponibilidade):
  GET    /saas/scheduling/slots                — lista slots do período
  POST   /saas/scheduling/slots                — cria slot(s) de disponibilidade
  POST   /saas/scheduling/slots/bulk           — cria slots em lote (semanal)
  DELETE /saas/scheduling/slots/<id>           — remove slot
  POST   /saas/scheduling/slots/<id>/block     — bloqueia horário

Endpoints — Appointments (agendamentos):
  GET    /saas/scheduling/appointments         — lista agendamentos
  POST   /saas/scheduling/appointments         — cria agendamento manual
  GET    /saas/scheduling/appointments/<id>    — detalhe
  PUT    /saas/scheduling/appointments/<id>    — edita (notas, status)
  POST   /saas/scheduling/appointments/<id>/confirm  — confirma
  POST   /saas/scheduling/appointments/<id>/cancel   — cancela (libera slot)
  POST   /saas/scheduling/appointments/<id>/complete  — marca como concluído
  POST   /saas/scheduling/appointments/<id>/no-show   — marca no-show
  POST   /saas/scheduling/appointments/<id>/remind    — envia lembrete WA
  GET    /saas/scheduling/today               — agenda do dia
  GET    /saas/scheduling/availability        — slots livres (para booking público)
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, date, timedelta, timezone, time

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
scheduling_bp = Blueprint("saas_scheduling", __name__, url_prefix="/saas/scheduling")


# ═══════════════════════════════════════════════════════════════════════
# SLOTS — Disponibilidade
# ═══════════════════════════════════════════════════════════════════════

@scheduling_bp.route("/slots", methods=["GET"])
@login_required
def list_slots():
    """Lista slots. Filtros: ?from=2026-09-01&to=2026-09-30&booked=false"""
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    booked = request.args.get("booked")

    db = SessionLocal()
    try:
        q = db.query(models.ExpertScheduleSlot).filter_by(
            tenant_id=current_user.tenant_id,
        )

        if from_str:
            try:
                from_date = date.fromisoformat(from_str)
                q = q.filter(models.ExpertScheduleSlot.slot_date >= from_date)
            except ValueError:
                pass
        if to_str:
            try:
                to_date = date.fromisoformat(to_str)
                q = q.filter(models.ExpertScheduleSlot.slot_date <= to_date)
            except ValueError:
                pass
        if booked is not None:
            q = q.filter_by(is_booked=booked.lower() == "true")

        slots = q.order_by(models.ExpertScheduleSlot.slot_time.asc()).limit(200).all()

        return jsonify({
            "slots": [_slot_to_dict(s) for s in slots]
        })
    finally:
        db.close()


@scheduling_bp.route("/slots", methods=["POST"])
@login_required
def create_slot():
    """
    Cria 1 slot.
    Body: {slot_date, slot_time (HH:MM), duration_minutes?}
    """
    body = request.get_json(silent=True) or {}
    slot_date_str = body.get("slot_date")
    slot_time_str = body.get("slot_time")  # "14:00"
    duration = int(body.get("duration_minutes", 60))

    if not slot_date_str or not slot_time_str:
        return jsonify({"error": "slot_date_and_slot_time_required"}), 422

    try:
        d = date.fromisoformat(slot_date_str)
        h, m = map(int, slot_time_str.split(":"))
        slot_dt = datetime(d.year, d.month, d.day, h, m, tzinfo=timezone.utc)
    except Exception:
        return jsonify({"error": "invalid_date_or_time_format"}), 422

    db = SessionLocal()
    try:
        # Verificar duplicata
        existing = db.query(models.ExpertScheduleSlot).filter_by(
            tenant_id=current_user.tenant_id,
            slot_time=slot_dt,
        ).first()
        if existing:
            return jsonify({"error": "slot_already_exists"}), 409

        slot = models.ExpertScheduleSlot(
            tenant_id=current_user.tenant_id,
            slot_date=d,
            slot_time=slot_dt,
            duration_minutes=duration,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        return jsonify({"ok": True, "id": slot.id}), 201
    finally:
        db.close()


@scheduling_bp.route("/slots/bulk", methods=["POST"])
@login_required
def create_slots_bulk():
    """
    Cria slots em lote para um período.

    Body: {
        from_date: "2026-09-01", to_date: "2026-09-30",
        weekdays: [1, 2, 3, 4, 5],  // 0=seg, 6=dom
        times: ["09:00", "10:00", "14:00", "15:00"],
        duration_minutes: 60
    }
    """
    body = request.get_json(silent=True) or {}
    from_str = body.get("from_date")
    to_str = body.get("to_date")
    weekdays = body.get("weekdays", [0, 1, 2, 3, 4])  # seg-sex default
    times = body.get("times", [])
    duration = int(body.get("duration_minutes", 60))

    if not from_str or not to_str or not times:
        return jsonify({"error": "from_date_to_date_times_required"}), 422

    try:
        from_date = date.fromisoformat(from_str)
        to_date = date.fromisoformat(to_str)
    except Exception:
        return jsonify({"error": "invalid_date_format"}), 422

    if (to_date - from_date).days > 90:
        return jsonify({"error": "max_90_days"}), 422

    db = SessionLocal()
    try:
        created = 0
        skipped = 0
        current_date = from_date
        while current_date <= to_date:
            if current_date.weekday() in weekdays:
                for t_str in times:
                    try:
                        h, m = map(int, t_str.split(":"))
                        slot_dt = datetime(
                            current_date.year, current_date.month, current_date.day,
                            h, m, tzinfo=timezone.utc,
                        )
                        # Skip se já existe
                        existing = db.query(models.ExpertScheduleSlot).filter_by(
                            tenant_id=current_user.tenant_id,
                            slot_time=slot_dt,
                        ).first()
                        if existing:
                            skipped += 1
                            continue

                        db.add(models.ExpertScheduleSlot(
                            tenant_id=current_user.tenant_id,
                            slot_date=current_date,
                            slot_time=slot_dt,
                            duration_minutes=duration,
                        ))
                        created += 1
                    except Exception:
                        skipped += 1
            current_date += timedelta(days=1)

        db.commit()
        return jsonify({"ok": True, "created": created, "skipped": skipped}), 201
    finally:
        db.close()


@scheduling_bp.route("/slots/<int:slot_id>", methods=["DELETE"])
@login_required
def delete_slot(slot_id: int):
    db = SessionLocal()
    try:
        slot = db.query(models.ExpertScheduleSlot).filter_by(
            id=slot_id, tenant_id=current_user.tenant_id,
        ).first()
        if not slot:
            return jsonify({"error": "not_found"}), 404
        if slot.is_booked:
            return jsonify({"error": "slot_is_booked_cancel_appointment_first"}), 409
        db.delete(slot)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@scheduling_bp.route("/slots/<int:slot_id>/block", methods=["POST"])
@login_required
def block_slot(slot_id: int):
    """Bloqueia/desbloqueia slot manualmente."""
    db = SessionLocal()
    try:
        slot = db.query(models.ExpertScheduleSlot).filter_by(
            id=slot_id, tenant_id=current_user.tenant_id,
        ).first()
        if not slot:
            return jsonify({"error": "not_found"}), 404
        slot.is_blocked = not slot.is_blocked
        db.commit()
        return jsonify({"ok": True, "is_blocked": slot.is_blocked})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# APPOINTMENTS — Agendamentos
# ═══════════════════════════════════════════════════════════════════════

@scheduling_bp.route("/appointments", methods=["GET"])
@login_required
def list_appointments():
    """Filtros: ?status=confirmed&from=2026-09-01&to=2026-09-30&lead_id=123"""
    status = request.args.get("status")
    from_str = request.args.get("from")
    to_str = request.args.get("to")
    lead_id = request.args.get("lead_id")

    db = SessionLocal()
    try:
        q = db.query(models.Appointment).filter_by(
            tenant_id=current_user.tenant_id,
        )
        if status:
            q = q.filter_by(status=status)
        if lead_id and str(lead_id).isdigit():
            q = q.filter_by(lead_id=int(lead_id))
        if from_str:
            try:
                q = q.filter(models.Appointment.scheduled_at >= datetime.fromisoformat(from_str))
            except Exception:
                pass
        if to_str:
            try:
                to_dt = datetime.fromisoformat(to_str)
                q = q.filter(models.Appointment.scheduled_at <= to_dt + timedelta(days=1))
            except Exception:
                pass

        appts = q.order_by(models.Appointment.scheduled_at.asc()).limit(100).all()
        return jsonify({
            "appointments": [_appt_to_dict(a) for a in appts]
        })
    finally:
        db.close()


@scheduling_bp.route("/appointments", methods=["POST"])
@login_required
def create_appointment():
    """
    Cria agendamento.
    Body: {slot_id?, scheduled_at?, lead_id?, service_id?,
           client_name?, client_phone?, client_email?,
           appointment_type?, modality?, meeting_url?,
           duration_minutes?, amount_cents?, payment_method?,
           notes_before?, subscription_id?}
    """
    body = request.get_json(silent=True) or {}
    slot_id = body.get("slot_id")
    scheduled_at_str = body.get("scheduled_at")

    db = SessionLocal()
    try:
        scheduled_at = None
        duration = int(body.get("duration_minutes", 60))

        # Resolver horário via slot ou direto
        if slot_id:
            slot = db.query(models.ExpertScheduleSlot).filter_by(
                id=int(slot_id), tenant_id=current_user.tenant_id,
            ).first()
            if not slot:
                return jsonify({"error": "slot_not_found"}), 404
            if slot.is_booked or slot.is_blocked:
                return jsonify({"error": "slot_unavailable"}), 409
            scheduled_at = slot.slot_time
            duration = slot.duration_minutes
        elif scheduled_at_str:
            scheduled_at = _parse_dt(scheduled_at_str)
        else:
            return jsonify({"error": "slot_id_or_scheduled_at_required"}), 422

        if not scheduled_at:
            return jsonify({"error": "invalid_scheduled_at"}), 422

        # Resolver lead
        lead_id = body.get("lead_id")
        client_name = (body.get("client_name") or "").strip() or None
        client_phone = (body.get("client_phone") or "").strip() or None

        if lead_id and not client_name:
            lead = db.query(models.Lead).filter_by(
                id=int(lead_id), tenant_id=current_user.tenant_id,
            ).first()
            if lead:
                client_name = client_name or lead.nome
                client_phone = client_phone or lead.telefone

        appt = models.Appointment(
            tenant_id=current_user.tenant_id,
            slot_id=slot_id,
            lead_id=lead_id,
            service_id=body.get("service_id"),
            client_name=client_name,
            client_phone=client_phone,
            client_email=(body.get("client_email") or "").strip() or None,
            scheduled_at=scheduled_at,
            duration_minutes=duration,
            appointment_type=body.get("appointment_type", "consultation"),
            modality=body.get("modality", "online"),
            meeting_url=body.get("meeting_url"),
            status="pending",
            amount_cents=int(body.get("amount_cents", 0)),
            payment_method=body.get("payment_method"),
            notes_before=body.get("notes_before"),
            subscription_id=body.get("subscription_id"),
        )
        db.add(appt)

        # Marcar slot como reservado
        if slot_id:
            slot.is_booked = True
            slot.lead_id = lead_id
            slot.appointment_id = appt.id

        # Decrementar sessões da assinatura
        if body.get("subscription_id"):
            sub = db.query(models.ClientSubscription).filter_by(
                id=body["subscription_id"], tenant_id=current_user.tenant_id,
            ).first()
            if sub and sub.status == "active":
                sub.sessions_used += 1

        db.commit()
        db.refresh(appt)

        return jsonify({
            "ok": True,
            "id": appt.id,
            "scheduled_at": appt.scheduled_at.isoformat(),
        }), 201
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>", methods=["GET"])
@login_required
def get_appointment(appt_id: int):
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404
        return jsonify(_appt_to_dict(a))
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>", methods=["PUT"])
@login_required
def update_appointment(appt_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404

        editable = [
            "client_name", "client_phone", "client_email",
            "appointment_type", "modality", "meeting_url",
            "amount_cents", "payment_method", "payment_status",
            "notes_before", "notes_after",
        ]
        for field in editable:
            if field in body:
                setattr(a, field, body[field])

        if "scheduled_at" in body:
            a.scheduled_at = _parse_dt(body["scheduled_at"]) or a.scheduled_at

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>/confirm", methods=["POST"])
@login_required
def confirm_appointment(appt_id: int):
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404
        a.status = "confirmed"
        a.confirmed_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appt_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404

        a.status = "cancelled"
        a.cancelled_at = datetime.now(timezone.utc)
        a.cancel_reason = body.get("reason")

        # Liberar slot
        if a.slot_id:
            slot = db.query(models.ExpertScheduleSlot).filter_by(id=a.slot_id).first()
            if slot:
                slot.is_booked = False
                slot.lead_id = None
                slot.appointment_id = None

        # Devolver sessão da assinatura
        if a.subscription_id:
            sub = db.query(models.ClientSubscription).filter_by(id=a.subscription_id).first()
            if sub and sub.sessions_used > 0:
                sub.sessions_used -= 1

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>/complete", methods=["POST"])
@login_required
def complete_appointment(appt_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404
        a.status = "completed"
        if body.get("notes_after"):
            a.notes_after = body["notes_after"]
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>/no-show", methods=["POST"])
@login_required
def no_show_appointment(appt_id: int):
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404
        a.status = "no_show"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@scheduling_bp.route("/appointments/<int:appt_id>/remind", methods=["POST"])
@login_required
@limiter.limit("30/hour")
def remind_appointment(appt_id: int):
    """Envia lembrete via WhatsApp."""
    db = SessionLocal()
    try:
        a = db.query(models.Appointment).filter_by(
            id=appt_id, tenant_id=current_user.tenant_id,
        ).first()
        if not a:
            return jsonify({"error": "not_found"}), 404

        phone = a.client_phone
        if not phone and a.lead_id:
            lead = db.query(models.Lead).filter_by(id=a.lead_id).first()
            if lead:
                phone = lead.telefone

        if not phone:
            return jsonify({"error": "no_phone_available"}), 422

        sched_str = a.scheduled_at.strftime("%d/%m/%Y às %H:%M")
        msg = f"🔔 Lembrete: Você tem uma sessão agendada para {sched_str}."
        if a.modality == "online" and a.meeting_url:
            msg += f"\n\n📹 Link: {a.meeting_url}"

        try:
            import horoscope
            client = horoscope._get_whatsapp_client(current_user.tenant_id)
            if client:
                client.enviar_mensagem(phone, msg, formato="texto")
                a.reminder_sent = True
                db.commit()
                return jsonify({"ok": True, "sent_to": phone})
        except Exception as exc:
            logger.warning("[scheduling.remind] falhou: %s", exc)

        return jsonify({"ok": False, "error": "send_failed"}), 502
    finally:
        db.close()


@scheduling_bp.route("/today", methods=["GET"])
@login_required
def today_schedule():
    """Agenda do dia — painel rápido."""
    db = SessionLocal()
    try:
        today = date.today()
        tomorrow = today + timedelta(days=1)

        appts = db.query(models.Appointment).filter(
            models.Appointment.tenant_id == current_user.tenant_id,
            models.Appointment.scheduled_at >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc),
            models.Appointment.scheduled_at < datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=timezone.utc),
            models.Appointment.status.notin_(["cancelled"]),
        ).order_by(models.Appointment.scheduled_at.asc()).all()

        return jsonify({
            "date": today.isoformat(),
            "total": len(appts),
            "appointments": [_appt_to_dict(a) for a in appts],
        })
    finally:
        db.close()


@scheduling_bp.route("/availability", methods=["GET"])
@login_required
def get_availability():
    """
    Slots livres para booking.
    ?from=2026-09-01&to=2026-09-30&service_id=1
    """
    from_str = request.args.get("from", date.today().isoformat())
    to_str = request.args.get("to", (date.today() + timedelta(days=30)).isoformat())

    db = SessionLocal()
    try:
        q = db.query(models.ExpertScheduleSlot).filter_by(
            tenant_id=current_user.tenant_id,
            is_booked=False,
            is_blocked=False,
        )
        try:
            q = q.filter(models.ExpertScheduleSlot.slot_date >= date.fromisoformat(from_str))
            q = q.filter(models.ExpertScheduleSlot.slot_date <= date.fromisoformat(to_str))
        except Exception:
            pass

        # Só futuros
        q = q.filter(models.ExpertScheduleSlot.slot_time > datetime.now(timezone.utc))

        slots = q.order_by(models.ExpertScheduleSlot.slot_time.asc()).limit(100).all()

        return jsonify({
            "available_slots": [_slot_to_dict(s) for s in slots]
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _slot_to_dict(s: models.ExpertScheduleSlot) -> dict:
    return {
        "id": s.id,
        "slot_date": str(s.slot_date) if s.slot_date else None,
        "slot_time": s.slot_time.isoformat() if s.slot_time else None,
        "duration_minutes": s.duration_minutes,
        "is_booked": s.is_booked,
        "is_blocked": s.is_blocked,
        "lead_id": s.lead_id,
        "appointment_id": s.appointment_id,
    }


def _appt_to_dict(a: models.Appointment) -> dict:
    return {
        "id": a.id,
        "slot_id": a.slot_id,
        "lead_id": a.lead_id,
        "service_id": a.service_id,
        "client_name": a.client_name,
        "client_phone": a.client_phone,
        "client_email": a.client_email,
        "scheduled_at": a.scheduled_at.isoformat() if a.scheduled_at else None,
        "duration_minutes": a.duration_minutes,
        "appointment_type": a.appointment_type,
        "modality": a.modality,
        "meeting_url": a.meeting_url,
        "status": a.status,
        "payment_status": a.payment_status,
        "amount_cents": a.amount_cents,
        "notes_before": a.notes_before,
        "notes_after": a.notes_after,
        "reminder_sent": a.reminder_sent,
        "subscription_id": a.subscription_id,
        "created_at": a.created_at.isoformat(),
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
