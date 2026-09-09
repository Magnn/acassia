"""
tests/test_devices_conflict.py — Testes de gerenciamento de dispositivos OpenWA e detecção de conflitos de sessão
"""

from unittest.mock import patch, MagicMock
from flask import Flask
from db.database import SessionLocal
from db import models


def test_device_status_conflict_detection():
    db = SessionLocal()
    tenant_id = "tenant_conflict_test"
    try:
        # Limpa dispositivos anteriores deste tenant
        db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()
        dev = models.WADevice(
            tenant_id=tenant_id,
            nickname="Dispositivo Conflito",
            provider="openwa",
            openwa_server_url="http://openwa.test:3000",
            openwa_session_id="session_conflict",
            connected=True,
            connection_state="open",
            active=True,
        )
        db.add(dev)
        db.commit()
        db.refresh(dev)
        dev_id = dev.id

        mock_user = MagicMock()
        mock_user.tenant_id = tenant_id

        # Simula provider retornando CONFLICT no status
        mock_provider = MagicMock()
        mock_provider.status.return_value = {
            "ok": False,
            "mode": "openwa",
            "connection_state": "CONFLICT",
            "hint": "Conflito detectado",
        }

        with patch("flask_login.utils._get_user", return_value=mock_user):
            with patch("api.saas.wa_devices._get_provider_for_device", return_value=mock_provider):
                from api.saas.wa_devices import device_status
                app = Flask(__name__)
                with app.test_request_context():
                    response = device_status(dev_id)
                    data = response.get_json()
                    assert data["ok"] is False
                    assert data["connected"] is False
                    assert data["connection_state"] == "CONFLICT"
                    assert data["is_conflict"] is True

        # Verifica persistência no banco
        db.expire_all()
        dev_db = db.query(models.WADevice).filter_by(id=dev_id).first()
        assert dev_db.connected is False
        assert dev_db.connection_state == "CONFLICT"
    finally:
        db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()
        db.commit()
        db.close()


def test_device_restart_endpoint():
    db = SessionLocal()
    tenant_id = "tenant_restart_test"
    try:
        db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()
        dev = models.WADevice(
            tenant_id=tenant_id,
            nickname="Dispositivo Restart",
            provider="openwa",
            connected=False,
            connection_state="CONFLICT",
            active=True,
        )
        db.add(dev)
        db.commit()
        db.refresh(dev)
        dev_id = dev.id

        mock_user = MagicMock()
        mock_user.tenant_id = tenant_id

        mock_provider = MagicMock()
        mock_provider.restart_session.return_value = True

        with patch("flask_login.utils._get_user", return_value=mock_user):
            with patch("api.saas.wa_devices._get_provider_for_device", return_value=mock_provider):
                from api.saas.wa_devices import restart_device
                app = Flask(__name__)
                with app.test_request_context():
                    response = restart_device(dev_id)
                    data = response.get_json()
                    assert data["ok"] is True
                    mock_provider.restart_session.assert_called_once()

        db.expire_all()
        dev_db = db.query(models.WADevice).filter_by(id=dev_id).first()
        assert dev_db.connection_state == "connecting"
    finally:
        db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()
        db.commit()
        db.close()


def test_wa_group_buttons_text_fallback():
    db = SessionLocal()
    tenant_id = "tenant_group_fallback_test"
    try:
        db.query(models.WAGroup).filter_by(tenant_id=tenant_id).delete()
        db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()

        dev = models.WADevice(
            tenant_id=tenant_id,
            nickname="Dev OpenWA",
            provider="openwa",
            connected=True,
            is_primary=True,
            active=True,
        )
        db.add(dev)
        db.flush()

        group = models.WAGroup(
            tenant_id=tenant_id,
            device_id=dev.id,
            group_jid="120363029999@g.us",
            name="Grupo Teste",
        )
        db.add(group)
        db.commit()
        group_id = group.id

        mock_user = MagicMock()
        mock_user.tenant_id = tenant_id

        mock_provider = MagicMock()
        mock_provider.enviar_mensagem.return_value = True

        with patch("flask_login.utils._get_user", return_value=mock_user):
            with patch("api.saas.wa_devices._get_provider_for_device", return_value=mock_provider):
                from api.saas.wa_groups import send_button_message
                app = Flask(__name__)
                with app.test_request_context(
                    json={
                        "type": "reply_buttons",
                        "header": "Aviso Especial",
                        "body": "Escolha uma das opções abaixo:",
                        "footer": "Sibila Tarot",
                        "buttons": [
                            {"id": "sim", "title": "Quero participar"},
                            {"id": "nao", "title": "Agora não"},
                        ],
                    }
                ):
                    response = send_button_message(group_id)
                    data = response.get_json()
                    assert data["ok"] is True
                    assert data["fallback"] is True
                    assert data["provider"] == "openwa"
                    mock_provider.enviar_mensagem.assert_called_once()
                    _, args, kwargs = mock_provider.enviar_mensagem.mock_calls[0]
                    sent_jid, sent_text = args[0], args[1]
                    assert sent_jid == "120363029999@g.us"
                    assert "*Aviso Especial*" in sent_text
                    assert "Escolha uma das opções abaixo:" in sent_text
                    assert "1️⃣ Quero participar" in sent_text
                    assert "2️⃣ Agora não" in sent_text
                    assert "_Sibila Tarot_" in sent_text
    finally:
        db.query(models.WAGroupMessage).filter_by(tenant_id=tenant_id).delete()
        db.query(models.WAGroup).filter_by(tenant_id=tenant_id).delete()
        db.query(models.WADevice).filter_by(tenant_id=tenant_id).delete()
        db.commit()
        db.close()

