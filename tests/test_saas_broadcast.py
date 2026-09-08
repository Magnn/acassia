"""Testes da suite SaaS Broadcast (Disparo em massa com paridade ChatbotX)."""

from pathlib import Path
import pytest
from flask import Flask

from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.broadcast import broadcast_bp
from db import models
from db.database import Base, SessionLocal, engine as db_engine

_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.BroadcastRecipient).delete()
    db.query(models.BroadcastCampaign).delete()
    db.query(models.Lead).delete()
    db.query(models.User).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def app() -> Flask:
    flask_app = Flask("test_broadcast_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="test_broadcast_key", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(broadcast_bp)
    return flask_app


@pytest.fixture
def auth_client(app):
    user = signup_user("broadcast_tester@acassia.com", "senha-123456")
    client = app.test_client()
    with app.test_request_context():
        client.post("/saas/login", data={"email": "broadcast_tester@acassia.com", "password": "senha-123456"})
    return client, user


def test_broadcast_lifecycle_and_chatbotx_parity(auth_client):
    client, user = auth_client

    # 1. Create a campaign
    res = client.post("/saas/broadcast", json={
        "name": "Campanha Black Friday 2026",
        "message_template": "Ola {{nome}}, confira as promocoes!",
        "anti_ban_delay_seconds": 5,
        "segment_filters": {"tag": "vip"},
    })
    assert res.status_code == 201
    camp = res.get_json()["campaign"]
    camp_id = camp["id"]
    assert camp["name"] == "Campanha Black Friday 2026"
    assert camp["status"] == "draft"

    # 2. Rename campaign
    res_rename = client.patch(f"/saas/broadcast/{camp_id}/rename", json={"name": "Campanha BF 2026 VIP"})
    assert res_rename.status_code == 200
    assert res_rename.get_json()["campaign"]["name"] == "Campanha BF 2026 VIP"

    # 3. Duplicate campaign
    res_dup = client.post(f"/saas/broadcast/{camp_id}/duplicate")
    assert res_dup.status_code == 201
    dup_camp = res_dup.get_json()["campaign"]
    assert "(Cópia)" in dup_camp["name"] or "Copia" in dup_camp["name"]
    assert dup_camp["status"] == "draft"

    # 4. Pause / Resume / Move to Draft states
    db = SessionLocal()
    campaign_db = db.query(models.BroadcastCampaign).filter_by(id=camp_id).first()
    campaign_db.status = "sending"
    db.commit()
    db.close()

    # Pause
    res_pause = client.post(f"/saas/broadcast/{camp_id}/pause")
    assert res_pause.status_code == 200
    assert res_pause.get_json()["campaign"]["status"] == "paused"

    # Resume
    res_resume = client.post(f"/saas/broadcast/{camp_id}/resume")
    assert res_resume.status_code == 200
    assert res_resume.get_json()["campaign"]["status"] == "sending"

    # Pause again and move to draft
    client.post(f"/saas/broadcast/{camp_id}/pause")
    res_draft = client.post(f"/saas/broadcast/{camp_id}/move-to-draft")
    assert res_draft.status_code == 200
    assert res_draft.get_json()["campaign"]["status"] == "draft"

    # 5. Resend failed recipients
    db = SessionLocal()
    failed_lead = models.Lead(
        tenant_id=user.tenant_id,
        telefone="5511999999999",
        nome="Fulano",
    )
    db.add(failed_lead)
    db.commit()

    rec = models.BroadcastRecipient(
        campaign_id=camp_id,
        lead_id=failed_lead.id,
        status="failed",
        error_reason="Meta timeout",
    )
    db.add(rec)
    db.commit()
    db.close()

    res_retry = client.post(f"/saas/broadcast/{camp_id}/resend-failed")
    assert res_retry.status_code == 200
    assert res_retry.get_json()["requeued_count"] == 1

    # 6. Tags endpoint
    db = SessionLocal()
    lead = models.Lead(
        tenant_id=user.tenant_id,
        telefone="5511988887777",
        nome="Cliente Tag",
        tags=["vip", "black_friday"],
    )
    db.add(lead)
    db.commit()
    db.close()

    res_tags = client.get("/saas/broadcast/tags")
    assert res_tags.status_code == 200
    tags = res_tags.get_json()["tags"]
    assert "vip" in tags
    assert "black_friday" in tags
