"""Credential-vault and webhook authentication tests for external channels."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from flask import Flask

from api.public.telegram_webhook import telegram_bp
from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.wa_devices import devices_bp
from api.utils.tenant_secrets import decrypt_tenant_secret
from db import models
from db.database import Base, SessionLocal, engine as db_engine


_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.TenantFlowSecret).delete()
    db.query(models.WADevice).delete()
    db.query(models.User).filter(models.User.email.in_([
        "device-security@example.com", "telegram-security@example.com"
    ])).delete(synchronize_session=False)
    db.commit()
    db.close()


def _app(*blueprints):
    app = Flask("channel_security", template_folder=_TEMPLATE_DIR)
    app.config.update(SECRET_KEY="channel-security", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    for blueprint in blueprints:
        app.register_blueprint(blueprint)
    return app


def _logged_client(app, email):
    user = signup_user(email, "senha-123456")
    client = app.test_client()
    client.post("/saas/login", data={"email": email, "password": "senha-123456"})
    return client, user


def test_device_credentials_live_only_in_vault_and_are_removed_on_delete():
    client, user = _logged_client(_app(devices_bp), "device-security@example.com")
    created = client.post("/saas/devices/", json={
        "nickname": "Principal",
        "provider": "evolution",
        "evolution_instance": "instancia",
        "evolution_server_url": "https://evolution.example",
        "evolution_api_key": "evolution-super-secret",
        "meta_access_token": "meta-super-secret",
    })
    assert created.status_code == 201
    device_id = created.get_json()["device_id"]

    db = SessionLocal()
    try:
        device = db.query(models.WADevice).filter_by(id=device_id).one()
        assert device.evolution_api_key is None
        assert device.meta_access_token is None
        secrets = db.query(models.TenantFlowSecret).filter_by(tenant_id=user.tenant_id).all()
        assert len(secrets) == 2
        values = {row.key: decrypt_tenant_secret(row.value_cipher) for row in secrets}
        assert values[f"whatsapp.device.{device_id}.evolution_api_key"] == "evolution-super-secret"
        assert values[f"whatsapp.device.{device_id}.meta_access_token"] == "meta-super-secret"
    finally:
        db.close()

    updated = client.put(f"/saas/devices/{device_id}", json={"evolution_api_key": "rotated-secret"})
    assert updated.status_code == 200
    deleted = client.delete(f"/saas/devices/{device_id}")
    assert deleted.status_code == 200
    db = SessionLocal()
    try:
        assert db.query(models.TenantFlowSecret).filter_by(tenant_id=user.tenant_id).count() == 0
    finally:
        db.close()


def test_telegram_setup_requires_login_and_stores_encrypted_credentials():
    app = _app(telegram_bp)
    anonymous = app.test_client()
    assert anonymous.post("/api/webhooks/telegram/setup", json={"bot_token": "123:abc"}).status_code == 401

    client, user = _logged_client(app, "telegram-security@example.com")
    response = MagicMock(status_code=200)
    response.json.return_value = {"ok": True, "result": True}
    with patch("api.public.telegram_webhook.requests.post", return_value=response) as request_post:
        configured = client.post("/api/webhooks/telegram/setup", json={"bot_token": "123:abc"})
    assert configured.status_code == 200
    sent_body = request_post.call_args.kwargs["json"]
    assert sent_body["secret_token"]
    assert "secret_token" not in configured.get_data(as_text=True)

    db = SessionLocal()
    try:
        rows = db.query(models.TenantFlowSecret).filter_by(tenant_id=user.tenant_id).all()
        values = {row.key: decrypt_tenant_secret(row.value_cipher) for row in rows}
        assert values["telegram.bot_token"] == "123:abc"
        webhook_secret = values["telegram.webhook_secret"]
        assert all("123:abc" not in row.value_cipher for row in rows)
    finally:
        db.close()

    denied = client.post(f"/api/webhooks/telegram/{user.tenant_id}", json={})
    assert denied.status_code == 403
    accepted = client.post(
        f"/api/webhooks/telegram/{user.tenant_id}",
        json={},
        headers={"X-Telegram-Bot-Api-Secret-Token": webhook_secret},
    )
    assert accepted.status_code == 200
