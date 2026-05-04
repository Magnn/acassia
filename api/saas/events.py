"""
api/saas/events.py — Motor de Eventos, Retiros & Workshops
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: venda de retiros espirituais, workshops, vivências, cerimônias.

Endpoints:
  GET    /saas/events/                  — lista eventos do tenant
  POST   /saas/events/                  — cria evento
  GET    /saas/events/<id>              — detalhe + inscritos
  PUT    /saas/events/<id>              — edita evento
  DELETE /saas/events/<id>              — cancela evento
  POST   /saas/events/<id>/publish      — publica (abre inscrições)
  POST   /saas/events/<id>/register     — inscreve lead/consumidor
  GET    /saas/events/<id>/registrations — lista inscritos
  POST   /saas/events/<id>/registrations/<rid>/confirm — confirma inscrição
  POST   /saas/events/<id>/registrations/<rid>/cancel  — cancela inscrição
  POST   /saas/events/<id>/notify       — envia notificação para inscritos
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
events_bp = Blueprint("saas_events", __name__, url_prefix="/saas/events")


@events_bp.route("/", methods=["GET"])
@login_required
def list_events():
    db = SessionLocal()
    try:
        events = db.query(models.Event).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.Event.starts_at.desc()).limit(50).all()

        return jsonify({
            "events": [_event_to_dict(e) for e in events]
        })
    finally:
        db.close()


@events_bp.route("/", methods=["POST"])
@login_required
def create_event():
    """
    Body: {title, description?, event_type?, location_name?, is_online?, online_url?,
           starts_at, ends_at?, max_spots?, price_cents?, installments_max?,
           early_bird_price_cents?, early_bird_deadline?, cover_image_url?, metadata_json?}
    """
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    starts_at_str = body.get("starts_at")

    if not title or len(title) < 3:
        return jsonify({"error": "title_required"}), 422
    if not starts_at_str:
        return jsonify({"error": "starts_at_required"}), 422

    starts_at = _parse_dt(starts_at_str)
    if not starts_at:
        return jsonify({"error": "invalid_starts_at_format"}), 422

    db = SessionLocal()
    try:
        event = models.Event(
            tenant_id=current_user.tenant_id,
            created_by_user_id=current_user.id,
            title=title[:200],
            description=(body.get("description") or "").strip() or None,
            event_type=body.get("event_type", "retreat"),
            location_name=body.get("location_name"),
            location_address=body.get("location_address"),
            is_online=bool(body.get("is_online", False)),
            online_url=body.get("online_url"),
            starts_at=starts_at,
            ends_at=_parse_dt(body.get("ends_at")),
            max_spots=body.get("max_spots"),
            price_cents=int(body.get("price_cents", 0)),
            installments_max=int(body.get("installments_max", 1)),
            early_bird_price_cents=body.get("early_bird_price_cents"),
            early_bird_deadline=_parse_dt(body.get("early_bird_deadline")),
            cover_image_url=body.get("cover_image_url"),
            metadata_json=body.get("metadata_json") or {},
            status="draft",
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        return jsonify({"ok": True, "id": event.id}), 201
    finally:
        db.close()


@events_bp.route("/<int:event_id>", methods=["GET"])
@login_required
def get_event(event_id: int):
    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404

        regs = db.query(models.EventRegistration).filter_by(event_id=event_id).all()

        result = _event_to_dict(e)
        result["registrations_summary"] = {
            "total": len(regs),
            "confirmed": sum(1 for r in regs if r.status == "confirmed"),
            "waitlisted": sum(1 for r in regs if r.is_waitlist),
            "cancelled": sum(1 for r in regs if r.status == "cancelled"),
            "revenue_cents": sum(r.amount_paid_cents for r in regs if r.status == "confirmed"),
        }
        return jsonify(result)
    finally:
        db.close()


@events_bp.route("/<int:event_id>", methods=["PUT"])
@login_required
def update_event(event_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404

        editable = [
            "title", "description", "event_type", "location_name", "location_address",
            "is_online", "online_url", "max_spots", "price_cents", "installments_max",
            "early_bird_price_cents", "cover_image_url", "metadata_json",
            "waitlist_enabled",
        ]
        for field in editable:
            if field in body:
                val = body[field]
                if field == "title":
                    val = (val or "").strip()[:200]
                setattr(e, field, val)

        if "starts_at" in body:
            e.starts_at = _parse_dt(body["starts_at"]) or e.starts_at
        if "ends_at" in body:
            e.ends_at = _parse_dt(body["ends_at"])
        if "early_bird_deadline" in body:
            e.early_bird_deadline = _parse_dt(body["early_bird_deadline"])

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@events_bp.route("/<int:event_id>", methods=["DELETE"])
@login_required
def delete_event(event_id: int):
    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404
        e.status = "cancelled"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@events_bp.route("/<int:event_id>/publish", methods=["POST"])
@login_required
def publish_event(event_id: int):
    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404
        if e.status not in ("draft",):
            return jsonify({"error": "already_published"}), 409

        e.status = "published"
        e.published_at = datetime.now(timezone.utc)
        db.commit()

        return jsonify({"ok": True, "status": "published"})
    finally:
        db.close()


@events_bp.route("/<int:event_id>/register", methods=["POST"])
@login_required
def register_for_event(event_id: int):
    """
    Inscreve um lead/consumidor no evento.

    Body: {lead_id?, name?, phone?, email?, payment_method?, payment_id?, amount_paid_cents?, coupon_code?}
    """
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404
        if e.status not in ("published",):
            return jsonify({"error": "event_not_open"}), 409

        # Verificar vagas
        is_waitlist = False
        if e.max_spots and e.spots_taken >= e.max_spots:
            if e.waitlist_enabled:
                is_waitlist = True
            else:
                return jsonify({"error": "sold_out"}), 409

        # Calcular preço (early bird?)
        price = e.price_cents
        now = datetime.now(timezone.utc)
        if e.early_bird_price_cents and e.early_bird_deadline:
            deadline = e.early_bird_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if now < deadline:
                price = e.early_bird_price_cents

        # Cupom
        discount = 0
        coupon_code = body.get("coupon_code")
        if coupon_code:
            coupon = db.query(models.Coupon).filter_by(
                tenant_id=current_user.tenant_id,
                code=coupon_code.upper().strip(),
                is_active=True,
            ).first()
            if coupon and (coupon.applies_to in ("event", "all", None)):
                if coupon.max_uses is None or coupon.used_count < coupon.max_uses:
                    if coupon.discount_type == "percent":
                        discount = int(price * coupon.discount_value / 100)
                    else:
                        discount = coupon.discount_value * 100
                    coupon.used_count += 1

        final_price = max(0, price - discount)

        reg = models.EventRegistration(
            event_id=event_id,
            tenant_id=current_user.tenant_id,
            lead_id=body.get("lead_id"),
            name=(body.get("name") or "").strip() or None,
            phone=(body.get("phone") or "").strip() or None,
            email=(body.get("email") or "").strip() or None,
            status="waitlisted" if is_waitlist else ("confirmed" if final_price == 0 else "pending"),
            is_waitlist=is_waitlist,
            amount_paid_cents=body.get("amount_paid_cents", final_price),
            payment_method=body.get("payment_method"),
            payment_id=body.get("payment_id"),
        )
        db.add(reg)

        if not is_waitlist:
            e.spots_taken += 1
            if e.max_spots and e.spots_taken >= e.max_spots:
                e.status = "sold_out"

        db.commit()
        db.refresh(reg)

        return jsonify({
            "ok": True,
            "registration_id": reg.id,
            "status": reg.status,
            "is_waitlist": is_waitlist,
            "amount_cents": final_price,
            "spots_remaining": (e.max_spots - e.spots_taken) if e.max_spots else None,
        }), 201
    finally:
        db.close()


@events_bp.route("/<int:event_id>/registrations", methods=["GET"])
@login_required
def list_registrations(event_id: int):
    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404

        regs = db.query(models.EventRegistration).filter_by(
            event_id=event_id,
        ).order_by(models.EventRegistration.registered_at.asc()).all()

        return jsonify({
            "registrations": [
                {
                    "id": r.id, "lead_id": r.lead_id,
                    "name": r.name, "phone": r.phone, "email": r.email,
                    "status": r.status, "is_waitlist": r.is_waitlist,
                    "amount_paid_cents": r.amount_paid_cents,
                    "payment_method": r.payment_method,
                    "notes": r.notes,
                    "registered_at": r.registered_at.isoformat(),
                } for r in regs
            ],
            "spots_taken": e.spots_taken,
            "max_spots": e.max_spots,
        })
    finally:
        db.close()


@events_bp.route("/<int:event_id>/registrations/<int:reg_id>/confirm", methods=["POST"])
@login_required
def confirm_registration(event_id: int, reg_id: int):
    db = SessionLocal()
    try:
        reg = db.query(models.EventRegistration).filter_by(
            id=reg_id, event_id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not reg:
            return jsonify({"error": "not_found"}), 404
        reg.status = "confirmed"
        if reg.is_waitlist:
            reg.is_waitlist = False
            e = db.query(models.Event).filter_by(id=event_id).first()
            if e:
                e.spots_taken += 1
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@events_bp.route("/<int:event_id>/registrations/<int:reg_id>/cancel", methods=["POST"])
@login_required
def cancel_registration(event_id: int, reg_id: int):
    db = SessionLocal()
    try:
        reg = db.query(models.EventRegistration).filter_by(
            id=reg_id, event_id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not reg:
            return jsonify({"error": "not_found"}), 404
        was_confirmed = reg.status == "confirmed"
        reg.status = "cancelled"
        if was_confirmed:
            e = db.query(models.Event).filter_by(id=event_id).first()
            if e and e.spots_taken > 0:
                e.spots_taken -= 1
                if e.status == "sold_out":
                    e.status = "published"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@events_bp.route("/<int:event_id>/notify", methods=["POST"])
@login_required
@limiter.limit("10/hour")
def notify_registrants(event_id: int):
    """
    Envia mensagem WhatsApp para todos os inscritos confirmados.
    Body: {message}
    """
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message_required"}), 422

    db = SessionLocal()
    try:
        e = db.query(models.Event).filter_by(
            id=event_id, tenant_id=current_user.tenant_id,
        ).first()
        if not e:
            return jsonify({"error": "not_found"}), 404

        regs = db.query(models.EventRegistration).filter_by(
            event_id=event_id, status="confirmed",
        ).all()

        # Resolve phones from leads
        sent = 0
        for reg in regs:
            phone = reg.phone
            if not phone and reg.lead_id:
                lead = db.query(models.Lead).filter_by(id=reg.lead_id).first()
                if lead:
                    phone = lead.telefone
            if phone:
                try:
                    import horoscope
                    client = horoscope._get_whatsapp_client(current_user.tenant_id)
                    if client:
                        client.enviar_mensagem(phone, message, formato="texto")
                        sent += 1
                except Exception:
                    pass

        return jsonify({"ok": True, "sent": sent, "total_registrants": len(regs)})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _event_to_dict(e: models.Event) -> dict:
    now = datetime.now(timezone.utc)
    is_early_bird = False
    if e.early_bird_price_cents is not None and e.early_bird_deadline is not None:
        deadline = e.early_bird_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        is_early_bird = now < deadline
    return {
        "id": e.id, "title": e.title, "description": e.description,
        "event_type": e.event_type,
        "location_name": e.location_name,
        "location_address": e.location_address,
        "is_online": e.is_online, "online_url": e.online_url,
        "starts_at": e.starts_at.isoformat() if e.starts_at else None,
        "ends_at": e.ends_at.isoformat() if e.ends_at else None,
        "max_spots": e.max_spots, "spots_taken": e.spots_taken,
        "spots_remaining": (e.max_spots - e.spots_taken) if e.max_spots else None,
        "waitlist_enabled": e.waitlist_enabled,
        "price_cents": e.price_cents,
        "price_brl": e.price_cents / 100,
        "installments_max": e.installments_max,
        "is_early_bird": is_early_bird,
        "early_bird_price_cents": e.early_bird_price_cents,
        "early_bird_price_brl": e.early_bird_price_cents / 100 if e.early_bird_price_cents else None,
        "early_bird_deadline": e.early_bird_deadline.isoformat() if e.early_bird_deadline else None,
        "cover_image_url": e.cover_image_url,
        "status": e.status,
        "metadata": e.metadata_json,
        "created_at": e.created_at.isoformat(),
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
