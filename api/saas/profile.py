"""
api/saas/profile.py — Perfil Público do Profissional (Landing Page)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: landing page pública para terapeutas, oraculistas e coaches.
Acessível sem login em /p/<slug> — é a porta de entrada B2C.

Endpoints ADMIN (logado):
  GET    /saas/profile/                     — meu perfil
  POST   /saas/profile/                     — cria/atualiza perfil
  POST   /saas/profile/publish              — publica
  POST   /saas/profile/testimonials         — adiciona depoimento
  GET    /saas/profile/testimonials          — lista depoimentos
  DELETE /saas/profile/testimonials/<id>     — remove depoimento
  GET    /saas/profile/stats                — métricas

Endpoints PÚBLICOS (sem login):
  GET    /p/<slug>                          — página pública (JSON)
  GET    /p/<slug>/services                 — serviços públicos
  GET    /p/<slug>/availability             — horários disponíveis
  POST   /p/<slug>/book                     — solicitar agendamento
"""

from __future__ import annotations

import logging
import re
import secrets
from datetime import datetime, date, timedelta, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)
profile_bp = Blueprint("saas_profile", __name__)


# ═══════════════════════════════════════════════════════════════════════
# ADMIN — Gestão do perfil (requer login)
# ═══════════════════════════════════════════════════════════════════════

@profile_bp.route("/saas/profile/", methods=["GET"])
@login_required
def get_my_profile():
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        if not p:
            return jsonify({"exists": False})
        testimonials = db.query(models.ExpertTestimonial).filter_by(
            profile_id=p.id, is_approved=True,
        ).count()
        result = _profile_to_dict(p)
        result["testimonials_count"] = testimonials
        return jsonify(result)
    finally:
        db.close()


@profile_bp.route("/saas/profile/", methods=["POST"])
@login_required
def upsert_profile():
    """
    Cria ou atualiza perfil público.
    Body: {display_name, slug?, headline?, bio?, avatar_url?, cover_image_url?,
           specialties?, city?, state?, instagram?, whatsapp_display?,
           show_services?, show_testimonials?, show_calendar?,
           accept_online?, accept_in_person?, theme_color?,
           meta_title?, meta_description?}
    """
    body = request.get_json(silent=True) or {}
    display_name = (body.get("display_name") or "").strip()
    if not display_name or len(display_name) < 2:
        return jsonify({"error": "display_name_required"}), 422

    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()

        if not p:
            slug = body.get("slug") or _make_slug(display_name)
            # Verificar unicidade do slug
            existing_slug = db.query(models.ExpertProfile).filter_by(slug=slug).first()
            if existing_slug:
                slug = slug + "-" + secrets.token_hex(3)

            p = models.ExpertProfile(
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                slug=slug,
                display_name=display_name,
            )
            db.add(p)

        # Atualizar campos
        fields = [
            "display_name", "headline", "bio", "avatar_url", "cover_image_url",
            "specialties", "city", "state", "instagram", "whatsapp_display",
            "show_services", "show_testimonials", "show_calendar",
            "accept_online", "accept_in_person", "theme_color", "custom_css",
            "meta_title", "meta_description",
        ]
        for f in fields:
            if f in body:
                setattr(p, f, body[f])

        if "slug" in body and body["slug"]:
            new_slug = _make_slug(body["slug"])
            existing = db.query(models.ExpertProfile).filter(
                models.ExpertProfile.slug == new_slug,
                models.ExpertProfile.id != p.id,
            ).first()
            if existing:
                return jsonify({"error": "slug_taken"}), 409
            p.slug = new_slug

        db.commit()
        db.refresh(p)
        return jsonify({"ok": True, "slug": p.slug, "url": f"/p/{p.slug}"}), 201
    finally:
        db.close()


@profile_bp.route("/saas/profile/publish", methods=["POST"])
@login_required
def publish_profile():
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        if not p:
            return jsonify({"error": "profile_not_found"}), 404
        p.is_published = True
        p.published_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "url": f"/p/{p.slug}"})
    finally:
        db.close()


