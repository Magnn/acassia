"""Security contract for the public webchat widget."""

from pathlib import Path

import pytest
from flask import Flask

from api.public.webchat import webchat_bp
from api.saas.auth import auth_bp, login_manager, signup_user
from db import models
from db.database import Base, SessionLocal, engine as db_engine


_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")
_ORIGIN = "https://cliente.example"


@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    monkeypatch.setenv("WEBCHAT_SIGNING_KEY", "test-webchat-signing-key-with-enough-entropy")
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.Mensagem).delete()
    db.query(models.Lead).delete()
    db.query(models.TenantFlowVariable).filter_by(key="webchat.allowed_origins").delete()
    db.query(models.User).filter_by(email="webchat-owner@example.com").delete()
    db.commit()
    db.close()


@pytest.fixture
def app():
    flask_app = Flask("test_public_webchat", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="test-webchat-session", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(webchat_bp)
    return flask_app


@pytest.fixture
def configured_client(app):
    user = signup_user("webchat-owner@example.com", "senha-123456")
    client = app.test_client()
    client.post("/saas/login", data={"email": user.email, "password": "senha-123456"})
    response = client.put("/api/public/webchat/config", json={"allowed_origins": [_ORIGIN]})
    assert response.status_code == 200
    return client, user, response.get_json()["site_key"]


def test_init_requires_signed_site_key_and_allowed_origin(configured_client):
    client, _, site_key = configured_client

    missing = client.post("/api/public/webchat/init", json={}, headers={"Origin": _ORIGIN})
    assert missing.status_code == 401

    wrong_origin = client.post(
        "/api/public/webchat/init",
        json={"site_key": site_key},
        headers={"Origin": "https://evil.example"},
    )
    assert wrong_origin.status_code == 403
    assert "Access-Control-Allow-Origin" not in wrong_origin.headers

    valid = client.post(
        "/api/public/webchat/init",
        json={"site_key": site_key, "name": "Visitante"},
        headers={"Origin": _ORIGIN},
    )
    assert valid.status_code == 200
    payload = valid.get_json()
    assert payload["session_id"].startswith("web_")
    assert payload["session_token"]
    assert valid.headers["Access-Control-Allow-Origin"] == _ORIGIN


def test_session_token_binds_tenant_and_session(configured_client, monkeypatch):
    client, user, site_key = configured_client
    notifications = []
    monkeypatch.setattr(
        "api.saas.realtime_hooks.notify_message_created",
        lambda tenant_id, lead_id, payload: notifications.append((tenant_id, lead_id, payload)),
    )
    initialized = client.post(
        "/api/public/webchat/init",
        json={"site_key": site_key},
        headers={"Origin": _ORIGIN},
    ).get_json()

    rejected = client.post(
        "/api/public/webchat/message",
        json={"text": "Olá", "session_token": initialized["session_token"] + "x"},
        headers={"Origin": _ORIGIN},
    )
    assert rejected.status_code == 401

    accepted = client.post(
        "/api/public/webchat/message",
        json={"text": "Olá", "session_token": initialized["session_token"]},
        headers={"Origin": _ORIGIN},
    )
    assert accepted.status_code == 200

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(
            tenant_id=user.tenant_id, telefone=initialized["session_id"]
        ).one()
        assert db.query(models.Mensagem).filter_by(lead_id=lead.id, remetente="user").count() == 1
        assert notifications[0][0] == user.tenant_id
        assert notifications[0][1] == lead.id
    finally:
        db.close()


def test_config_rejects_insecure_remote_origin(configured_client):
    client, _, _ = configured_client
    response = client.put(
        "/api/public/webchat/config",
        json={"allowed_origins": ["http://cliente.example"]},
    )
    assert response.status_code == 422
    assert response.get_json()["error"] == "invalid_origin"
