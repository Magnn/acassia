"""tests/test_email_sender.py — Testes do disparador de emails transacionais."""
from unittest.mock import MagicMock, patch
from api.utils.email_sender import send_email, send_password_reset_email, is_email_service_configured


def test_is_email_service_configured_false_by_default(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    assert is_email_service_configured() is False


def test_is_email_service_configured_true_with_resend(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_123456789")
    assert is_email_service_configured() is True


def test_is_email_service_configured_true_with_smtp(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASS", "secret")
    assert is_email_service_configured() is True


def test_send_email_invalid_email():
    assert send_email("", "Assunto", "<html>corpo</html>") is False
    assert send_email("invalido", "Assunto", "<html>corpo</html>") is False


def test_send_email_via_resend(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "msg_123"}
        mock_post.return_value = mock_resp

        ok = send_password_reset_email("destino@teste.com", "http://localhost/saas/reset-password/abc")
        assert ok is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert "destino@teste.com" in call_kwargs["json"]["to"]
