"""
tts/audio_engine.py — Motor de Voz SUPREME v3.3 (Gemini Native + Fix Storage)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Geração de Áudios (TTS) usando a API Nativa do Gemini 2.5 Flash.

ESTA VERSÃO RESOLVE:
🔥 FIX STORAGE: Agora faz o upload do arquivo WAV convertido, não do PCM bruto.
🔥 NATURALIDADE: Refinamento no pacing místico (vírgula após o nome do lead).
🔥 ROBUSTEZ: Verificação de integridade dos bytes PCM antes da conversão.
🔥 COMPATIBILIDADE: Configuração de amostragem cravada em 24kHz para WhatsApp.
"""

import os
import hashlib
import logging
import re
import time
import base64
import wave
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from db.database import SessionLocal
from db.models import AudioCache
from config_cliente import CONFIG_CLIENTE

logger = logging.getLogger(__name__)

# Configuração de Caminhos
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_DIR = os.path.join(_ROOT, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class AudioEngine:
    def __init__(self):
        # Chave e Configuração Gemini
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_tts = "gemini-2.5-flash-preview-tts"
        
        # Vozes: Leda (Maternal/Grave), Kore (Mística), Aoede (Séria)
        self.voice_name = os.getenv("GEMINI_VOICE_NAME", "Leda")
        
        # URL base para o WhatsApp (importante para o download da Meta)
        self.public_url_base = os.getenv("PUBLIC_URL", "http://127.0.0.1:5000").rstrip('/')

    # ── INTERFACE PRINCIPAL ──────────────────────────────────────────────
    def gerar(self, texto: str) -> str:
        """Interface simplificada para o engine principal."""
        return self.gerar_audio_url(texto, {}, e_template_fixo=False) or ""

    def gerar_audio_url(
        self,
        template: str,
        variaveis: dict,
        e_template_fixo: bool = True
    ) -> Optional[str]:
        """
        Substitui variáveis, aplica pacing dramático e gera o áudio WAV.
        """
        if not self.api_key or not template:
            logger.warning("⚠️ [TTS] Geração abortada: Falta chave ou texto.")
            return None

        # 1. Preparação do Texto (Substituição de variáveis)
        texto_final = template
        for k, v in variaveis.items():
            # Adiciona uma vírgula após o nome para a IA fazer uma pausa natural
            val = f"{v}," if k == "nome" and v else v
            texto_final = texto_final.replace(f"{{{{{k}}}}}", str(val))
        
        # 2. Refinamento de Pacing (O segredo do realismo)
        texto_limpo = self._limpar_para_tts(texto_final)
        texto_dramatico = self._aplicar_pacing_mistico(texto_limpo)
        
        if not texto_dramatico: return None

        # 3. Cache Check (Baseado no texto limpo, não no dramático)
        cache_key = hashlib.sha256(texto_limpo.encode("utf-8")).hexdigest()[:32]
        url_cacheada = self._buscar_cache(cache_key)
        if url_cacheada:
            logger.info(f"🎯 [TTS] Cache hit: {cache_key[:10]}")
            return url_cacheada

        # 4. Geração via Gemini API
        logger.info(f"🎙️ [TTS] Gerando voz ({self.voice_name}) para: '%.50s...'", texto_limpo)
        audio_raw_pcm = self._chamar_gemini_tts(texto_dramatico)
        if not audio_raw_pcm or len(audio_raw_pcm) < 100: 
            logger.error("🚨 [TTS] Gemini retornou áudio vazio ou corrompido.")
            return None

        # 5. Conversão para WAV
        filename = f"tts_{cache_key}.wav"
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        
        if self._salvar_pcm_como_wav(audio_raw_pcm, filepath):
            # 6. Publicação e Registro
            # Lemos os bytes do WAV para o upload (Bug fix: não enviar PCM bruto para a nuvem)
            with open(filepath, "rb") as f:
                wav_bytes = f.read()

            url_final = self._upload_storage_externo(filename, wav_bytes) or f"{self.public_url_base}/media/{filename}"
            
            expiry = timedelta(days=30) if e_template_fixo else timedelta(hours=72)
            self._salvar_cache(cache_key, url_final, texto_limpo, expiry)
            return url_final

        return None

    # ── MÉTODOS DE API E PROCESSAMENTO ───────────────────────────────────
    def _chamar_gemini_tts(self, texto: str) -> Optional[bytes]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_tts}:generateContent?key={self.api_key}"
        
        # Prompt de Sistema Refinado para Entonação
        instrucao_voz = (
            "Diga este texto como umo Meu Mistério Quiromante experiente. "
            "Use um tom de voz calmo, acolhedor, místico e com pausas naturais. "
            "O texto é: "
        )

        payload = {
            "contents": [{
                "parts": [{"text": f"{instrucao_voz} {texto}"}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self.voice_name}
                    }
                }
            }
        }

        for t in range(1, 4):
            try:
                r = requests.post(url, json=payload, timeout=45)
                if r.status_code == 200:
                    data = r.json()
                    parts = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                    for p in parts:
                        if 'inlineData' in p:
                            return base64.b64decode(p['inlineData']['data'])
                
                logger.error(f"❌ [TTS] Gemini HTTP {r.status_code}: {r.text[:200]}")
                time.sleep(t * 2)
            except Exception as e:
                logger.error(f"🚨 [TTS] Erro na tentativa {t}: {e}")
                time.sleep(t)
        return None

    def _salvar_pcm_como_wav(self, pcm_data: bytes, output_path: str) -> bool:
        """Converte RAW PCM 16-bit 24kHz para WAV standard."""
        try:
            with wave.open(output_path, 'wb') as wav_file:
                wav_file.setnchannels(1)   # Mono
                wav_file.setsampwidth(2)  # 16-bit (2 bytes)
                wav_file.setframerate(24000)
                wav_file.writeframes(pcm_data)
            return True
        except Exception as e:
            logger.error(f"🚨 [TTS] Erro na conversão WAV: {e}")
            if os.path.exists(output_path): os.remove(output_path)
            return False

    def _aplicar_pacing_mistico(self, texto: str) -> str:
        """Injeta pontuação invisível para forçar a IA a dar pausas dramáticas."""
        # Vírgulas viram pausas curtas
        texto = texto.replace(", ", ", ... ")
        # Pontos viram pausas longas com quebra
        texto = texto.replace(". ", ". \n\n ")
        # Três pontos viram um silêncio reflexivo
        texto = texto.replace("...", " ... ... ")
        return texto

    def _limpar_para_tts(self, texto: str) -> str:
        if not texto: return ""
        # Remove emojis e caracteres técnicos
        texto = re.sub(r"[^\w\s\.,!?;:\-àáâãäéêëíïóôõöúüçñ]", "", texto, flags=re.UNICODE)
        # Remove markdown
        texto = re.sub(r"[*_~`]", "", texto)
        return re.sub(r"\s+", " ", texto).strip()

    def _upload_storage_externo(self, filename: str, wav_data: bytes) -> Optional[str]:
        """Suporte preparado para S3/R2."""
        bucket = os.getenv("AUDIO_STORAGE_BUCKET")
        if not bucket: return None
        try:
            import boto3
            s3 = boto3.client("s3", endpoint_url=os.getenv("AUDIO_STORAGE_ENDPOINT"),
                              aws_access_key_id=os.getenv("AUDIO_STORAGE_KEY_ID"),
                              aws_secret_access_key=os.getenv("AUDIO_STORAGE_SECRET"))
            s3.put_object(Bucket=bucket, Key=f"audio/{filename}", Body=wav_data, ContentType="audio/wav")
            return f"{os.getenv('AUDIO_BASE_URL').rstrip('/')}/audio/{filename}"
        except Exception as e: 
            logger.warning(f"⚠️ [TTS] Falha upload nuvem: {e}")
            return None

    # ── GESTÃO DE CACHE ──────────────────────────────────────────────────
    def _buscar_cache(self, cache_key: str) -> Optional[str]:
        db = SessionLocal()
        try:
            res = db.query(AudioCache).filter_by(cache_key=cache_key).first()
            if res:
                exp = res.expira_em.replace(tzinfo=timezone.utc)
                if exp < datetime.now(timezone.utc):
                    db.delete(res)
                    db.commit()
                    return None
                return res.url_publica
            return None
        except Exception as e:
            logger.error(f"🚨 [TTS] Erro busca cache: {e}")
            return None
        finally: db.close()

    def _salvar_cache(self, cache_key: str, url: str, texto: str, expiry: timedelta):
        db = SessionLocal()
        try:
            novo = AudioCache(cache_key=cache_key, url_publica=url, texto_original=texto[:500],
                             expira_em=datetime.now(timezone.utc) + expiry,
                             criado_em=datetime.now(timezone.utc))
            db.add(novo)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"🚨 [TTS] Erro ao salvar cache: {e}")
        finally: db.close()