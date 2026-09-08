"""
api/channels/base.py — Contrato unificado de Canais (Omnichannel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Paridade ChatbotX: WhatsApp, Webchat, Telegram, Instagram, Facebook, Email.
Permite que o motor de fluxos, inbox e automações conversem com qualquer canal
através de uma interface comum.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    WEBCHAT = "webchat"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    EMAIL = "email"


@dataclass
class OutboundMessage:
    """Mensagem enviada da plataforma para o destinatário."""
    recipient_id: str  # telefone, chat_id, ig_scoped_id, email, etc.
    text: str
    format: str = "texto"  # texto, imagem, audio, video, documento
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    buttons: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InboundMessage:
    """Mensagem recebida de um usuário externo."""
    sender_id: str
    channel_type: ChannelType
    text: str
    message_id: Optional[str] = None
    format: str = "texto"
    media_url: Optional[str] = None
    sender_name: Optional[str] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelResult:
    """Resultado do envio através de um canal."""
    ok: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class ChannelAdapter(ABC):
    """Contrato base para adaptadores de canais de comunicação."""

    channel_type: ChannelType

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    @abstractmethod
    def send_message(self, message: OutboundMessage) -> ChannelResult:
        """Envia mensagem para o destinatário."""
        pass

    @abstractmethod
    def parse_inbound(self, payload: Dict[str, Any]) -> List[InboundMessage]:
        """Converte o payload bruto do webhook em lista normalizada de InboundMessage."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Indica se as credenciais do canal estão configuradas para o tenant."""
        pass
