"""api/channels/registry.py — Registry e Factory de adaptadores de canal."""
from typing import Dict, Type
from api.channels.base import ChannelAdapter, ChannelType
from api.channels.whatsapp import WhatsAppChannelAdapter
from api.channels.webchat import WebchatChannelAdapter
from api.channels.telegram import TelegramChannelAdapter

_ADAPTER_MAP: Dict[ChannelType, Type[ChannelAdapter]] = {
    ChannelType.WHATSAPP: WhatsAppChannelAdapter,
    ChannelType.WEBCHAT: WebchatChannelAdapter,
    ChannelType.TELEGRAM: TelegramChannelAdapter,
}

def get_channel_adapter(channel: str | ChannelType, tenant_id: str) -> ChannelAdapter:
    """Retorna instância do ChannelAdapter para o canal e tenant informados."""
    try:
        ctype = ChannelType(str(channel).lower())
    except ValueError:
        ctype = ChannelType.WHATSAPP

    cls = _ADAPTER_MAP.get(ctype, WhatsAppChannelAdapter)
    return cls(tenant_id=tenant_id)

def list_supported_channels() -> list[str]:
    return [c.value for c in ChannelType]
