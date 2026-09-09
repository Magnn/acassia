"""
Evolution API — provider não oficial (open source).

Conexão via QR code (replica WhatsApp Web). Mais barato e sem App Review,
mas viola TOS do WhatsApp e pode banir o número. Use por sua conta e risco.

Endpoint padrão Evolution API v2:
  POST {server_url}/message/sendText/{instance}
  POST {server_url}/message/sendMedia/{instance}
  GET  {server_url}/instance/connectionState/{instance}
  GET  {server_url}/instance/qrcode/{instance}    (no momento de pareamento)

Config esperada:
  - whatsapp.evolution.server_url   (variable)  ex.: https://evo.example.com
  - whatsapp.evolution.instance     (variable)  nome da instância
  - whatsapp.evolution.api_key      (secret)    apikey global ou da instância

Ver docs: https://doc.evolution-api.com
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from .base import ProviderMode, SendResult, WhatsAppProvider

import threading

logger = logging.getLogger(__name__)

TIMEOUT_CONNECT = 5
TIMEOUT_READ = 15
_LAST_EVOLUTION_MSG_ID = threading.local()


def pop_last_evolution_msg_id() -> str | None:
    val = getattr(_LAST_EVOLUTION_MSG_ID, "value", None)
    _LAST_EVOLUTION_MSG_ID.value = None
    return val


class EvolutionProvider(WhatsAppProvider):
    mode = ProviderMode.EVOLUTION

    @property
    def server_url(self) -> str:
        return str(self.config.get("evolution_server_url") or "").rstrip("/")

    @property
    def instance(self) -> str:
        return str(self.config.get("evolution_instance") or "").strip()

    @property
    def api_key(self) -> str:
        return str(self.config.get("evolution_api_key") or "").strip()

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def status(self) -> dict[str, Any]:
        configured = bool(self.server_url and self.instance and self.api_key)
        if not configured:
            return {
                "ok": False,
                "mode": self.mode.value,
                "configured": False,
                "hint": "Forneça server_url, instance e api_key do servidor Evolution.",
            }
        # Tenta health check da instância — connectionState
        try:
            resp = requests.get(
                f"{self.server_url}/instance/connectionState/{self.instance}",
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            ready = resp.status_code == 200
            data = resp.json() if resp.text else {}
            state = (data.get("instance") or {}).get("state") if isinstance(data, dict) else None
            return {
                "ok": ready and state == "open",
                "mode": self.mode.value,
                "configured": True,
                "connection_state": state,
                "hint": (
                    None if state == "open"
                    else "Instância não pareada. Acesse /instance/qrcode no Evolution e escaneie o QR."
                ),
            }
        except requests.exceptions.RequestException as exc:
            return {
                "ok": False,
                "mode": self.mode.value,
                "configured": True,
                "hint": f"Servidor Evolution inacessível: {exc}",
            }

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto") -> bool:
        if not conteudo or not str(conteudo).strip():
            return False
        if not (self.server_url and self.instance and self.api_key):
            logger.error("[evolution] tenant=%s sem credenciais", self.tenant_id)
            return False

        if formato == "texto":
            url = f"{self.server_url}/message/sendText/{self.instance}"
            payload = {"number": numero, "text": conteudo}
        elif formato in ("audio", "imagem", "video", "documento"):
            url = f"{self.server_url}/message/sendMedia/{self.instance}"
            kind_map = {
                "audio": "audio",
                "imagem": "image",
                "video": "video",
                "documento": "document",
            }
            payload = {
                "number": numero,
                "mediatype": kind_map[formato],
                "media": conteudo,  # URL pública
            }
        else:
            logger.warning("[evolution] formato desconhecido: %s", formato)
            return False

        try:
            resp = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            if resp.status_code in (200, 201):
                try:
                    data = resp.json() if resp.text else {}
                    msg_id = (data.get("key") or {}).get("id") or data.get("messageId") or data.get("id")
                    if msg_id:
                        _LAST_EVOLUTION_MSG_ID.value = str(msg_id)
                except Exception:
                    pass
                logger.info(
                    "[evolution] tenant=%s %s enviado para %s",
                    self.tenant_id, formato.upper(), numero,
                )
                return True
            logger.error(
                "[evolution] tenant=%s HTTP %s para %s — %s",
                self.tenant_id, resp.status_code, numero, (resp.text or "")[:300],
            )
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("[evolution] tenant=%s erro %s: %s", self.tenant_id, numero, exc)
            return False

    def get_qr_code(self) -> SendResult:
        """Busca o QR code atual pra parear a instância (uso na tela de conexão)."""
        if not (self.server_url and self.instance and self.api_key):
            return SendResult(ok=False, error="credenciais ausentes")
        try:
            resp = requests.get(
                f"{self.server_url}/instance/connect/{self.instance}",
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            data = resp.json() if resp.text else {}
            if resp.status_code == 200 and isinstance(data, dict):
                # Evolution v2 retorna {base64, code, count} no objeto raiz
                return SendResult(ok=True, raw=data)
            return SendResult(ok=False, error=f"HTTP {resp.status_code}", raw=data)
        except requests.exceptions.RequestException as exc:
            return SendResult(ok=False, error=str(exc))
