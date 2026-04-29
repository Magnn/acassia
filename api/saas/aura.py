"""
Aura imagery endpoints (Frente 4.18).

GET    /saas/aura/status                       — provider configurado?
GET    /saas/aura/leads/<lead_id>              — ultima aura
POST   /saas/aura/leads/<lead_id>/generate     — gera aura semanal
POST   /saas/aura/leads/<lead_id>/send         — envia imagem WhatsApp
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal

import aura_engine


logger = logging.getLogger(__name__)
aura_bp = Blueprint("saas_aura", __name__, url_prefix="/saas/aura")


def _serialize_aura(row: models.LeadAuraImage | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "lead_id": row.lead_id,
        "signo": row.signo,
        "week_id": row.week_id,
        "image_url": row.image_url,
        "prompt": row.prompt,
        "provider": row.provider,
        "sent_to_lead": row.sent_to_lead,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "created_at": row.created_at.isoformat(),
    }


@aura_bp.route("/status", methods=["GET"])
@login_required
def status():
    return jsonify({
        "available": aura_engine.is_available(),
        "provider": aura_engine._provider_active(),
        "hint": "Configure REPLICATE_API_TOKEN ou TOGETHER_API_KEY no .env",
    })


@aura_bp.route("/leads/<int:lead_id>", methods=["GET"])
@login_required
def get_latest(lead_id: int):
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        row = db.query(models.LeadAuraImage).filter_by(
            lead_id=lead_id,
        ).order_by(models.LeadAuraImage.created_at.desc()).first()
        return jsonify({
            "lead_id": lead_id,
            "signo": lead.signo,
            "current_week": aura_engine.week_id_for(),
            "aura": _serialize_aura(row),
        })
    finally:
        db.close()


@aura_bp.route("/leads/<int:lead_id>/generate", methods=["POST"])
@login_required
def generate(lead_id: int):
    """Gera aura desta semana. Idempotente por (lead, week_id) salvo force=true."""
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force"))
    mood = (body.get("mood") or "").strip() or None

    if not aura_engine.is_available():
        return jsonify({
            "error": "provider_not_configured",
            "message": "Configure REPLICATE_API_TOKEN ou TOGETHER_API_KEY",
        }), 503

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404
        if not lead.signo:
            return jsonify({
                "error": "lead_missing_sign",
                "message": "Calcule o signo do lead antes de gerar a aura",
            }), 422

        week_id = aura_engine.week_id_for()
        existing = db.query(models.LeadAuraImage).filter_by(
            lead_id=lead_id, week_id=week_id,
        ).first()
        if existing and not force:
            return jsonify({"ok": True, "cached": True, "aura": _serialize_aura(existing)})

        try:
            result = aura_engine.generate_aura_image(lead.signo, mood=mood)
        except aura_engine.AuraProviderError as exc:
            return jsonify({"error": "provider_error", "message": str(exc)}), 502
        except Exception as exc:
            logger.exception("[aura.generate] falha lead=%s: %s", lead_id, exc)
            return jsonify({"error": "unexpected", "message": str(exc)[:200]}), 500

        if existing:
            existing.image_url = result["url"]
            existing.prompt = result["prompt"]
            existing.provider = result["provider"]
            existing.sent_to_lead = False
            existing.sent_at = None
            existing.created_at = datetime.now(timezone.utc)
            row = existing
        else:
            row = models.LeadAuraImage(
                lead_id=lead_id,
                tenant_id=current_user.tenant_id,
                signo=lead.signo,
                week_id=week_id,
                image_url=result["url"],
                prompt=result["prompt"],
                provider=result["provider"],
            )
            db.add(row)

        db.commit()
        db.refresh(row)

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="aura.generated",
                target_type="lead",
                target_id=str(lead_id),
                payload={"signo": lead.signo, "week_id": week_id, "provider": result["provider"]},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({"ok": True, "cached": False, "aura": _serialize_aura(row)})
    finally:
        db.close()


@aura_bp.route("/leads/<int:lead_id>/send", methods=["POST"])
@login_required
def send_to_lead(lead_id: int):
    body = request.get_json(silent=True) or {}
    aura_id = body.get("aura_id")

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=lead_id, tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        if aura_id:
            row = db.query(models.LeadAuraImage).filter_by(
                id=int(aura_id), lead_id=lead_id, tenant_id=current_user.tenant_id,
            ).first()
        else:
            row = db.query(models.LeadAuraImage).filter_by(
                lead_id=lead_id, tenant_id=current_user.tenant_id,
            ).order_by(models.LeadAuraImage.created_at.desc()).first()
        if not row:
            return jsonify({"error": "aura_not_found"}), 404

        try:
            import horoscope
            client = horoscope._get_whatsapp_client(current_user.tenant_id)
            if client is None:
                return jsonify({"error": "whatsapp_unavailable"}), 502
            ok = client.enviar_mensagem(lead.telefone, row.image_url, formato="imagem")
            if not ok:
                return jsonify({"error": "send_returned_false"}), 502
        except Exception as exc:
            logger.exception("[aura.send] falha: %s", exc)
            return jsonify({"error": "send_failed", "message": str(exc)[:200]}), 502

        row.sent_to_lead = True
        row.sent_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True, "aura": _serialize_aura(row)})
    finally:
        db.close()
