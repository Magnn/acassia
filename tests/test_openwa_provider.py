"""
tests/test_openwa_provider.py — Testes unitários do Provider OpenWA (wa-automate)
"""

from unittest.mock import patch, MagicMock
from api.whatsapp_providers.base import ProviderMode, SendResult
from api.whatsapp_providers.openwa import (
    OpenWAProvider,
    _normalize_openwa_jid,
    pop_last_openwa_msg_id,
)
from api.whatsapp_providers.factory import get_provider_for_tenant


def test_normalize_openwa_jid():
    assert _normalize_openwa_jid("5511999998888") == "5511999998888@c.us"
    assert _normalize_openwa_jid("+55 (11) 99999-8888") == "5511999998888@c.us"
    assert _normalize_openwa_jid("12036302@g.us") == "12036302@g.us"
    assert _normalize_openwa_jid("user@c.us") == "user@c.us"
    assert _normalize_openwa_jid("") == ""


def test_openwa_text_send():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
            "openwa_api_key": "secret_key_123",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"messageId": "openwa_msg_999"}'
    mock_resp.json.return_value = {"messageId": "openwa_msg_999"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        result = provider.send_message_result("5511999998888", "Olá via OpenWA!")
        assert result.ok is True
        assert result.message_id == "openwa_msg_999"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://openwa.test:3000/api/sessao_1/send-message"
        assert kwargs["json"] == {
            "to": "5511999998888@c.us",
            "text": "Olá via OpenWA!",
        }
        assert kwargs["headers"]["x-api-key"] == "secret_key_123"


def test_openwa_audio_ptt_send():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.text = '{"id": "openwa_voice_123"}'
    mock_resp.json.return_value = {"id": "openwa_voice_123"}

    with patch("requests.post", return_value=mock_resp) as mock_post:
        ok = provider.enviar_mensagem(
            "5511999998888",
            "https://cdn.meumisterio.com/audio/leitura.mp3",
            formato="audio",
        )
        assert ok is True
        assert pop_last_openwa_msg_id() == "openwa_voice_123"
        args, kwargs = mock_post.call_args
        assert args[0] == "http://openwa.test:3000/api/sessao_1/send-voice"
        assert kwargs["json"]["ptt"] is True
        assert kwargs["json"]["url"] == "https://cdn.meumisterio.com/audio/leitura.mp3"


def test_openwa_status_connected():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"status": "CONNECTED"}'
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"status": "CONNECTED"}

    with patch("requests.get", return_value=mock_resp):
        st = provider.status()
        assert st["ok"] is True
        assert st["connection_state"] == "open"
        assert st["mode"] == "openwa"


def test_openwa_status_conflict_detection():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"status": "CONFLICT", "message": "WhatsApp Web opened in another tab"}'
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"status": "CONFLICT", "message": "WhatsApp Web opened in another tab"}

    with patch("requests.get", return_value=mock_resp):
        st = provider.status()
        assert st["ok"] is False
        assert st["connection_state"] == "CONFLICT"
        assert "Conflito de Sessão" in st["hint"]


def test_openwa_simulate_presence():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("requests.post", return_value=mock_resp) as mock_post:
        ok = provider.simulate_presence("5511999998888", presence="recording")
        assert ok is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://openwa.test:3000/api/sessao_1/simulate-typing"
        assert kwargs["json"]["presence"] == "recording"
        assert kwargs["json"]["on"] is True


def test_openwa_qr_code_json():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"base64": "data:image/png;base64,ABCDEF=="}'
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"base64": "data:image/png;base64,ABCDEF=="}

    with patch("requests.get", return_value=mock_resp):
        res = provider.get_qr_code()
        assert res.ok is True
        assert res.raw["base64"] == "data:image/png;base64,ABCDEF=="


def test_openwa_restart_session():
    provider = OpenWAProvider(
        tenant_id="tenant_teste",
        config={
            "openwa_server_url": "http://openwa.test:3000",
            "openwa_session_id": "sessao_1",
        },
    )

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("requests.post", return_value=mock_resp) as mock_post:
        ok = provider.restart_session()
        assert ok is True
        mock_post.assert_called_once()
        args, _ = mock_post.call_args
        assert args[0] == "http://openwa.test:3000/api/sessao_1/restart"


def test_factory_resolves_openwa():
    with patch("api.tenant_config.get_tenant_config", return_value={
        "whatsapp": {
            "provider": "openwa",
            "openwa": {
                "server_url": "http://openwa.local:3000",
                "session_id": "tenant_1",
                "api_key": "my_secret",
            }
        }
    }):
        prov = get_provider_for_tenant("tenant_1")
        assert isinstance(prov, OpenWAProvider)
        assert prov.mode == ProviderMode.OPENWA
        assert prov.server_url == "http://openwa.local:3000"
        assert prov.session_id == "tenant_1"
        assert prov.api_key == "my_secret"
