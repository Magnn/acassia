"""
Coex — BSP brasileiro parceiro Meta.

Implementação ESTRUTURAL: a integração concreta requer doc oficial Coex
(URL base, formato de payload, autenticação) que varia por contrato.
Quando o tenant fornecer essas infos, plugar em ``_send`` abaixo.

Config esperada no tenant_config:
  - whatsapp.coex.api_url      (variable)  ex.: https://api.coex.cx/v1/messages
  - whatsapp.coex.instance     (variable)  identificador da instância
  - whatsapp.coex.api_key      (secret)    bearer token
"""

from __future__ import annotations

import logging
from typing import Any

from .base import ProviderMode, WhatsAppProvider

logger = logging.getLogger(__name__)


class CoexProvider(WhatsAppProvider):
    mode = ProviderMode.COEX

    @property
    def api_url(self) -> str:
        return str(self.config.get("coex_api_url") or "").strip()

    @property
    def instance(self) -> str:
        return str(self.config.get("coex_instance") or "").strip()

    @property
    def api_key(self) -> str:
        return str(self.config.get("coex_api_key") or "").strip()

    def status(self) -> dict[str, Any]:
        configured = bool(self.api_url and self.api_key)
        return {
            "ok": False,  # ainda não validamos conexão real
            "mode": self.mode.value,
            "configured": configured,
            "implemented": False,
            "hint": (
                "Coex é stub. Forneça api_url, instance e api_key da Coex; "
                "a integração de envio será implementada conforme docs do BSP."
            ),
        }

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto") -> bool:
        # TODO: implementar quando tenant fornecer credenciais + endpoint Coex.
        # Tipicamente é um POST para api_url com payload similar ao Meta Cloud
        # (Coex repassa pra Graph API), mas formato exato varia.
        logger.warning(
            "[coex] tenant=%s envio NÃO implementado (stub) — to=%s formato=%s len=%d",
            self.tenant_id, numero, formato, len(conteudo or ""),
        )
        return False
