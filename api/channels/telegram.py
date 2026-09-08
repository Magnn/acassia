"""api/channels/telegram.py — Adaptador para canal Telegram."""
import logging
import requests
from api.channels.base import (
    ChannelAdapter,
    ChannelCapabilities,
    ChannelType,
    ChannelResult,
    OutboundMessage,
    InboundMessage,
)
from db.database import SessionLocal
from db import models
from api.utils.tenant_secrets import decrypt_tenant_secret

logger = logging.getLogger(__name__)

class TelegramChannelAdapter(ChannelAdapter):
    channel_type = ChannelType.TELEGRAM

    def get_capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_buttons=True,
            supports_media=True,
            supports_templates=False,
            supports_reactions=False,
            supports_audio=True,
            supports_markdown=True,
        )

    def _get_token(self) -> str:
        db = SessionLocal()
        try:
            sec = db.query(models.TenantFlowSecret).filter_by(
                tenant_id=self.tenant_id, key="telegram.bot_token"
            ).first()
            if sec and sec.value_cipher:
                return decrypt_tenant_secret(sec.value_cipher, allow_plaintext_legacy=True)
            return ""
        finally:
            db.close()

    def send_message(self, message: OutboundMessage) -> ChannelResult:
        token = self._get_token()
        if not token:
            return ChannelResult(ok=False, error="telegram_token_not_configured")

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": message.recipient_id,
                "text": message.text,
                "parse_mode": "HTML",
            }, timeout=10)
            data = resp.json()
            if data.get("ok"):
                msg_id = str(data.get("result", {}).get("message_id", ""))
                return ChannelResult(ok=True, message_id=msg_id, raw=data)
            return ChannelResult(ok=False, error=data.get("description", "telegram_error"), raw=data)
        except Exception as exc:
            logger.exception("[TELEGRAM_ADAPTER] Erro ao enviar: %s", exc)
            return ChannelResult(ok=False, error=str(exc))

    def parse_inbound(self, payload: dict) -> list[InboundMessage]:
        messages = []
        msg = payload.get("message") or payload.get("channel_post")
        if msg:
            chat = msg.get("chat") or {}
            sender_id = str(chat.get("id", ""))
            text = msg.get("text", "")
            first_name = (msg.get("from") or {}).get("first_name", "")
            if sender_id and text:
                messages.append(InboundMessage(
                    sender_id=sender_id,
                    channel_type=self.channel_type,
                    text=text,
                    message_id=str(msg.get("message_id", "")),
                    sender_name=first_name,
                    raw_payload=payload,
                ))
        return messages

    def is_configured(self) -> bool:
        return bool(self._get_token())
