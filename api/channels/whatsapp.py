"""api/channels/whatsapp.py — Adaptador para canal WhatsApp."""
import logging
from api.channels.base import (
    ChannelAdapter,
    ChannelCapabilities,
    ChannelType,
    ChannelResult,
    OutboundMessage,
    InboundMessage,
)

try:
    import horoscope
except Exception:
    horoscope = None

logger = logging.getLogger(__name__)

class WhatsAppChannelAdapter(ChannelAdapter):
    channel_type = ChannelType.WHATSAPP

    def get_capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_buttons=False,
            supports_media=True,
            supports_templates=False,
            supports_reactions=False,
            supports_audio=True,
            supports_markdown=False,
        )

    def send_message(self, message: OutboundMessage) -> ChannelResult:
        try:
            client = horoscope._get_whatsapp_client(self.tenant_id) if horoscope else None
            if not client:
                return ChannelResult(ok=False, error="whatsapp_client_not_configured")

            caps = self.get_capabilities()
            body_text = message.text or ""
            if message.buttons and not caps.supports_buttons:
                button_lines = []
                for i, btn in enumerate(message.buttons, 1):
                    btn_title = btn.get("title") or btn.get("text") or btn.get("id") or f"Opção {i}"
                    button_lines.append(f"{i}. {btn_title}")
                if button_lines:
                    body_text = (body_text + "\n\n" + "\n".join(button_lines)).strip()

            result = client.send_message_result(
                message.recipient_id,
                body_text,
                formato=(message.format or "imagem") if message.media_url else "texto",
                media_url=message.media_url,
            )
            return ChannelResult(ok=result.ok, message_id=result.message_id, error=result.error)
        except Exception as exc:
            logger.exception("[WHATSAPP_ADAPTER] Erro ao enviar: %s", exc)
            return ChannelResult(ok=False, error=str(exc))

    def parse_inbound(self, payload: dict) -> list[InboundMessage]:
        messages = []
        try:
            entry = (payload.get("entry") or [{}])[0]
            change = (entry.get("changes") or [{}])[0]
            val = change.get("value") or {}
            raw_msgs = val.get("messages") or []
            contacts = val.get("contacts") or []
            sender_name = None
            if contacts and isinstance(contacts, list):
                prof = contacts[0].get("profile") or {}
                sender_name = prof.get("name")

            for m in raw_msgs:
                from_num = m.get("from")
                m_type = m.get("type", "text")
                text = ""
                if m_type == "text":
                    text = (m.get("text") or {}).get("body", "")
                elif m_type == "interactive":
                    text = ((m.get("interactive") or {}).get("button_reply") or {}).get("title", "")
                messages.append(InboundMessage(
                    sender_id=from_num,
                    channel_type=self.channel_type,
                    text=text,
                    message_id=m.get("id"),
                    format=m_type,
                    sender_name=sender_name,
                    raw_payload=m,
                ))
        except Exception as exc:
            logger.warning("[WHATSAPP_ADAPTER] Erro no parse: %s", exc)
        return messages

    def is_configured(self) -> bool:
        try:
            import horoscope
            return horoscope._get_whatsapp_client(self.tenant_id) is not None
        except Exception:
            return False
