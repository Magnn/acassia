"""
WhatsApp client legado — agora um shim por cima do sistema multi-provider.

Mantém a API ``whatsapp_client.enviar_mensagem(...)`` que o motor já usa,
mas internamente delega pro provider configurado do tenant em curso. Em
runtime, o tenant é resolvido via ``tenant_context.get_request_tenant_id``
quando há request Flask, ou via env ``ACASSIA_TENANT_ID`` (default)
em workers / threads.

Para uso explícito multi-tenant, use:

    from api.whatsapp_providers import get_provider_for_tenant
    p = get_provider_for_tenant(tenant_id)
    p.enviar_mensagem(...)
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

from api.whatsapp_providers import get_provider_for_tenant

load_dotenv()

logger = logging.getLogger(__name__)


def _current_tenant_id() -> str:
    try:
        from flask import has_request_context
        from tenant_context import get_request_tenant_id

        if has_request_context():
            return get_request_tenant_id()
    except Exception:
        pass
    return os.getenv("ACASSIA_TENANT_ID", "default")


class WhatsAppAPI:
    """
    Compat shim: mantém a forma do client antigo (singleton, método
    enviar_mensagem) mas resolve provider per-tenant em cada chamada.
    """

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto") -> bool:
        tid = _current_tenant_id()
        provider = get_provider_for_tenant(tid)
        return provider.enviar_mensagem(numero, conteudo, formato=formato)


whatsapp_client = WhatsAppAPI()
