import pytest
from unittest.mock import patch, MagicMock

from api.channels.base import ChannelType, OutboundMessage, ChannelResult
from api.channels.registry import get_channel_adapter, list_supported_channels
from api.channels.whatsapp import WhatsAppChannelAdapter
from api.channels.webchat import WebchatChannelAdapter
from api.channels.telegram import TelegramChannelAdapter

def test_registry_returns_correct_adapter():
    assert isinstance(get_channel_adapter("whatsapp", "tenant_1"), WhatsAppChannelAdapter)
    assert isinstance(get_channel_adapter("webchat", "tenant_1"), WebchatChannelAdapter)
    assert isinstance(get_channel_adapter("telegram", "tenant_1"), TelegramChannelAdapter)
    with pytest.raises(ValueError, match="unsupported_channel"):
        get_channel_adapter("invalid_channel", "tenant_1")
    assert "whatsapp" in list_supported_channels()
    assert "telegram" in list_supported_channels()
    assert "instagram" not in list_supported_channels()

def test_parse_inbound_whatsapp():
    adapter = WhatsAppChannelAdapter("tenant_1")
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"profile": {"name": "Test User"}}],
                    "messages": [{
                        "from": "5511999999999",
                        "id": "wamid.123",
                        "type": "text",
                        "text": {"body": "Hello"}
                    }]
                }
            }]
        }]
    }
    msgs = adapter.parse_inbound(payload)
    assert len(msgs) == 1
    assert msgs[0].sender_id == "5511999999999"
    assert msgs[0].text == "Hello"
    assert msgs[0].sender_name == "Test User"
    assert msgs[0].channel_type == ChannelType.WHATSAPP

def test_parse_inbound_telegram():
    adapter = TelegramChannelAdapter("tenant_1")
    payload = {
        "message": {
            "message_id": 42,
            "from": {"first_name": "John"},
            "chat": {"id": 12345},
            "text": "Hi Telegram"
        }
    }
    msgs = adapter.parse_inbound(payload)
    assert len(msgs) == 1
    assert msgs[0].sender_id == "12345"
    assert msgs[0].text == "Hi Telegram"
    assert msgs[0].sender_name == "John"
    assert msgs[0].channel_type == ChannelType.TELEGRAM

@patch("api.channels.whatsapp.horoscope")
def test_send_message_whatsapp(mock_horoscope):
    mock_client = MagicMock()
    mock_client.enviar_mensagem.return_value = True
    mock_horoscope._get_whatsapp_client.return_value = mock_client
    
    adapter = WhatsAppChannelAdapter("tenant_1")
    out = OutboundMessage(recipient_id="5511999999999", text="Hello")
    res = adapter.send_message(out)
    
    assert res.ok is True
    mock_client.enviar_mensagem.assert_called_once_with("5511999999999", "Hello", formato="texto")

@patch("api.channels.webchat.SessionLocal")
def test_send_message_webchat(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_lead = MagicMock()
    mock_lead.id = 1
    mock_db.query().filter_by().first.return_value = mock_lead
    
    adapter = WebchatChannelAdapter("tenant_1")
    out = OutboundMessage(recipient_id="5511999999999", text="Hello Webchat")
    
    with patch("api.saas.realtime_hooks.notify_message_created") as mock_notify:
        res = adapter.send_message(out)
        
    assert res.ok is True
    assert mock_db.add.called
    assert mock_db.commit.called
