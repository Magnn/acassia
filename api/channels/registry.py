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
    except ValueError as exc:
        raise ValueError(f"unsupported_channel:{channel}") from exc

    cls = _ADAPTER_MAP.get(ctype)
    if cls is None:
        raise ValueError(f"channel_not_implemented:{ctype.value}")
    return cls(tenant_id=tenant_id)

def list_supported_channels() -> list[str]:
    return [channel.value for channel in _ADAPTER_MAP]
