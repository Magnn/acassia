"""
webhooks/media.py — Download, STT e utilitários de mídia WhatsApp
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extraído do app.py monolítico para reduzir complexidade.
Funções usadas pelo webhook Meta (_triagem_meta) durante
processamento de imagens e áudios.
"""

from __future__ import annotations

import base64
import logging
import os

import requests

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Configuração de STT
WEBAPP_TOKEN = os.getenv("WEBAPP_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
STT_MODEL = None  # Será importado de config_cliente na primeira chamada


def _get_stt_model() -> str:
    global STT_MODEL
    if STT_MODEL is None:
        try:
            from config_cliente import CONFIG_CLIENTE
            STT_MODEL = CONFIG_CLIENTE.get("modelo_stt", "gemini-2.5-flash")
        except Exception:
            STT_MODEL = "gemini-2.5-flash"
    return STT_MODEL


def is_simulator_media_id(media_id) -> bool:
    """True para IDs do `simulador_fantasmas.py` — não existem na Graph API."""
    if media_id is None:
        return False
    s = str(media_id).strip()
    return s in ("ID_IMAGEM_TESTE", "ID_AUDIO_TESTE") or (
        s.startswith("ID_") and "TESTE" in s.upper()
    )


def baixar_midia(media_id):
    """Descarrega mídia da Meta via Graph API."""
    try:
        if is_simulator_media_id(media_id):
            logger.info(
                "🧪 [DOWNLOAD] Ignorado (media_id de simulador local, sem objeto na Meta): %s",
                media_id,
            )
            return None, None
        headers = {"Authorization": f"Bearer {WEBAPP_TOKEN}"}
        # 1. Obtém URL temporária de download
        r1 = requests.get(f"https://graph.facebook.com/v19.0/{media_id}", headers=headers, timeout=12)
        if r1.status_code != 200:
            logger.error(f"❌ [DOWNLOAD] Erro Meta URL: {r1.text}")
            return None, None

        url = r1.json().get("url")
        mime = r1.json().get("mime_type", "")

        # 2. Descarrega o conteúdo binário real
        r2 = requests.get(url, headers=headers, timeout=30)
        if r2.status_code != 200:
            return None, None

        # Define extensão baseada no MIME
        ext = mime.split("/")[-1].split(";")[0] or "bin"
        filename = f"{media_id}.{ext}"
        filepath = os.path.join(DOWNLOAD_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(r2.content)

        return filepath, mime
    except Exception as e:
        logger.error(f"❌ [DOWNLOAD] Falha fatal: {e}")
        return None, None


# Variável global para o modelo Whisper (Lazy Load para não estourar RAM no boot)
_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # 'turbo' ou 'base' são ideais para rodar rápido na VPS em CPU.
        # device="cpu", compute_type="int8" reduz drasticamente o consumo de memória.
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def transcrever_audio(filepath, mime):
    """
    Motor Híbrido de Speech-to-Text.
    1. Tenta usar Whisper Local (Custo $0).
    2. Fallback para Gemini Pro/Flash se Whisper falhar ou não estiver instalado.
    """
    if not os.path.exists(filepath):
        return "[Áudio ausente]"

    # TENTATIVA 1: Whisper Local (Open Source / Zero Custo)
    try:
        import faster_whisper
        logger.info(f"🎙️ [STT] Iniciando transcrição com Whisper local: {filepath}")
        
        # O Whisper pode falhar se o OGG do WhatsApp estiver mal formatado, mas o FFmpeg embutido geralmente resolve
        model = _get_whisper_model()
        segments, info = model.transcribe(filepath, language="pt", beam_size=5)
        
        texto_whisper = " ".join([segment.text for segment in segments])
        texto_final = texto_whisper.strip()
        
        if texto_final:
            logger.info("✅ [STT] Transcrição Whisper concluída com sucesso.")
            return texto_final
    except ImportError:
        logger.info("🎙️ [STT] faster-whisper não detectado. Iniciando fallback para Gemini API...")
    except Exception as e:
        logger.error(f"❌ [STT] Erro no processamento Whisper: {e}. Acionando fallback Gemini...")

    # TENTATIVA 2: Fallback Gemini (Nuvem)
    try:
        with open(filepath, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        model = _get_stt_model()
        # Endpoint de geração de conteúdo do Gemini (Flash ou Pro)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime.split(";")[0], "data": audio_b64}},
                    {"text": "Transcreva o áudio literalmente em português, sem adicionar comentários ou introduções."}
                ]
            }],
            "generationConfig": {
                "temperature": 0.0,  # Zero para máxima fidelidade
                "max_output_tokens": 1024
            }
        }

        resp = requests.post(url, json=payload, timeout=40)
        if resp.status_code == 200:
            res_json = resp.json()
            text = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return text.strip() or "[Áudio inaudível]"

        logger.error(f"❌ [STT] Erro Gemini API: {resp.text}")
        return "[Áudio recebido]"
    except Exception as e:
        logger.error(f"❌ [STT] Erro na transcrição Gemini: {e}")
        return "[Falha no processamento de voz]"
