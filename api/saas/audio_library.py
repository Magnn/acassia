"""
Audio library categorizada (Frente 4.17).

Endpoints:
    GET    /saas/audio-library                — lista com filtros
    POST   /saas/audio-library                — upload audio (multipart)
    PATCH  /saas/audio-library/<id>           — atualiza title/category/tags
    DELETE /saas/audio-library/<id>           — soft delete (+ purge file)
    POST   /saas/audio-library/<id>/send      — envia pro lead
    GET    /saas/audio-library/categories     — categorias com contagem
    POST   /saas/audio-library/suggest        — sugestao IA pra contexto

Storage local em ../media/voice (mesmo dir do voice TTS) — V2 S3.
"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter


logger = logging.getLogger(__name__)
audio_lib_bp = Blueprint("saas_audio_library", __name__, url_prefix="/saas/audio-library")


_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "media", "voice")
os.makedirs(_AUDIO_DIR, exist_ok=True)


VALID_CATEGORIES = {
    "saudacao", "protecao", "prosperidade", "amor", "fechamento",
    "carreira", "familia", "saude", "outro",
}
ALLOWED_EXT = {"mp3", "ogg", "m4a", "webm", "wav"}
MAX_BYTES = 25_000_000  # 25 MB


def _serialize(item: models.AudioLibraryItem) -> dict:
    return {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "tags": item.tags or [],
        "audio_url": item.audio_url,
        "duration_s": item.duration_s,
        "uploaded_by": item.uploaded_by,
        "usage_count": item.usage_count,
        "created_at": item.created_at.isoformat(),
    }


@audio_lib_bp.route("", methods=["GET"])
@login_required
def list_items():
    category = (request.args.get("category") or "").strip().lower() or None
    search = (request.args.get("search") or "").strip().lower()

    db = SessionLocal()
    try:
        q = db.query(models.AudioLibraryItem).filter_by(
            tenant_id=current_user.tenant_id,
            deleted_at=None,
        )
        if category:
            q = q.filter_by(category=category)
        if search:
            like = f"%{search}%"
            q = q.filter(models.AudioLibraryItem.title.ilike(like))
        items = q.order_by(
            models.AudioLibraryItem.usage_count.desc(),
            models.AudioLibraryItem.created_at.desc(),
        ).all()
        return jsonify({
            "items": [_serialize(i) for i in items],
            "total": len(items),
        })
    finally:
        db.close()


@audio_lib_bp.route("/categories", methods=["GET"])
@login_required
def categories_count():
    from sqlalchemy import func
    db = SessionLocal()
    try:
        rows = db.query(
            models.AudioLibraryItem.category,
            func.count(models.AudioLibraryItem.id),
        ).filter_by(
            tenant_id=current_user.tenant_id,
            deleted_at=None,
        ).group_by(models.AudioLibraryItem.category).all()
        return jsonify({
            "categories": [
                {"category": c or "outro", "count": int(n)}
                for c, n in rows
            ],
        })
    finally:
        db.close()


@audio_lib_bp.route("", methods=["POST"])
@login_required
@limiter.limit("60/hour")
def upload_item():
    """Multipart com audio + form fields title/category/tags."""
    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "outro").strip().lower()
    tags_raw = (request.form.get("tags") or "").strip()
    audio_file = request.files.get("audio")

    if not title or len(title) < 3:
        return jsonify({"error": "title_too_short"}), 422
    if category not in VALID_CATEGORIES:
        return jsonify({
            "error": "category_invalid",
            "valid": sorted(VALID_CATEGORIES),
        }), 422
    if not audio_file:
        return jsonify({"error": "audio_required"}), 422

    ext = (audio_file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        return jsonify({
            "error": "ext_not_allowed",
            "allowed": sorted(ALLOWED_EXT),
        }), 422

    audio_bytes = audio_file.read()
    if len(audio_bytes) < 5_000:
        return jsonify({"error": "audio_too_short"}), 422
    if len(audio_bytes) > MAX_BYTES:
        return jsonify({"error": "audio_too_large", "max_bytes": MAX_BYTES}), 422

    # Sanitiza tags
    tags = []
    for t in tags_raw.split(","):
        t = t.strip().lower()[:30]
        if t:
            tags.append(t)
    tags = tags[:10]

    # Persist file
    file_id = secrets.token_hex(8)
    filename = f"{current_user.tenant_id}_lib_{file_id}.{ext}"
    filepath = os.path.join(_AUDIO_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    db = SessionLocal()
    try:
        item = models.AudioLibraryItem(
            tenant_id=current_user.tenant_id,
            title=title[:200],
            category=category,
            tags=tags,
            audio_url=f"/saas/voice/audio/{file_id}",
            file_path=filepath,
            duration_s=None,  # V2: extract via ffprobe
            uploaded_by=current_user.id,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify({"ok": True, "item": _serialize(item)}), 201
    finally:
        db.close()


@audio_lib_bp.route("/<int:item_id>", methods=["PATCH"])
@login_required
def update_item(item_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        item = db.query(models.AudioLibraryItem).filter_by(
            id=item_id, tenant_id=current_user.tenant_id, deleted_at=None,
        ).first()
        if not item:
            return jsonify({"error": "not_found"}), 404

        if "title" in body:
            t = (body["title"] or "").strip()
            if len(t) >= 3:
                item.title = t[:200]
        if "category" in body:
            c = (body["category"] or "").strip().lower()
            if c in VALID_CATEGORIES:
                item.category = c
        if "tags" in body:
            tags_in = body["tags"]
            if isinstance(tags_in, list):
                clean = []
                for t in tags_in:
                    if isinstance(t, str):
                        t2 = t.strip().lower()[:30]
                        if t2:
                            clean.append(t2)
                item.tags = clean[:10]

        db.commit()
        return jsonify({"ok": True, "item": _serialize(item)})
    finally:
        db.close()


@audio_lib_bp.route("/<int:item_id>", methods=["DELETE"])
@login_required
def delete_item(item_id: int):
    """Soft delete + tenta remover arquivo local (best-effort)."""
    db = SessionLocal()
    try:
        item = db.query(models.AudioLibraryItem).filter_by(
            id=item_id, tenant_id=current_user.tenant_id, deleted_at=None,
        ).first()
        if not item:
            return jsonify({"error": "not_found"}), 404
        item.deleted_at = datetime.now(timezone.utc)
        db.commit()

        # Tenta remover arquivo local (nao critico)
        if item.file_path:
            try:
                if os.path.exists(item.file_path):
                    os.remove(item.file_path)
            except Exception as exc:
                logger.warning("[audio_library.delete] remove file falhou: %s", exc)

        return jsonify({"ok": True})
    finally:
        db.close()


@audio_lib_bp.route("/<int:item_id>/send", methods=["POST"])
@login_required
@limiter.limit("120/hour")
def send_to_lead(item_id: int):
    """Envia audio da biblioteca pro lead via WhatsApp."""
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422

    db = SessionLocal()
    try:
        item = db.query(models.AudioLibraryItem).filter_by(
            id=item_id, tenant_id=current_user.tenant_id, deleted_at=None,
        ).first()
        if not item:
            return jsonify({"error": "not_found"}), 404

        lead = db.query(models.Lead).filter_by(
            id=int(lead_id), tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        # URL absoluta — Meta exige HTTPS publica
        public_base = (os.getenv("PUBLIC_URL") or "").rstrip("/")
        if not public_base:
            return jsonify({
                "error": "public_url_not_configured",
                "audio_url_local": item.audio_url,
            }), 503
        absolute_url = f"{public_base}{item.audio_url}"

        try:
            from api.whatsapp_api import whatsapp_client
            ok = whatsapp_client.enviar_mensagem(
                lead.telefone, absolute_url, formato="audio",
            )
        except Exception as exc:
            logger.exception("[audio_library.send] envio falhou")
            return jsonify({"error": "send_failed", "message": str(exc)[:200]}), 502

        if not ok:
            return jsonify({"error": "send_returned_false"}), 502

        # Increment usage + persist no historico
        item.usage_count = (item.usage_count or 0) + 1
        try:
            db.add(models.Mensagem(
                lead_id=lead.id,
                remetente="bot",
                texto=item.title,
                tipo="audio",
                media_url=absolute_url,
            ))
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="audio_library.sent",
                target_type="audio_library_item",
                target_id=str(item.id),
                payload={"lead_id": lead.id, "title": item.title},
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({
            "ok": True,
            "audio_url": absolute_url,
            "title": item.title,
            "usage_count": item.usage_count,
        })
    finally:
        db.close()


@audio_lib_bp.route("/suggest", methods=["POST"])
@login_required
def suggest_audio():
    """
    Sugere ate 3 audios da biblioteca relevantes pro contexto da conversa.

    Heuristica simples (V1 — sem Gemini):
        - usa spiritual_category do lead se existe
        - mapa: amor->amor, dinheiro->prosperidade, espiritual->protecao,
                familia->familia, decisao->protecao, saude->saude
        - fallback: top 3 mais usados
    """
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422

    cat_map = {
        "amor": "amor",
        "dinheiro": "prosperidade",
        "espiritual": "protecao",
        "familia": "familia",
        "decisao": "protecao",
        "saude": "saude",
        "carreira": "carreira",
        "luto": "protecao",
    }

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=int(lead_id), tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        target_cat = cat_map.get((lead.spiritual_category or "").lower())
        items: list[models.AudioLibraryItem] = []

        if target_cat:
            items = db.query(models.AudioLibraryItem).filter_by(
                tenant_id=current_user.tenant_id,
                category=target_cat,
                deleted_at=None,
            ).order_by(
                models.AudioLibraryItem.usage_count.desc(),
            ).limit(3).all()

        if len(items) < 3:
            extras = db.query(models.AudioLibraryItem).filter(
                models.AudioLibraryItem.tenant_id == current_user.tenant_id,
                models.AudioLibraryItem.deleted_at.is_(None),
            ).order_by(
                models.AudioLibraryItem.usage_count.desc(),
            ).limit(3 - len(items)).all()
            seen = {i.id for i in items}
            for e in extras:
                if e.id not in seen:
                    items.append(e)

        return jsonify({
            "matched_category": target_cat,
            "lead_spiritual_category": lead.spiritual_category,
            "suggestions": [_serialize(i) for i in items[:3]],
        })
    finally:
        db.close()
