"""
Meta Cloud API direta — Graph API v21+.

Lê credenciais do tenant_config (TenantFlowVariable + TenantFlowSecret):
  - whatsapp.phone_number_id   (variable)
  - whatsapp.waba_id           (variable, opcional pra envio)
  - whatsapp.access_token      (secret)

Fallback retro: env vars WEBAPP_TOKEN, PHONE_NUMBER_ID, WABA_ID.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

from .base import ProviderMode, SendResult, WhatsAppProvider

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v21.0"
TIMEOUT_CONNECT = 5
TIMEOUT_READ = 15


class MetaCloudProvider(WhatsAppProvider):
    mode = ProviderMode.META_CLOUD

    @property
    def phone_id(self) -> str:
        return str(
            self.config.get("phone_number_id")
            or os.getenv("PHONE_NUMBER_ID")
            or ""
        ).strip()

    @property
    def access_token(self) -> str:
        return str(
            self.config.get("access_token")
            or os.getenv("WEBAPP_TOKEN")
            or ""
        ).strip()

    @property
    def waba_id(self) -> str:
        return str(
            self.config.get("waba_id")
            or os.getenv("WABA_ID")
            or ""
        ).strip()

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{GRAPH_VERSION}/{self.phone_id}/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def status(self) -> dict[str, Any]:
        configured = bool(self.phone_id and self.access_token)
        return {
            "ok": configured,
            "mode": self.mode.value,
            "configured": configured,
            "phone_number_id": self.phone_id or None,
            "waba_id": self.waba_id or None,
            "hint": (
                None
                if configured
                else "Configure phone_number_id e access_token (System User token, permanente)."
            ),
        }

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto") -> bool:
        if not conteudo or not str(conteudo).strip():
            return False
        if not self.phone_id or not self.access_token:
            logger.error("[meta_cloud] tenant=%s sem credenciais — abortando envio", self.tenant_id)
            return False

        payload: dict[str, Any] = {"messaging_product": "whatsapp", "to": numero}

        if formato == "texto":
            payload["type"] = "text"
            payload["text"] = {"body": conteudo}
        elif formato == "audio":
            payload["type"] = "audio"
            payload["audio"] = {"link": conteudo}
        elif formato == "imagem":
            payload["type"] = "image"
            payload["image"] = {"link": conteudo}
        elif formato == "video":
            payload["type"] = "video"
            payload["video"] = {"link": conteudo}
        elif formato == "documento":
            payload["type"] = "document"
            payload["document"] = {"link": conteudo}
        else:
            logger.warning("[meta_cloud] formato desconhecido: %s", formato)
            return False

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            if response.status_code == 200:
                logger.info(
                    "[meta_cloud] tenant=%s %s enviado para %s",
                    self.tenant_id, formato.upper(), numero,
                )
                return True
            logger.error(
                "[meta_cloud] tenant=%s HTTP %s para %s — body: %s",
                self.tenant_id, response.status_code, numero,
                (response.text or "")[:300],
            )
            return False
        except requests.exceptions.Timeout:
            logger.error(
                "[meta_cloud] tenant=%s timeout %s para %s", self.tenant_id, formato, numero,
            )
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("[meta_cloud] tenant=%s erro %s: %s", self.tenant_id, numero, exc)
            return False

    def test_connection(self, target_number: str) -> SendResult:
        """Override pra capturar message_id retornado pela Graph API."""
        if not self.phone_id or not self.access_token:
            return SendResult(ok=False, error="credenciais ausentes")
        try:
            response = requests.post(
                self.base_url,
                json={
                    "messaging_product": "whatsapp",
                    "to": target_number,
                    "type": "text",
                    "text": {"body": "Teste de conexão Sibila — integração Meta Cloud OK."},
                },
                headers=self._headers(),
                timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
            )
            data = response.json() if response.text else {}
            if response.status_code == 200:
                msgs = data.get("messages") or []
                wamid = (msgs[0].get("id") if msgs else None) if isinstance(msgs, list) else None
                return SendResult(ok=True, message_id=wamid, raw=data)
            return SendResult(
                ok=False,
                error=f"HTTP {response.status_code}: {(response.text or '')[:200]}",
                raw=data,
            )
        except requests.exceptions.RequestException as exc:
            return SendResult(ok=False, error=str(exc))