@profile_bp.route("/saas/profile/testimonials", methods=["POST"])
@login_required
def add_testimonial():
    """Body: {client_name, text, rating?, service_type?, client_avatar_url?}"""
    body = request.get_json(silent=True) or {}
    name = (body.get("client_name") or "").strip()
    text = (body.get("text") or "").strip()
    if not name or not text:
        return jsonify({"error": "client_name_and_text_required"}), 422

    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        if not p:
            return jsonify({"error": "profile_not_found"}), 404

        t = models.ExpertTestimonial(
            tenant_id=current_user.tenant_id,
            profile_id=p.id,
            client_name=name[:128],
            text=text[:1000],
            rating=min(5, max(1, int(body.get("rating", 5)))),
            service_type=body.get("service_type"),
            client_avatar_url=body.get("client_avatar_url"),
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return jsonify({"ok": True, "id": t.id}), 201
    finally:
        db.close()


@profile_bp.route("/saas/profile/testimonials", methods=["GET"])
@login_required
def list_testimonials():
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        if not p:
            return jsonify({"testimonials": []})

        items = db.query(models.ExpertTestimonial).filter_by(
            profile_id=p.id,
        ).order_by(models.ExpertTestimonial.created_at.desc()).all()

        return jsonify({
            "testimonials": [
                {
                    "id": t.id, "client_name": t.client_name, "text": t.text,
                    "rating": t.rating, "service_type": t.service_type,
                    "is_approved": t.is_approved,
                    "created_at": t.created_at.isoformat(),
                } for t in items
            ]
        })
    finally:
        db.close()


@profile_bp.route("/saas/profile/testimonials/<int:tid>", methods=["DELETE"])
@login_required
def delete_testimonial(tid: int):
    db = SessionLocal()
    try:
        t = db.query(models.ExpertTestimonial).filter_by(
            id=tid, tenant_id=current_user.tenant_id,
        ).first()
        if not t:
            return jsonify({"error": "not_found"}), 404
        db.delete(t)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@profile_bp.route("/saas/profile/stats", methods=["GET"])
@login_required
def profile_stats():
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            tenant_id=current_user.tenant_id,
        ).first()
        if not p:
            return jsonify({"error": "not_found"}), 404
        return jsonify({
            "total_views": p.total_views,
            "total_bookings": p.total_bookings,
            "is_published": p.is_published,
            "slug": p.slug,
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# PÚBLICO — Página do profissional (sem login!)
# ═══════════════════════════════════════════════════════════════════════

@profile_bp.route("/p/<slug>", methods=["GET"])
def public_profile(slug: str):
    """Página pública do profissional — sem login necessário."""
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            slug=slug, is_published=True,
        ).first()
        if not p:
            return jsonify({"error": "profile_not_found"}), 404

        # Incrementar views
        p.total_views += 1
        db.commit()

        result = _profile_to_dict(p)

        # Serviços
        if p.show_services:
            try:
                services = db.query(models.ExpertService).filter_by(
                    tenant_id=p.tenant_id, is_active=True,
                ).order_by(models.ExpertService.sort_order.asc()).all()
                result["services"] = [
                    {
                        "id": s.id, "title": s.title,
                        "description": s.short_description or s.description,
                        "price_cents": s.price_cents,
                        "price_brl": s.price_cents / 100 if s.price_cents else 0,
                        "duration_minutes": s.duration_minutes,
                        "modality": s.modality,
                        "category": s.category,
                    } for s in services
                ]
            except Exception:
                result["services"] = []

        # Depoimentos
        if p.show_testimonials:
            testimonials = db.query(models.ExpertTestimonial).filter_by(
                profile_id=p.id, is_approved=True,
            ).order_by(models.ExpertTestimonial.created_at.desc()).limit(10).all()
            result["testimonials"] = [
                {
                    "client_name": t.client_name, "text": t.text,
                    "rating": t.rating, "service_type": t.service_type,
                } for t in testimonials
            ]

        # Próximos slots livres
        if p.show_calendar:
            now = datetime.now(timezone.utc)
            slots = db.query(models.ExpertScheduleSlot).filter(
                models.ExpertScheduleSlot.tenant_id == p.tenant_id,
                models.ExpertScheduleSlot.is_booked == False,
                models.ExpertScheduleSlot.is_blocked == False,
                models.ExpertScheduleSlot.slot_time > now,
            ).order_by(models.ExpertScheduleSlot.slot_time.asc()).limit(20).all()
            result["available_slots"] = [
                {
                    "id": s.id,
                    "date": str(s.slot_date) if s.slot_date else None,
                    "time": s.slot_time.isoformat() if s.slot_time else None,
                    "duration": s.duration_minutes,
                } for s in slots
            ]

        return jsonify(result)
    finally:
        db.close()


@profile_bp.route("/p/<slug>/services", methods=["GET"])
def public_services(slug: str):
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            slug=slug, is_published=True,
        ).first()
        if not p:
            return jsonify({"error": "not_found"}), 404

        try:
            services = db.query(models.ExpertService).filter_by(
                tenant_id=p.tenant_id, is_active=True,
            ).order_by(models.ExpertService.sort_order.asc()).all()
        except Exception:
            services = []

        return jsonify({
            "services": [
                {
                    "id": s.id, "title": s.title,
                    "description": s.short_description or s.description,
                    "price_cents": s.price_cents,
                    "price_brl": s.price_cents / 100 if s.price_cents else 0,
                    "duration_minutes": s.duration_minutes,
                    "modality": s.modality,
                    "category": s.category,
                    "cover_image_url": s.cover_image_url,
                } for s in services
            ]
        })
    finally:
        db.close()


