"""
Pacote de providers WhatsApp.

4 modos suportados por tenant:
- meta_cloud: Meta Cloud API direta (Graph API)
- coex: Coex (BSP parceiro Meta — repassa pra Cloud API)
- evolution: Evolution API (não oficial, conexão via QR como WhatsApp Web)
- openwa: OpenWA / WA-Automate Gateway (self-hosted, suporte PTT nativo e detecção de conflitos)

Use ``get_provider_for_tenant(tenant_id)`` para obter a instância correta
baseada na config persistida no tenant. Fallback automático para o legado
single-tenant (env WEBAPP_TOKEN/PHONE_NUMBER_ID) se nenhum tenant config
estiver presente, mantendo retrocompat.
"""

from .base import (
    ProviderError,
    ProviderMode,
    SendResult,
    WhatsAppProvider,
)
from .factory import get_provider_for_tenant
from .openwa import OpenWAProvider

__all__ = [
    "OpenWAProvider",
    "ProviderError",
    "ProviderMode",
    "SendResult",
    "WhatsAppProvider",
    "get_provider_for_tenant",
]
