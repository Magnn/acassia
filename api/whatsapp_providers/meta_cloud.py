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
import random
import threading
import time
from typing import Any

import requests

from .base import ProviderMode, SendResult, WhatsAppProvider


# Thread-local pra propagar wamid do envio mais recente sem quebrar
# a assinatura legada de enviar_mensagem. Engine chama pop_last_wamid()
# logo apos um send pra associar ao Mensagem persistido.
_LAST_WAMID = threading.local()


def pop_last_wamid() -> str | None:
    """Retorna e limpa o wamid do envio mais recente desta thread."""
    val = getattr(_LAST_WAMID, "value", None)
    _LAST_WAMID.value = None
    return val

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v21.0"
TIMEOUT_CONNECT = 5
TIMEOUT_READ = 15

# Backoff config: 4xx nao retry, 5xx/timeout/connection-reset retry com jitter
SEND_MAX_ATTEMPTS = int(os.getenv("META_SEND_MAX_ATTEMPTS", "3"))
SEND_BASE_BACKOFF_S = float(os.getenv("META_SEND_BASE_BACKOFF_S", "1.0"))
SEND_MAX_BACKOFF_S = float(os.getenv("META_SEND_MAX_BACKOFF_S", "8.0"))


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

        # Retry com backoff exponencial + jitter para 5xx, timeout e erros de rede.
        # 4xx (auth/validacao) NAO retentamos — falha rapido pra alertar config errada.
        for attempt in range(1, SEND_MAX_ATTEMPTS + 1):
            try:
                response = requests.post(
                    self.base_url,
                    json=payload,
                    headers=self._headers(),
                    timeout=(TIMEOUT_CONNECT, TIMEOUT_READ),
                )
                status = response.status_code
                if status == 200:
                    # Captura wamid do response pra tracking de delivery
                    try:
                        body = response.json() or {}
                        msgs = body.get("messages") or []
                        if msgs and isinstance(msgs, list):
                            wamid = msgs[0].get("id") if isinstance(msgs[0], dict) else None
                            if wamid:
                                _LAST_WAMID.value = wamid
                    except Exception:
                        pass

                    if attempt > 1:
                        logger.info(
                            "[meta_cloud] tenant=%s %s enviado para %s (sucesso na tentativa %s/%s)",
                            self.tenant_id, formato.upper(), numero,
                            attempt, SEND_MAX_ATTEMPTS,
                        )
                    else:
                        logger.info(
                            "[meta_cloud] tenant=%s %s enviado para %s",
                            self.tenant_id, formato.upper(), numero,
                        )
                    return True

                # 4xx: nao retry (auth/permissao/numero invalido)
                if 400 <= status < 500:
                    logger.error(
                        "[meta_cloud] tenant=%s HTTP %s para %s (4xx — sem retry) body: %s",
                        self.tenant_id, status, numero,
                        (response.text or "")[:300],
                    )
                    return False

                # 5xx: retry se ainda houver tentativas
                if attempt < SEND_MAX_ATTEMPTS:
                    backoff = min(
                        SEND_MAX_BACKOFF_S,
                        SEND_BASE_BACKOFF_S * (2 ** (attempt - 1)),
                    ) + random.uniform(0, 0.4)
                    logger.warning(
                        "[meta_cloud] tenant=%s HTTP %s tentativa=%s/%s aguardando %.1fs — body: %s",
                        self.tenant_id, status, attempt, SEND_MAX_ATTEMPTS, backoff,
                        (response.text or "")[:200],
                    )
                    time.sleep(backoff)
                    continue

                logger.error(
                    "[meta_cloud] tenant=%s HTTP %s para %s exauridas %s tentativas — body: %s",
                    self.tenant_id, status, numero, SEND_MAX_ATTEMPTS,
                    (response.text or "")[:300],
                )
                return False

            except requests.exceptions.Timeout:
                if attempt < SEND_MAX_ATTEMPTS:
                    backoff = min(
                        SEND_MAX_BACKOFF_S,
                        SEND_BASE_BACKOFF_S * (2 ** (attempt - 1)),
                    ) + random.uniform(0, 0.4)
                    logger.warning(
                        "[meta_cloud] tenant=%s timeout tentativa=%s/%s aguardando %.1fs",
                        self.tenant_id, attempt, SEND_MAX_ATTEMPTS, backoff,
                    )
                    time.sleep(backoff)
                    continue
                logger.error(
                    "[meta_cloud] tenant=%s timeout exaurido para %s", self.tenant_id, numero,
                )
                return False

            except requests.exceptions.ConnectionError as exc:
                if attempt < SEND_MAX_ATTEMPTS:
                    backoff = min(
                        SEND_MAX_BACKOFF_S,
                        SEND_BASE_BACKOFF_S * (2 ** (attempt - 1)),
                    ) + random.uniform(0, 0.4)
                    logger.warning(
                        "[meta_cloud] tenant=%s connection error %s tentativa=%s/%s aguardando %.1fs",
                        self.tenant_id, exc, attempt, SEND_MAX_ATTEMPTS, backoff,
                    )
                    time.sleep(backoff)
                    continue
                logger.error(
                    "[meta_cloud] tenant=%s connection error exaurido para %s: %s",
                    self.tenant_id, numero, exc,
                )
                return False

            except requests.exceptions.RequestException as exc:
                # Erros nao-retryable (ex.: SSL, invalid URL) — fail fast
                logger.error(
                    "[meta_cloud] tenant=%s erro nao-retryable %s: %s",
                    self.tenant_id, numero, exc,
                )
                return False

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
