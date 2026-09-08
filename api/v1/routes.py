"""
api/v1/routes.py — Developer API v1 pública (Paridade ChatbotX / ManyChat)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Endpoints para desenvolvedores e integrações (Zapier, Make, n8n, CRM externo).
"""

from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, g
from db.database import SessionLocal
from db import models
from api.v1.auth import require_api_key

v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@v1_bp.route("/ping", methods=["GET"])
@require_api_key
def ping():
    return jsonify({"ok": True, "tenant_id": g.tenant_id, "timestamp": datetime.now(timezone.utc).isoformat()})


@v1_bp.route("/messages/send", methods=["POST"])
@require_api_key
def send_message():
    """
    Envia mensagem para um contato via WhatsApp, Webchat ou Telegram.
    Body: {"recipient": "5511999999999", "channel": "whatsapp", "text": "Olá!", "format": "texto", "media_url": "..."}
    """
    body = request.get_json(silent=True) or {}
    recipient = (body.get("recipient") or body.get("phone") or "").strip()
    text = (body.get("text") or body.get("message") or "").strip()
    channel = (body.get("channel") or "whatsapp").strip().lower()

    if not recipient or not text:
        return jsonify({"error": "recipient_and_text_required"}), 400

    from api.channels.registry import get_channel_adapter
    from api.channels.base import OutboundMessage

    adapter = get_channel_adapter(channel, g.tenant_id)
    out = OutboundMessage(
        recipient_id=recipient,
        text=text,
        format=body.get("format", "texto"),
        media_url=body.get("media_url"),
    )
    result = adapter.send_message(out)
    return jsonify({
        "ok": result.ok,
        "message_id": result.message_id,
        "error": result.error,
        "channel": channel,
    }), (200 if result.ok else 502)


@v1_bp.route("/contacts", methods=["POST"])
@require_api_key
def create_or_update_contact():
    """
    Cria ou atualiza contato (lead).
    Body: {"phone": "5511999999999", "name": "João", "tags": ["vip"], "custom_fields": {"empresa": "Acme"}}
    """
    body = request.get_json(silent=True) or {}
    phone = (body.get("phone") or body.get("telefone") or "").strip()
    if not phone:
        return jsonify({"error": "phone_required"}), 400

    name = (body.get("name") or body.get("nome") or "Novo Contato").strip()
    tags = body.get("tags") or []
    custom_fields = body.get("custom_fields") or {}

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            tenant_id=g.tenant_id, telefone=phone
        ).first()

        now = datetime.now(timezone.utc)
        if not lead:
            lead = models.Lead(
                tenant_id=g.tenant_id,
                telefone=phone,
                nome=name,
                tags=tags,
                custom_fields=custom_fields,
            )
            db.add(lead)
            created = True
        else:
            if name and name != "Novo Contato":
                lead.nome = name
            existing_tags = list(lead.tags or [])
            for t in tags:
                if t not in existing_tags:
                    existing_tags.append(t)
            lead.tags = existing_tags
            merged_fields = dict(lead.custom_fields or {})
            merged_fields.update(custom_fields)
            lead.custom_fields = merged_fields
            lead.atualizado_em = now
            created = False

        db.commit()
        db.refresh(lead)

        return jsonify({
            "ok": True,
            "created": created,
            "contact": {
                "id": lead.id,
                "phone": lead.telefone,
                "name": lead.nome,
                "tags": lead.tags or [],
                "custom_fields": lead.custom_fields or {},
            }
        }), (201 if created else 200)
    finally:
        db.close()


@v1_bp.route("/contacts/<phone_or_id>", methods=["GET"])
@require_api_key
def get_contact(phone_or_id: str):
    """Retorna detalhes do contato pelo ID ou número de telefone."""
    db = SessionLocal()
    try:
        query = db.query(models.Lead).filter_by(tenant_id=g.tenant_id)
        if phone_or_id.isdigit() and len(phone_or_id) <= 9:
            lead = query.filter_by(id=int(phone_or_id)).first()
        else:
            lead = query.filter_by(telefone=phone_or_id).first()

        if not lead:
            return jsonify({"error": "contact_not_found"}), 404

        return jsonify({
            "ok": True,
            "contact": {
                "id": lead.id,
                "phone": lead.telefone,
                "name": lead.nome,
                "tags": lead.tags or [],
                "custom_fields": lead.custom_fields or {},
                "score_band": lead.score_band,
                "bot_pausado": bool(lead.bot_pausado),
                "created_at": lead.criado_em.isoformat() if lead.criado_em else None,
            }
        })
    finally:
        db.close()


@v1_bp.route("/contacts/<phone_or_id>/tags", methods=["POST"])
@require_api_key
def add_contact_tags(phone_or_id: str):
    """Adiciona tags ao contato."""
    body = request.get_json(silent=True) or {}
    tags = body.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]

    db = SessionLocal()
    try:
        query = db.query(models.Lead).filter_by(tenant_id=g.tenant_id)
        if phone_or_id.isdigit() and len(phone_or_id) <= 9:
            lead = query.filter_by(id=int(phone_or_id)).first()
        else:
            lead = query.filter_by(telefone=phone_or_id).first()

        if not lead:
            return jsonify({"error": "contact_not_found"}), 404

        current_tags = list(lead.tags or [])
        for t in tags:
            clean = str(t).strip().lower()
            if clean and clean not in current_tags:
                current_tags.append(clean)
        lead.tags = current_tags
        db.commit()

        return jsonify({"ok": True, "tags": current_tags})
    finally:
        db.close()


@v1_bp.route("/sequences/enroll", methods=["POST"])
@require_api_key
def enroll_sequence():
    """
    Inscreve contato em uma sequência.
    Body: {"sequence_id": 1, "contact_id": 123} ou {"sequence_id": 1, "phone": "5511999999999"}
    """
    body = request.get_json(silent=True) or {}
    seq_id = body.get("sequence_id")
    contact_id = body.get("contact_id")
    phone = body.get("phone")

    if not seq_id or (not contact_id and not phone):
        return jsonify({"error": "sequence_id_and_contact_required"}), 400

    db = SessionLocal()
    try:
        if not contact_id and phone:
            lead = db.query(models.Lead).filter_by(tenant_id=g.tenant_id, telefone=str(phone).strip()).first()
            if not lead:
                return jsonify({"error": "contact_not_found"}), 404
            contact_id = lead.id

        from api.saas.sequences import _agora_utc, _calculate_next_run_at

        seq = db.query(models.Sequence).filter_by(id=int(seq_id), tenant_id=g.tenant_id).first()
        if not seq:
            return jsonify({"error": "sequence_not_found"}), 404

        first_step = db.query(models.SequenceStep).filter_by(sequence_id=seq.id, order=0, is_active=True).first()
        now = _agora_utc()
        next_run = _calculate_next_run_at(first_step, now) if first_step else now

        existing = db.query(models.ContactOnSequence).filter_by(sequence_id=seq.id, lead_id=contact_id).first()
        if existing:
            existing.status = "active"
            existing.current_step = 0
            existing.next_run_at = next_run
        else:
            db.add(models.ContactOnSequence(
                tenant_id=g.tenant_id,
                sequence_id=seq.id,
                lead_id=contact_id,
                current_step=0,
                status="active",
                next_run_at=next_run,
                enrolled_at=now,
            ))
        db.commit()
        return jsonify({"ok": True, "enrolled": True, "sequence_id": seq.id, "contact_id": contact_id})
    finally:
        db.close()
