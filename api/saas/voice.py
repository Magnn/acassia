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
                    "is_default": bool(c.is_default),
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


@voice_bp.route("/clones/<int:clone_id>/set-default", methods=["POST"])
@login_required
def set_default(clone_id: int):
    """
    Marca este clone como o default do tenant (Frente 4.16). Apenas 1 default
    por tenant — desmarca os outros automaticamente.
    """
    db = SessionLocal()
    try:
        clone = db.query(models.VoiceClone).filter_by(
            id=clone_id, tenant_id=current_user.tenant_id,
        ).first()
        if not clone or clone.deleted_at:
            return jsonify({"error": "not_found"}), 404
        if clone.status != "active":
            return jsonify({"error": "clone_not_active", "status": clone.status}), 422

        # Desmarca outros defaults do mesmo tenant
        db.query(models.VoiceClone).filter(
            models.VoiceClone.tenant_id == current_user.tenant_id,
            models.VoiceClone.id != clone.id,
            models.VoiceClone.is_default == True,  # noqa: E712
        ).update({"is_default": False}, synchronize_session=False)

        clone.is_default = True
        db.commit()

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="voice.clone.default_set",
                target_type="voice_clone",
                target_id=str(clone.id),
                payload={"name": clone.name},
            ))
            db.commit()
        except Exception:
            pass

        return jsonify({"ok": True, "id": clone.id, "is_default": True})
    finally:
        db.close()


@voice_bp.route("/clones/<int:clone_id>/unset-default", methods=["POST"])
@login_required
def unset_default(clone_id: int):
    """Desmarca o default — bot volta a nao usar voz clonada."""
    db = SessionLocal()
    try:
        clone = db.query(models.VoiceClone).filter_by(
            id=clone_id, tenant_id=current_user.tenant_id,
        ).first()
        if not clone or clone.deleted_at:
            return jsonify({"error": "not_found"}), 404
        clone.is_default = False
        db.commit()
        return jsonify({"ok": True, "is_default": False})
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

        stability = float(body.get("stability") or 0.5)
        similarity = float(body.get("similarity") or 0.75)

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
                stability=stability,
                similarity_boost=similarity,
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

