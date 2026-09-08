"""Security and credential-storage tests for social webhooks."""

import hashlib
import hmac
import json
from pathlib import Path

import pytest
from flask import Flask
from cryptography.fernet import Fernet

from api.public.social_automations import social_bp
from api.saas.auth import auth_bp, login_manager, signup_user
from db import models
from db.database import Base, SessionLocal, engine as db_engine


_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_SECRET_KEY", Fernet.generate_key().decode("ascii"))
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.TenantFlowSecret).delete()
    db.query(models.TenantFlowVariable).filter(
        models.TenantFlowVariable.key.in_([
            "social.comment_rules", "tiktok.business", "youtube.integration"
        ])
    ).delete(synchronize_session=False)
    db.query(models.User).filter_by(email="social-owner@example.com").delete()
    db.commit()
    db.close()


@pytest.fixture
def configured_client():
    app = Flask("test_social_security", template_folder=_TEMPLATE_DIR)
    app.config.update(SECRET_KEY="social-test", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(social_bp)
    user = signup_user("social-owner@example.com", "senha-123456")
    client = app.test_client()
    client.post("/saas/login", data={"email": user.email, "password": "senha-123456"})
    return client, user


def test_social_credentials_are_encrypted_and_never_echoed(configured_client):
    client, user = configured_client
    response = client.post("/saas/social/rules", json={
        "rules": [],
        "credentials": {"verify_token": "verify-super-secret", "app_secret": "app-super-secret"},
    })
    assert response.status_code == 200
    assert "super-secret" not in response.get_data(as_text=True)

    db = SessionLocal()
    try:
        rows = db.query(models.TenantFlowSecret).filter_by(tenant_id=user.tenant_id).all()
        assert len(rows) == 2
        assert all(row.value_cipher.startswith("fernet:v1:") for row in rows)
        assert all("super-secret" not in row.value_cipher for row in rows)
    finally:
        db.close()


def test_meta_verification_and_post_signature_fail_closed(configured_client):
    client, user = configured_client
    client.post("/saas/social/rules", json={
        "rules": [],
        "credentials": {"verify_token": "verify-token", "app_secret": "app-secret"},
    })

    denied = client.get(
        f"/api/public/webhooks/meta-social?tenant_id={user.tenant_id}&hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=123"
    )
    assert denied.status_code == 403

    verified = client.get(
        f"/api/public/webhooks/meta-social?tenant_id={user.tenant_id}&hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=123"
    )
    assert verified.status_code == 200
    assert verified.get_data(as_text=True) == "123"

    payload = json.dumps({"entry": []}, separators=(",", ":")).encode()
    unsigned = client.post(
        f"/api/public/webhooks/meta-social?tenant_id={user.tenant_id}",
        data=payload,
        content_type="application/json",
    )
    assert unsigned.status_code == 403

    signature = "sha256=" + hmac.new(b"app-secret", payload, hashlib.sha256).hexdigest()
    accepted = client.post(
        f"/api/public/webhooks/meta-social?tenant_id={user.tenant_id}",
        data=payload,
        content_type="application/json",
        headers={"X-Hub-Signature-256": signature},
    )
    assert accepted.status_code == 200


def test_tiktok_and_youtube_secrets_are_not_stored_in_config(configured_client):
    client, user = configured_client
    tiktok = client.post("/saas/tiktok/config", json={
        "business_id": "business-1",
        "access_token": "tiktok-token",
        "webhook_secret": "tiktok-hook",
        "active": True,
    })
    youtube = client.post("/saas/youtube/config", json={
        "channel_id": "channel-1",
        "api_key": "youtube-key",
        "active": True,
    })
    assert tiktok.status_code == 200
    assert youtube.status_code == 200

    db = SessionLocal()
    try:
        variables = db.query(models.TenantFlowVariable).filter_by(tenant_id=user.tenant_id).all()
        serialized = json.dumps([row.value_json for row in variables])
        assert "tiktok-token" not in serialized
        assert "tiktok-hook" not in serialized
        assert "youtube-key" not in serialized
    finally:
        db.close()
