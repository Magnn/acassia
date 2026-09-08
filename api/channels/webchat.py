"""api/channels/webchat.py — Adaptador para canal Webchat."""
import logging
from datetime import datetime, timezone
from api.channels.base import ChannelAdapter, ChannelType, ChannelResult, OutboundMessage, InboundMessage
from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)

class WebchatChannelAdapter(ChannelAdapter):
    channel_type = ChannelType.WEBCHAT

    def send_message(self, message: OutboundMessage) -> ChannelResult:
        db = SessionLocal()
        try:
            lead = db.query(models.Lead).filter_by(
                tenant_id=self.tenant_id,
                telefone=message.recipient_id,
            ).first()
            if not lead:
                return ChannelResult(ok=False, error="lead_not_found")

            msg = models.Mensagem(
                lead_id=lead.id,
                remetente="assistant",
                texto=message.text,
                tipo=message.format or "texto",
                timestamp=datetime.now(timezone.utc),
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # Notificar realtime SSE
            try:
                from api.saas.realtime_hooks import notify_message_created
                notify_message_created(self.tenant_id, lead.id, {
                    "id": msg.id,
                    "texto": message.text,
                    "remetente": "assistant",
                    "timestamp": msg.timestamp.isoformat(),
                })
            except Exception:
                pass

            return ChannelResult(ok=True, message_id=str(msg.id))
        except Exception as exc:
            logger.exception("[WEBCHAT_ADAPTER] Erro: %s", exc)
            return ChannelResult(ok=False, error=str(exc))
        finally:
            db.close()

    def parse_inbound(self, payload: dict) -> list[InboundMessage]:
        text = payload.get("text", "")
        session_id = payload.get("session_id", "")
        return [InboundMessage(
            sender_id=session_id,
            channel_type=self.channel_type,
            text=text,
            raw_payload=payload,
        )] if session_id and text else []

    def is_configured(self) -> bool:
        return True
