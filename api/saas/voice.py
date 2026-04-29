"""
Voice cloning + TTS endpoints (Frente 4.14-4.16).

Endpoints:
    GET  /saas/voice/clones                  — lista vozes do tenant
    POST /saas/voice/clones                  — enroll (multipart audio)
    DELETE /saas/voice/clones/<id>           — soft-delete (+ remoto)
    POST /saas/voice/clones/<id>/synthesize  — gera TTS (retorna URL)
    POST /saas/voice/clones/<id>/test        — gera amostra de teste
    GET  /saas/voice/audio/<id>              — serve audio gerado (mp3)
    GET  /saas/voice/configured              — Eleven Labs configurado?
"""

from __future__ import annotations

import io
import logging
import os
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file, abort
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter
import voice_provider as vp


logger = logging.getLogger(__name__)
voice_bp = Blueprint("saas_voice", __name__, url_prefix="/saas/voice")


# Storage local pra audios gerados — V2 usar S3/Cloudinary (Frente 7.24)
_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "media", "voice")
os.makedirs(_AUDIO_DIR, exist_ok=True)


@voice_bp.route("/configured", methods=["GET"])
@login_required
def is_configured():
    return jsonify({"configured": vp.is_configured(current_user.tenant_id)})


@voice_bp.route("/clones", methods=["GET"])
@login_required
def list_clones():
    db = SessionLocal()
    try:
        clones = db.query(models.VoiceClone).filter(
            models.VoiceClone.tenant_id == current_user.tenant_id,
            models.VoiceClone.deleted_at.is_(None),
        ).order_by(models.VoiceClone.created_at.desc()).all()
        return jsonify({
            "clones": [
                {
                    "id": c.id,
                    "name": c.name,
                    "provider": c.provider,
                    "provider_voice_id": c.provider_voice_id,
                    "status": c.status,
                    "sample_audio_url": c.sample_audio_url,
                    "consented_at": c.consented_at.isoformat() if c.consented_at else None,
                    "created_at": c.created_at.isoformat(),
                } for c in clones
            ]
        })
    finally:
        db.close()


@voice_bp.route("/clones", methods=["POST"])
@login_required
@limiter.limit("5/hour")
def enroll_clone():
    """
    Enroll voice. Multipart com audio file (key='audio').
    Form fields: name, consent (must be 'true').
    Quota check: feature 'voice_cloning' (Pro+ only).
    """
    # Feature check
    try:
        import plans
        if not plans.has_feature(plans.effective_plan(current_user.tenant_id)[0], "voice_cloning"):
            return jsonify({
                "error": "feature_not_in_plan",
                "message": "Voice cloning está disponível no plano Pro ou superior",
            }), 402
    except Exception:
        pass

    consent = (request.form.get("consent") or "").strip().lower()
    if consent != "true":
        return jsonify({"error": "consent_required"}), 422

    name = (request.form.get("name") or "Minha voz").strip()[:100]
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "audio_required"}), 422

    audio_bytes = audio_file.read()
    if len(audio_bytes) < 50_000:  # ~3s de áudio
        return jsonify({"error": "audio_too_short", "message": "Mínimo 30s de áudio recomendado"}), 422
    if len(audio_bytes) > 25_000_000:  # 25 MB
        return jsonify({"error": "audio_too_large"}), 422

    if not vp.is_configured(current_user.tenant_id):
        return jsonify({"error": "provider_not_configured"}), 503

    try:
        result = vp.enroll_voice_elevenlabs(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            audio_bytes=audio_bytes,
            audio_filename=audio_file.filename or "voice.wav",
            name=name,
            description=f"Clone {name} tenant {current_user.tenant_id}",
        )
    except vp.VoiceProviderError as exc:
        logger.warning("[voice.enroll] tenant=%s falhou: %s", current_user.tenant_id, exc)
        return jsonify({"error": "provider_error", "message": str(exc)}), 502
    except Exception as exc:
        logger.exception("[voice.enroll] erro inesperado")
        return jsonify({"error": "internal", "message": str(exc)[:200]}), 500

    db = SessionLocal()
    try:
        clone = models.VoiceClone(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            name=name,
            provider=result.provider,
            provider_voice_id=result.provider_voice_id,
            status="active",
            consented_at=datetime.now(timezone.utc),
        )
        db.add(clone)
        db.commit()
        db.refresh(clone)

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="voice.clone.enrolled",
                target_type="voice_clone",
                target_id=str(clone.id),
                payload={"name": name, "provider": result.provider},
            ))
            db.commit()
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "id": clone.id,
            "name": clone.name,
            "provider_voice_id": clone.provider_voice_id,
            "status": clone.status,
        }), 201
    finally:
        db.close()


