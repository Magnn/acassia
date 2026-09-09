"""tests/test_email_sender.py — Testes do disparador de emails transacionais multi-provedor."""
from unittest.mock import MagicMock, patch
from api.utils.email_sender import (
    send_email,
    send_password_reset_email,
    is_email_service_configured,
    get_email_diagnostic_info,
)


def test_is_email_service_configured_false_by_default(monkeypatch):
    for k in ["RESEND_API_KEY", "RESEND_KEY", "SMTP_HOST", "SMTP_SERVER", "MAIL_SERVER", "SMTP_USER", "SMTP_PASS", "SENDGRID_API_KEY"]:
        monkeypatch.delenv(k, raising=False)
    assert is_email_service_configured() is False
    diag = get_email_diagnostic_info()
    assert diag["configured"] is False
    assert diag["active_provider"] == "none"


def test_is_email_service_configured_true_with_resend(monkeypatch):
    monkeypatch.setenv("RESEND_KEY", "re_123456789")
    assert is_email_service_configured() is True
    diag = get_email_diagnostic_info()
    assert diag["active_provider"] == "resend"


def test_is_email_service_configured_true_with_sendgrid(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_KEY", raising=False)
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.123456")
    assert is_email_service_configured() is True
    diag = get_email_diagnostic_info()
    assert diag["active_provider"] == "sendgrid"


def test_is_email_service_configured_true_with_flask_mail_aliases(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("RESEND_KEY", raising=False)
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.setenv("MAIL_SERVER", "smtp.sendgrid.net")
    monkeypatch.setenv("MAIL_USERNAME", "apikey")
    monkeypatch.setenv("MAIL_PASSWORD", "SG.testpass")
    assert is_email_service_configured() is True
    diag = get_email_diagnostic_info()
    assert diag["active_provider"] == "smtp"
    assert diag["smtp_host"] == "smtp.sendgrid.net"


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