@profile_bp.route("/p/<slug>/availability", methods=["GET"])
def public_availability(slug: str):
    """Slots livres para o público — para o consumidor agendar."""
    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            slug=slug, is_published=True,
        ).first()
        if not p:
            return jsonify({"error": "not_found"}), 404

        now = datetime.now(timezone.utc)
        days_ahead = int(request.args.get("days", 30))

        slots = db.query(models.ExpertScheduleSlot).filter(
            models.ExpertScheduleSlot.tenant_id == p.tenant_id,
            models.ExpertScheduleSlot.is_booked == False,
            models.ExpertScheduleSlot.is_blocked == False,
            models.ExpertScheduleSlot.slot_time > now,
            models.ExpertScheduleSlot.slot_time < now + timedelta(days=days_ahead),
        ).order_by(models.ExpertScheduleSlot.slot_time.asc()).limit(50).all()

        # Agrupar por data
        by_date = {}
        for s in slots:
            d = str(s.slot_date) if s.slot_date else "unknown"
            if d not in by_date:
                by_date[d] = []
            by_date[d].append({
                "id": s.id,
                "time": s.slot_time.strftime("%H:%M") if s.slot_time else None,
                "duration": s.duration_minutes,
            })

        return jsonify({
            "expert_name": p.display_name,
            "availability": by_date,
            "total_slots": len(slots),
        })
    finally:
        db.close()


@profile_bp.route("/p/<slug>/book", methods=["POST"])
def public_book(slug: str):
    """
    Solicitação de agendamento PÚBLICO (sem login).
    Body: {slot_id, name, phone, email?, service_id?, notes?}
    """
    body = request.get_json(silent=True) or {}
    slot_id = body.get("slot_id")
    name = (body.get("name") or "").strip()
    phone = (body.get("phone") or "").strip()

    if not slot_id or not name or not phone:
        return jsonify({"error": "slot_id_name_phone_required"}), 422

    db = SessionLocal()
    try:
        p = db.query(models.ExpertProfile).filter_by(
            slug=slug, is_published=True,
        ).first()
        if not p:
            return jsonify({"error": "not_found"}), 404

        slot = db.query(models.ExpertScheduleSlot).filter_by(
            id=int(slot_id), tenant_id=p.tenant_id,
            is_booked=False, is_blocked=False,
        ).first()
        if not slot:
            return jsonify({"error": "slot_unavailable"}), 409

        # Criar ou encontrar lead
        lead = db.query(models.Lead).filter_by(
            tenant_id=p.tenant_id, telefone=phone,
        ).first()
        if not lead:
            lead = models.Lead(
                tenant_id=p.tenant_id,
                nome=name[:128],
                telefone=phone,
                email=body.get("email"),
                origem="perfil_publico",
            )
            db.add(lead)
            db.flush()

        # Criar appointment
        appt = models.Appointment(
            tenant_id=p.tenant_id,
            slot_id=slot.id,
            lead_id=lead.id,
            service_id=body.get("service_id"),
            client_name=name[:128],
            client_phone=phone,
            client_email=body.get("email"),
            scheduled_at=slot.slot_time,
            duration_minutes=slot.duration_minutes,
            modality="online" if p.accept_online else "in_person",
            status="pending",
            notes_before=body.get("notes"),
        )
        db.add(appt)

        slot.is_booked = True
        slot.lead_id = lead.id
        p.total_bookings += 1

        db.commit()
        db.refresh(appt)

        return jsonify({
            "ok": True,
            "appointment_id": appt.id,
            "scheduled_at": appt.scheduled_at.isoformat(),
            "expert_name": p.display_name,
            "message": f"Agendamento solicitado! {p.display_name} entrará em contato para confirmar.",
        }), 201
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _profile_to_dict(p: models.ExpertProfile) -> dict:
    return {
        "id": p.id, "slug": p.slug,
        "display_name": p.display_name,
        "headline": p.headline,
        "bio": p.bio,
        "avatar_url": p.avatar_url,
        "cover_image_url": p.cover_image_url,
        "specialties": p.specialties or [],
        "city": p.city, "state": p.state,
        "instagram": p.instagram,
        "whatsapp_display": p.whatsapp_display,
        "show_services": p.show_services,
        "show_testimonials": p.show_testimonials,
        "show_calendar": p.show_calendar,
        "accept_online": p.accept_online,
        "accept_in_person": p.accept_in_person,
        "theme_color": p.theme_color,
        "meta_title": p.meta_title,
        "meta_description": p.meta_description,
        "total_views": p.total_views,
        "is_published": p.is_published,
        "url": f"/p/{p.slug}",
        "exists": True,
    }


def _make_slug(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[àáâãäå]", "a", slug)
    slug = re.sub(r"[èéêë]", "e", slug)
    slug = re.sub(r"[ìíîï]", "i", slug)
    slug = re.sub(r"[òóôõö]", "o", slug)
    slug = re.sub(r"[ùúûü]", "u", slug)
    slug = re.sub(r"[ç]", "c", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:64]