@voice_bp.route("/clones/<int:clone_id>", methods=["DELETE"])
@login_required
def delete_clone(clone_id: int):
    """Soft-delete + remove no provider."""
    db = SessionLocal()
    try:
        clone = db.query(models.VoiceClone).filter_by(
            id=clone_id, tenant_id=current_user.tenant_id,
        ).first()
        if not clone or clone.deleted_at:
            return jsonify({"error": "not_found"}), 404

        # Tenta remover no provider (não-fatal)
        try:
            vp.delete_voice_elevenlabs(
                tenant_id=current_user.tenant_id,
                voice_id=clone.provider_voice_id,
            )
        except Exception:
            pass

        clone.deleted_at = datetime.now(timezone.utc)
        db.commit()

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="voice.clone.deleted",
                target_type="voice_clone",
                target_id=str(clone_id),
            ))
            db.commit()
        except Exception:
            pass

        return jsonify({"ok": True})
    finally:
        db.close()


@voice_bp.route("/clones/<int:clone_id>/synthesize", methods=["POST"])
@login_required
@limiter.limit("30/minute")
def synthesize(clone_id: int):
    """
    Gera TTS. Body: {text, lead_id?}.
    Retorna {audio_url, duration_s, generation_id}.
    """
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()

    if not text:
        return jsonify({"error": "text_required"}), 422
    if len(text) > 5000:
        return jsonify({"error": "text_too_long", "max": 5000}), 422

    db = SessionLocal()
    try:
        clone = db.query(models.VoiceClone).filter_by(
            id=clone_id, tenant_id=current_user.tenant_id,
        ).first()
        if not clone or clone.deleted_at:
            return jsonify({"error": "clone_not_found"}), 404

        # Quota Gemini-style: cap chars por mês baseado em plano
        # Aqui usamos quota-spec custom — por enquanto, simples cap por tenant
        chars_count = len(text)
        try:
            import quota
            allowed, _, _ = quota.consume_quota(
                current_user.tenant_id, "gemini_tokens_month", chars_count,
            )
            if not allowed:
                return jsonify({"error": "quota_exceeded", "kind": "voice_chars"}), 402
        except Exception:
            pass

        try:
            audio_bytes = vp.synthesize_elevenlabs(
                tenant_id=current_user.tenant_id,
                voice_id=clone.provider_voice_id,
                text=text,
            )
        except vp.VoiceProviderError as exc:
            return jsonify({"error": "provider_error", "message": str(exc)}), 502

        # Salva localmente
        file_id = secrets.token_hex(8)
        filename = f"{current_user.tenant_id}_{file_id}.mp3"
        filepath = os.path.join(_AUDIO_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        gen = models.AudioGeneration(
            tenant_id=current_user.tenant_id,
            voice_clone_id=clone.id,
            text=text[:2000],
            chars_count=chars_count,
            audio_url=f"/saas/voice/audio/{file_id}",
            provider="elevenlabs",
            status="done",
        )
        db.add(gen)
        db.commit()
        db.refresh(gen)

        return jsonify({
            "ok": True,
            "generation_id": gen.id,
            "audio_url": gen.audio_url,
            "chars_count": chars_count,
            "size_bytes": len(audio_bytes),
        })
    finally:
        db.close()


@voice_bp.route("/clones/<int:clone_id>/test", methods=["POST"])
@login_required
@limiter.limit("10/hour")
def test_voice(clone_id: int):
    """Gera amostra rápida de teste."""
    sample_text = "Olá. Sou sua tarot reader. Vou te guiar nessa jornada espiritual hoje."
    return synthesize.__wrapped__(clone_id) if False else _generate_sample(clone_id, sample_text)


def _generate_sample(clone_id: int, sample_text: str):
    db = SessionLocal()
    try:
        clone = db.query(models.VoiceClone).filter_by(
            id=clone_id, tenant_id=current_user.tenant_id,
        ).first()
        if not clone:
            return jsonify({"error": "clone_not_found"}), 404
        try:
            audio_bytes = vp.synthesize_elevenlabs(
                tenant_id=current_user.tenant_id,
                voice_id=clone.provider_voice_id,
                text=sample_text,
            )
        except vp.VoiceProviderError as exc:
            return jsonify({"error": "provider_error", "message": str(exc)}), 502

        file_id = secrets.token_hex(8)
        filename = f"{current_user.tenant_id}_sample_{file_id}.mp3"
        filepath = os.path.join(_AUDIO_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        clone.sample_audio_url = f"/saas/voice/audio/{file_id}"
        db.commit()
        return jsonify({"ok": True, "sample_audio_url": clone.sample_audio_url})
    finally:
        db.close()


@voice_bp.route("/audio/<file_id>", methods=["GET"])
@login_required
def serve_audio(file_id: str):
    """Serve audio gerado. Validação multi-tenant via prefixo do filename."""
    # Sanitize file_id
    if not file_id.replace("_", "").isalnum():
        abort(400)

    # Procura arquivo que comece com tenant_id
    expected_prefix = f"{current_user.tenant_id}_"
    for fname in os.listdir(_AUDIO_DIR):
        if fname.startswith(expected_prefix) and file_id in fname:
            return send_file(
                os.path.join(_AUDIO_DIR, fname),
                mimetype="audio/mpeg",
                as_attachment=False,
            )
    abort(404)
