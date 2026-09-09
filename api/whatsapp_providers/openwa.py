"""
api/whatsapp_providers/openwa.py — Provider OpenWA / WA-Automate (Self-Hosted).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conexão direta com gateway REST do ecossistema OpenWA / wa-automate:
- Suporte a multi-sessão e self-hosted (Docker)
- Envio nativo de mensagens de texto, mídia e notas de voz PTT (Push-To-Talk)
- Simulação de presença humana (digitando / gravando áudio) anti-ban
- Detecção nativa de conflitos de sessão (CONFLICT) quando aberto em outro navegador
- Geração e renovação de QR Code para pareamento rápido

Endpoints típicos do Gateway OpenWA:
  GET  {server_url}/api/{session_id}/status
  GET  {server_url}/api/{session_id}/qr
  POST {server_url}/api/{session_id}/send-message
  POST {server_url}/api/{session_id}/send-voice
  POST {server_url}/api/{session_id}/send-media
  POST {server_url}/api/{session_id}/simulate-typing
  POST {server_url}/api/{session_id}/restart
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from typing import Any, Optional

import requests

from .base import ProviderMode, SendResult, WhatsAppProvider

logger = logging.getLogger(__name__)

TIMEOUT_CONNECT = 5
TIMEOUT_READ = 15

_LAST_OPENWA_MSG_ID = threading.local()


def pop_last_openwa_msg_id() -> Optional[str]:
    """Recupera e limpa o último ID de mensagem enviado por esta thread."""
    val = getattr(_LAST_OPENWA_MSG_ID, "value", None)
    _LAST_OPENWA_MSG_ID.value = None
    return val


def _normalize_openwa_jid(numero: str) -> str:
    """Garante sufixo @c.us ou @g.us esperado pelo wa-automate / OpenWA."""
    num = str(numero or "").strip()
    if not num:
        return ""
    if "@" in num:
        return num
    # Se só tiver dígitos, normaliza para contato
    clean_digits = "".join(ch for ch in num if ch.isdigit())
    return f"{clean_digits}@c.us" if clean_digits else num


class OpenWAProvider(WhatsAppProvider):
    """
    Provider para servidor OpenWA / wa-automate REST Gateway.
    """

    mode = ProviderMode.OPENWA

    @property
    def server_url(self) -> str:
        return str(
            self.config.get("openwa_server_url")
            or self.config.get("server_url")
            or ""
        ).rstrip("/")

    @property
    def session_id(self) -> str:
        return str(
            self.config.get("openwa_session_id")
            or self.config.get("session_id")
            or self.tenant_id
            or "default"
        ).strip()

    @property
    def api_key(self) -> str:
        return str(
            self.config.get("openwa_api_key")
            or self.config.get("api_key")
            or ""
        ).strip()

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def status(self) -> dict[str, Any]:
        """
        Consulta estado de conexão da sessão OpenWA.
        Detecta e reporta especificamente o estado CONFLICT.
        """
        if not (self.server_url and self.session_id):
            return {
                "ok": False,
                "mode": self.mode.value,
                "configured": False,
                "hint": "Configure server_url e session_id do OpenWA Gateway.",
            }

        url = f"{self.server_url}/api/{self.session_id}/status"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            if resp.status_code == 404:
                # Tenta rota raiz de status /{session_id}/status
                url_alt = f"{self.server_url}/{self.session_id}/status"
                resp = requests.get(
                    url_alt,
                    headers=self._headers(),
                    timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                )

            data = resp.json() if resp.text and "json" in resp.headers.get("content-type", "").lower() else {}
            raw_state = (
                data.get("status")
                or data.get("state")
                or data.get("connectionState")
                or ("CONNECTED" if resp.status_code == 200 else "DISCONNECTED")
            )
            raw_state_str = str(raw_state).upper()

            # Mapeamento do ciclo de vida OpenWA
            if "CONFLICT" in raw_state_str:
                return {
                    "ok": False,
                    "mode": self.mode.value,
                    "configured": True,
                    "connection_state": "CONFLICT",
                    "hint": "Conflito de Sessão: o WhatsApp Web foi aberto em outra aba ou navegador. Desconecte lá e reinicie a sessão aqui.",
                    "details": data,
                }
            elif raw_state_str in ("CONNECTED", "OPEN", "READY"):
                return {
                    "ok": True,
                    "mode": self.mode.value,
                    "configured": True,
                    "connection_state": "open",
                    "hint": None,
                    "details": data,
                }
            elif raw_state_str in ("PAIRING", "QR", "QRCODE", "SCAN_QR_CODE", "UNPAIRED"):
                return {
                    "ok": False,
                    "mode": self.mode.value,
                    "configured": True,
                    "connection_state": "pairing",
                    "hint": "Aguardando leitura do QR Code no aplicativo WhatsApp.",
                    "details": data,
                }
            else:
                return {
                    "ok": False,
                    "mode": self.mode.value,
                    "configured": True,
                    "connection_state": "close",
                    "hint": f"Sessão OpenWA desconectada ({raw_state}).",
                    "details": data,
                }

        except requests.exceptions.RequestException as exc:
            return {
                "ok": False,
                "mode": self.mode.value,
                "configured": True,
                "hint": f"Gateway OpenWA inacessível ({self.server_url}): {exc}",
            }

    def simulate_presence(
        self,
        numero: str,
        presence: str = "composing",
        delay_seconds: float = 0.0,
    ) -> bool:
        """
        Simula digitação ('composing') ou gravação de áudio ('recording')
        no WhatsApp para humanização e redução de bloqueio (anti-ban).
        """
        if not (self.server_url and self.session_id):
            return False

        to_jid = _normalize_openwa_jid(numero)
        is_recording = presence in ("recording", "audio")
        url_typing = f"{self.server_url}/api/{self.session_id}/simulate-typing"

        try:
            # Tenta endpoint simulate-typing ou presence
            payload = {
                "to": to_jid,
                "on": True,
                "presence": "recording" if is_recording else "composing",
            }
            resp = requests.post(
                url_typing,
                json=payload,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, 5),
            )
            ok = resp.status_code in (200, 201, 204)

            # Se foi solicitado delay para simular o tempo de digitação/gravação
            if delay_seconds > 0:
                sleep_time = min(max(delay_seconds, 0.5), 5.0)
                time.sleep(sleep_time)
                # Desliga a digitação após o delay
                requests.post(
                    url_typing,
                    json={"to": to_jid, "on": False, "presence": "paused"},
                    headers=self._headers(),
                    timeout=(TIMEOUT_CONNECT, 3),
                )
            return ok
        except Exception as exc:
            logger.debug("[openwa.simulate_presence] Falha silenciosa: %s", exc)
            return False

    def enviar_mensagem(
        self,
        numero: str,
        conteudo: str,
        formato: str = "texto",
        media_url: Optional[str] = None,
    ) -> bool:
        """
        Envia mensagem via OpenWA Gateway.
        Suporta texto, imagens, vídeos, documentos e áudio gravado nativo (PTT).
        """
        if not conteudo and not media_url:
            return False
        if not (self.server_url and self.session_id):
            logger.error("[openwa] tenant=%s sem credenciais configuradas", self.tenant_id)
            return False

        to_jid = _normalize_openwa_jid(numero)
        url = ""
        payload: dict[str, Any] = {}

        if formato == "texto":
            url = f"{self.server_url}/api/{self.session_id}/send-message"
            payload = {
                "to": to_jid,
                "text": str(conteudo),
            }
        elif formato == "audio":
            # Destaque OpenWA: envio nativo de nota de voz (PTT push-to-talk)
            url = f"{self.server_url}/api/{self.session_id}/send-voice"
            audio_source = media_url or conteudo
            payload = {
                "to": to_jid,
                "url": audio_source,
                "ptt": True,
            }
        elif formato in ("imagem", "video", "documento"):
            url = f"{self.server_url}/api/{self.session_id}/send-media"
            media_source = media_url or conteudo
            payload = {
                "to": to_jid,
                "url": media_source,
                "type": "image" if formato == "imagem" else formato,
                "caption": conteudo if media_url else "",
            }
        else:
            logger.warning("[openwa] Formato desconhecido: %s, caindo para texto", formato)
            url = f"{self.server_url}/api/{self.session_id}/send-message"
            payload = {"to": to_jid, "text": str(conteudo)}

        try:
            resp = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )

            # Fallback para rotas alternativas do OpenWA Gateway se 404
            if resp.status_code == 404 and formato == "texto":
                alt_url = f"{self.server_url}/api/{self.session_id}/sendText"
                resp = requests.post(
                    alt_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                )
            elif resp.status_code == 404 and formato == "audio":
                alt_url = f"{self.server_url}/api/{self.session_id}/sendPtt"
                resp = requests.post(
                    alt_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                )

            if resp.status_code in (200, 201):
                try:
                    data = resp.json() if resp.text else {}
                    msg_id = (
                        data.get("messageId")
                        or data.get("id")
                        or (data.get("data") or {}).get("id")
                    )
                    if msg_id:
                        _LAST_OPENWA_MSG_ID.value = str(msg_id)
                except Exception:
                    pass
                logger.info(
                    "[openwa] tenant=%s %s enviado com sucesso para %s",
                    self.tenant_id, formato.upper(), to_jid,
                )
                return True

            logger.error(
                "[openwa] tenant=%s HTTP %s para %s — %s",
                self.tenant_id, resp.status_code, to_jid, (resp.text or "")[:300],
            )
            return False

        except requests.exceptions.RequestException as exc:
            logger.error("[openwa] tenant=%s erro ao enviar para %s: %s", self.tenant_id, to_jid, exc)
            return False

    def get_qr_code(self) -> SendResult:
        """Busca o QR code para parear a sessão no OpenWA."""
        if not (self.server_url and self.session_id):
            return SendResult(ok=False, error="credenciais_ausentes")

        url = f"{self.server_url}/api/{self.session_id}/qr"
        try:
            resp = requests.get(
                url,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            if resp.status_code == 200:
                c_type = resp.headers.get("content-type", "").lower()
                if "application/json" in c_type or (resp.text and resp.text.strip().startswith("{")):
                    data = resp.json()
                    return SendResult(ok=True, raw=data)
                elif "image" in c_type or resp.content:
                    # Se retornar a imagem pura em PNG/JPEG, converte para base64
                    b64 = base64.b64encode(resp.content).decode("utf-8")
                    return SendResult(
                        ok=True,
                        raw={
                            "base64": f"data:{c_type or 'image/png'};base64,{b64}",
                            "qr": f"data:{c_type or 'image/png'};base64,{b64}",
                        },
                    )
            return SendResult(ok=False, error=f"HTTP {resp.status_code}", raw={"status": resp.status_code})
        except requests.exceptions.RequestException as exc:
            return SendResult(ok=False, error=str(exc))

    def restart_session(self) -> bool:
        """Reinicia a sessão após desconexão ou conflito (CONFLICT)."""
        if not (self.server_url and self.session_id):
            return False
        url = f"{self.server_url}/api/{self.session_id}/restart"
        try:
            resp = requests.post(
                url,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, 10),
            )
            return resp.status_code in (200, 201, 204)
        except Exception as exc:
            logger.warning("[openwa.restart_session] Falha ao reiniciar: %s", exc)
            return False
