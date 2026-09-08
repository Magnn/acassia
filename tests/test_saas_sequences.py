"""Testes da suite SaaS Sequences (Drip Campaigns com paridade ChatbotX)."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from flask import Flask

from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.sequences import sequences_bp, process_due_sequence_steps
from db import models
from db.database import Base, SessionLocal, engine as db_engine

_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.SequenceDispatch).delete()
    db.query(models.ContactOnSequence).delete()
    db.query(models.SequenceStep).delete()
    db.query(models.Sequence).delete()
    db.query(models.Lead).delete()
    db.query(models.User).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def app() -> Flask:
    flask_app = Flask("test_sequences_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="test_sequences_key", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(sequences_bp)
    return flask_app


@pytest.fixture
def auth_client(app):
    user = signup_user("sequence_tester@acassia.com", "senha-123456")
    client = app.test_client()
    with app.test_request_context():
        client.post("/saas/login", data={"email": "sequence_tester@acassia.com", "password": "senha-123456"})
    return client, user


def test_sequence_lifecycle_and_chatbotx_parity(auth_client):
    client, user = auth_client

    # 1. Create a sequence
    res = client.post("/saas/sequences", json={
        "name": "Onboarding 7 Dias VIP",
        "folder_name": "Lançamentos 2026",
    })
    assert res.status_code == 201
    seq = res.get_json()["sequence"]
    seq_id = seq["id"]
    assert seq["name"] == "Onboarding 7 Dias VIP"
    assert seq["active"] is True

    # 2. List sequences
    res_list = client.get("/saas/sequences")
    assert res_list.status_code == 200
    seqs = res_list.get_json()["sequences"]
    assert len(seqs) == 1
    assert seqs[0]["id"] == seq_id

    # 3. Rename sequence
    res_rename = client.patch(f"/saas/sequences/{seq_id}/rename", json={"name": "Onboarding VIP Supreme"})
    assert res_rename.status_code == 200
    assert res_rename.get_json()["name"] == "Onboarding VIP Supreme"

    # 4. Add Steps
    # Step 1: Immediately / 1 hour
    res_step1 = client.post(f"/saas/sequences/{seq_id}/steps", json={
        "order": 0,
        "delay_days": 0,
        "delay_minutes": 60,
        "delay_unit": "hours",
        "message_template": "Olá {{nome}}, seja bem-vindo ao dia 1!",
    })
    assert res_step1.status_code == 201
    step1 = res_step1.get_json()["step"]
    step1_id = step1["id"]

    # Step 2: 1 day later
    res_step2 = client.post(f"/saas/sequences/{seq_id}/steps", json={
        "order": 1,
        "delay_days": 1,
        "delay_unit": "days",
        "message_template": "Olá {{nome}}, aqui está seu conteúdo do dia 2!",
    })
    assert res_step2.status_code == 201

    # 5. Detail view with steps and stats
    res_detail = client.get(f"/saas/sequences/{seq_id}")
    assert res_detail.status_code == 200
    detail = res_detail.get_json()["sequence"]
    assert detail["messages"] == 2
    assert len(detail["steps"]) == 2

    # 6. Enroll a lead
    db = SessionLocal()
    lead = models.Lead(
        tenant_id=user.tenant_id,
        nome="Cliente Sequência",
        telefone="5511977778888",
    )
    db.add(lead)
    db.commit()
    lead_id = lead.id
    db.close()

    res_enroll = client.post(f"/saas/sequences/{seq_id}/enroll", json={"lead_ids": [lead_id]})
    assert res_enroll.status_code == 200
    assert res_enroll.get_json()["enrolled_count"] == 1

    # Check enrolled contacts
    res_contacts = client.get(f"/saas/sequences/{seq_id}/contacts")
    assert res_contacts.status_code == 200
    contacts = res_contacts.get_json()["contacts"]
    assert len(contacts) == 1
    assert contacts[0]["lead_id"] == lead_id
    assert contacts[0]["current_step"] == 0
    assert contacts[0]["status"] == "active"

    # 7. Process due steps (Simulate time arrived)
    db = SessionLocal()
    enrollment = db.query(models.ContactOnSequence).filter_by(sequence_id=seq_id, lead_id=lead_id).first()
    # Force next_run_at to past so it triggers
    enrollment.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()
    db.close()

    res_due = client.post("/saas/sequences/process-due")
    assert res_due.status_code == 200
    assert res_due.get_json()["processed"] >= 1

    # Verify enrollment advanced to step 1
    db = SessionLocal()
    enrollment_after = db.query(models.ContactOnSequence).filter_by(sequence_id=seq_id, lead_id=lead_id).first()
    assert enrollment_after.current_step == 1
    db.close()

    # 8. Unenroll
    res_unenroll = client.post(f"/saas/sequences/{seq_id}/unenroll", json={"lead_id": lead_id})
    assert res_unenroll.status_code == 200

    # 9. Delete sequence
    res_del = client.delete(f"/saas/sequences/{seq_id}")
    assert res_del.status_code == 200
