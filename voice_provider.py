"""
Voice cloning + TTS provider abstraction (Frente 4.14-4.16).

V1: ElevenLabs.
V2: Coqui TTS (self-hosted), OpenAI TTS.

API:
    enroll_voice(tenant_id, user_id, audio_bytes, name) → VoiceCloneResult
    synthesize_text(voice_clone_id, text, db_session?) → audio_bytes
    list_voices(tenant_id) → lista
    delete_voice(voice_clone_id) → cleanup local + provider

Configuração: ELEVENLABS_API_KEY env var (ou TenantFlowSecret pra per-tenant).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import requests


logger = logging.getLogger(__name__)


class VoiceProviderError(Exception):
    pass


class VoiceCloneResult:
    def __init__(
        self,
        provider: str,
        provider_voice_id: str,
        sample_audio_url: Optional[str] = None,
    ):
        self.provider = provider
        self.provider_voice_id = provider_voice_id
        self.sample_audio_url = sample_audio_url


_EL_BASE = "https://api.elevenlabs.io/v1"


def _eleven_key(tenant_id: Optional[str] = None) -> Optional[str]:
    """Resolve API key — TenantFlowSecret prioridade, env fallback."""
    if tenant_id:
        try:
            from db.database import SessionLocal
            from db import models
            db = SessionLocal()
            try:
                row = db.query(models.TenantFlowSecret).filter_by(
                    tenant_id=tenant_id, key="elevenlabs.api_key",
                ).first()
                # Coluna correta e value_cipher (nao value).
                if row and row.value_cipher:
                    return row.value_cipher
            finally:
                db.close()
        except Exception:
            pass
    return os.getenv("ELEVENLABS_API_KEY")


def is_configured(tenant_id: Optional[str] = None) -> bool:
    return bool(_eleven_key(tenant_id))


# ─── Enrollment (clone voice) ─────────────────────────────────────────


def enroll_voice_elevenlabs(
    *,
    tenant_id: str,
    user_id: int,
    audio_bytes: bytes,
    audio_filename: str,
    name: str,
    description: str = "",
) -> VoiceCloneResult:
    """
    Cria voice clone no ElevenLabs via Voice Add API.
    audio_bytes deve ser ≥30s de fala em pt-BR, mono, 22kHz+.
    """
    api_key = _eleven_key(tenant_id)
    if not api_key:
        raise VoiceProviderError("ELEVENLABS_API_KEY não configurado")

    headers = {"xi-api-key": api_key}
    files = {
        "files": (audio_filename or "voice.wav", audio_bytes, "audio/wav"),
    }
    data = {
        "name": name[:100],
        "description": description[:200],
        "labels": '{"language": "pt-br", "tenant": "%s"}' % tenant_id,
    }

    try:
        resp = requests.post(
            f"{_EL_BASE}/voices/add",
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )
    except requests.RequestException as exc:
        raise VoiceProviderError(f"Falha de rede com ElevenLabs: {exc}")

    if resp.status_code >= 400:
        logger.warning("[voice.enroll] erro %s: %s", resp.status_code, resp.text[:500])
        raise VoiceProviderError(f"ElevenLabs retornou {resp.status_code}: {resp.text[:200]}")

    payload = resp.json() or {}
    voice_id = payload.get("voice_id")
    if not voice_id:
        raise VoiceProviderError("Sem voice_id na resposta")

    return VoiceCloneResult(
        provider="elevenlabs",
        provider_voice_id=voice_id,
    )


def synthesize_elevenlabs(
    *,
    tenant_id: str,
    voice_id: str,
    text: str,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> bytes:
    """
    TTS via ElevenLabs. Retorna bytes audio (MP3 default).
    """
    api_key = _eleven_key(tenant_id)
    if not api_key:
        raise VoiceProviderError("API key não configurada")

    if not text or not text.strip():
        raise VoiceProviderError("texto vazio")
    if len(text) > 5000:
        raise VoiceProviderError("texto muito longo (>5000 chars)")

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }
    try:
        resp = requests.post(
            f"{_EL_BASE}/text-to-speech/{voice_id}",
            json=payload,
            headers=headers,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise VoiceProviderError(f"Falha rede: {exc}")
    if resp.status_code != 200:
        raise VoiceProviderError(f"ElevenLabs {resp.status_code}: {resp.text[:200]}")
    return resp.content


def get_default_voice_for_tenant(tenant_id: str):
    """
    Retorna o VoiceClone marcado como default do tenant (ou None).

    Usado pelo motor pra decidir se outbound de audio deve usar voz
    clonada ou TTS generica (Frente 4.16).
    """
    if not tenant_id:
        return None
    try:
        from db.database import SessionLocal
        from db import models
        db = SessionLocal()
        try:
            row = db.query(models.VoiceClone).filter_by(
                tenant_id=tenant_id,
                is_default=True,
                deleted_at=None,
                status="active",
            ).first()
            return row
        finally:
            db.close()
    except Exception as exc:
        logger.warning("[voice_provider.get_default] falha: %s", exc)
        return None


def synthesize_for_tenant(tenant_id: str, text: str) -> tuple[bytes | None, dict]:
    """
    Helper alto-nivel: pega voice default do tenant, sintetiza, retorna
    (audio_bytes, info_dict). Se nao houver default ou provider nao
    configurado, retorna (None, {error_reason}).

    info_dict contem: voice_clone_id, provider_voice_id, chars_count,
    error (se houve), error_reason.
    """
    info: dict = {"chars_count": len(text or "")}
    if not is_configured(tenant_id):
        info["error_reason"] = "provider_not_configured"
        return None, info
    clone = get_default_voice_for_tenant(tenant_id)
    if clone is None:
        info["error_reason"] = "no_default_voice"
        return None, info
    info["voice_clone_id"] = clone.id
    info["provider_voice_id"] = clone.provider_voice_id
    try:
        audio = synthesize_elevenlabs(
            tenant_id=tenant_id,
            voice_id=clone.provider_voice_id,
            text=text,
        )
        return audio, info
    except VoiceProviderError as exc:
        info["error_reason"] = "provider_error"
        info["error"] = str(exc)
        return None, info


def delete_voice_elevenlabs(*, tenant_id: str, voice_id: str) -> bool:
    api_key = _eleven_key(tenant_id)
    if not api_key:
        return False
    try:
        resp = requests.delete(
            f"{_EL_BASE}/voices/{voice_id}",
            headers={"xi-api-key": api_key},
            timeout=15,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False