@voice_bp.route("/presets/<provider_voice_id>/synthesize", methods=["POST"])
@login_required
@limiter.limit("30/minute")
def synthesize_preset(provider_voice_id: str):
    """
    Gera TTS para vozes pré-aprovadas (ElevenLabs defaults).
    """
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()

    if not text:
        return jsonify({"error": "text_required"}), 422
    if len(text) > 5000:
        return jsonify({"error": "text_too_long", "max": 5000}), 422

    stability = float(body.get("stability") or 0.5)
    similarity = float(body.get("similarity") or 0.75)

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
            voice_id=provider_voice_id,
            text=text,
            stability=stability,
            similarity_boost=similarity,
        )
    except vp.VoiceProviderError as exc:
        return jsonify({"error": "provider_error", "message": str(exc)}), 502

    # Salva localmente
    file_id = secrets.token_hex(8)
    filename = f"{current_user.tenant_id}_{file_id}.mp3"
    filepath = os.path.join(_AUDIO_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    db = SessionLocal()
    try:
        gen = models.AudioGeneration(
            tenant_id=current_user.tenant_id,
            voice_clone_id=None,  # Not a clone
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


@voice_bp.route("/send-to-lead", methods=["POST"])
@login_required
@limiter.limit("30/hour")
def send_audio_to_lead():
    """
    Sintetiza texto na voz clonada do tenant + envia como audio pro lead
    via WhatsApp em uma chamada (Frente 4.16).

    Body:
        {lead_id: int, text: str, voice_clone_id?: int (default = tenant default)}

    Fluxo:
        1. Resolve voice (explicito ou default do tenant)
        2. Quota check (gemini_tokens_month como proxy de chars)
        3. TTS via ElevenLabs
        4. Salva audio local + cria AudioGeneration
        5. Envia URL absoluta como audio msg via WhatsApp provider
        6. Salva no Mensagem como remetente=bot
    """
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    text = (body.get("text") or "").strip()
    voice_clone_id = body.get("voice_clone_id")

    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422
    if not text:
        return jsonify({"error": "text_required"}), 422
    if len(text) > 5000:
        return jsonify({"error": "text_too_long", "max": 5000}), 422

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=int(lead_id), tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        # Resolve voice
        if voice_clone_id:
            clone = db.query(models.VoiceClone).filter_by(
                id=int(voice_clone_id), tenant_id=current_user.tenant_id,
            ).first()
        else:
            clone = vp.get_default_voice_for_tenant(current_user.tenant_id)
            if clone is None:
                return jsonify({
                    "error": "no_default_voice",
                    "message": "Nenhuma voz clonada padrao. Defina em /voice ou passe voice_clone_id.",
                }), 422
        if not clone or clone.deleted_at:
            return jsonify({"error": "clone_not_found"}), 404
        if clone.status != "active":
            return jsonify({"error": "clone_not_active", "status": clone.status}), 422

        # Quota
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

        # TTS
        try:
            audio_bytes = vp.synthesize_elevenlabs(
                tenant_id=current_user.tenant_id,
                voice_id=clone.provider_voice_id,
                text=text,
            )
        except vp.VoiceProviderError as exc:
            return jsonify({"error": "provider_error", "message": str(exc)}), 502

        # Persist local
        file_id = secrets.token_hex(8)
        filename = f"{current_user.tenant_id}_{file_id}.mp3"
        filepath = os.path.join(_AUDIO_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        # AudioGeneration row
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

        # URL absoluta pra WhatsApp baixar — Meta precisa de URL publica HTTPS
        public_base = (os.getenv("PUBLIC_URL") or "").rstrip("/")
        if not public_base:
            return jsonify({
                "error": "public_url_not_configured",
                "message": "PUBLIC_URL env precisa estar definido para enviar audio pelo WhatsApp",
                "audio_url_local": gen.audio_url,
            }), 503
        absolute_url = f"{public_base}{gen.audio_url}"

        # Envia via provider (com simulação humanizada de gravação)
        try:
            from api.whatsapp_api import whatsapp_client
            try:
                whatsapp_client.simulate_presence(lead.telefone, presence="recording", delay_seconds=1.5)
            except Exception:
                pass
            ok = whatsapp_client.enviar_mensagem(
                lead.telefone, absolute_url, formato="audio",
            )
        except Exception as exc:
            logger.exception("[voice.send_to_lead] envio falhou")
            return jsonify({
                "ok": False,
                "error": "send_failed",
                "message": str(exc)[:200],
                "generation_id": gen.id,
            }), 502

        if not ok:
            return jsonify({
                "ok": False,
                "error": "send_returned_false",
                "generation_id": gen.id,
            }), 502

        # Marca msg no historico
        try:
            db.add(models.Mensagem(
                lead_id=lead.id,
                remetente="bot",
                texto=text[:2000],
                tipo="audio",
                media_url=absolute_url,
            ))
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="voice.audio.sent",
                target_type="lead",
                target_id=str(lead.id),
                payload={
                    "voice_clone_id": clone.id,
                    "chars_count": chars_count,
                    "generation_id": gen.id,
                },
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({
            "ok": True,
            "generation_id": gen.id,
            "voice_clone_id": clone.id,
            "audio_url": absolute_url,
            "chars_count": chars_count,
        })
    finally:
        db.close()


@voice_bp.route("/send-recorded-to-lead", methods=["POST"])
@login_required
@limiter.limit("60/hour")
def send_recorded_to_lead():
    """
    Recebe gravacao de audio inline (multipart 'audio' + form 'lead_id') e
    envia direto pro lead via WhatsApp (Frente 4.30 — voice-only mode).

    NAO faz TTS — apenas reupload do que o atendente gravou. O usuario
    fala diretamente, sem texto.
    """
    lead_id = request.form.get("lead_id")
    audio_file = request.files.get("audio")

    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422
    if not audio_file:
        return jsonify({"error": "audio_required"}), 422

    audio_bytes = audio_file.read()
    if len(audio_bytes) < 5_000:
        return jsonify({"error": "audio_too_short"}), 422
    if len(audio_bytes) > 25_000_000:
        return jsonify({"error": "audio_too_large"}), 422

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            id=int(lead_id), tenant_id=current_user.tenant_id,
        ).first()
        if not lead:
            return jsonify({"error": "lead_not_found"}), 404

        # Persist audio file localmente
        ext = (audio_file.filename or "").rsplit(".", 1)[-1].lower() or "webm"
        if ext not in ("mp3", "ogg", "m4a", "webm", "wav"):
            ext = "webm"
        file_id = secrets.token_hex(8)
        filename = f"{current_user.tenant_id}_rec_{file_id}.{ext}"
        filepath = os.path.join(_AUDIO_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        # URL absoluta — Meta requer HTTPS publica
        public_base = (os.getenv("PUBLIC_URL") or "").rstrip("/")
        if not public_base:
            return jsonify({
                "error": "public_url_not_configured",
                "audio_url_local": f"/saas/voice/audio/{file_id}",
            }), 503
        absolute_url = f"{public_base}/saas/voice/audio/{file_id}"

        # Envia via WhatsApp
        try:
            from api.whatsapp_api import whatsapp_client
            ok = whatsapp_client.enviar_mensagem(
                lead.telefone, absolute_url, formato="audio",
            )
        except Exception as exc:
            logger.exception("[voice.send_recorded] envio falhou")
            return jsonify({"error": "send_failed", "message": str(exc)[:200]}), 502
        if not ok:
            return jsonify({"error": "send_returned_false"}), 502

        # Persist Mensagem + audit
        try:
            db.add(models.Mensagem(
                lead_id=lead.id,
                remetente="bot",
                texto="[áudio gravado pelo atendente]",
                tipo="audio",
                media_url=absolute_url,
            ))
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="voice.recorded.sent",
                target_type="lead",
                target_id=str(lead.id),
                payload={
                    "file_id": file_id,
                    "size_bytes": len(audio_bytes),
                    "mime": audio_file.mimetype,
                },
            ))
            db.commit()
        except Exception:
            db.rollback()

        return jsonify({
            "ok": True,
            "audio_url": absolute_url,
            "size_bytes": len(audio_bytes),
        })
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
