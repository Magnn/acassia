"""Testes da suite SaaS Contacts Import & Sync (ChatbotX Slide 5 Parity)."""

from pathlib import Path
import pytest
from flask import Flask

from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.sequences import sequences_bp
from api.saas.contacts_import import contacts_import_bp, process_contact_import_job
from unittest.mock import patch
from db import models
from db.database import Base, SessionLocal, engine as db_engine

_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.ContactImport).delete()
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
    flask_app = Flask("test_contacts_import_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="test_imports_key", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(sequences_bp)
    flask_app.register_blueprint(contacts_import_bp)
    return flask_app


@pytest.fixture
def auth_client(app):
    user = signup_user("importer_tester@acassia.com", "senha-123456")
    client = app.test_client()
    with app.test_request_context():
        client.post("/saas/login", data={"email": "importer_tester@acassia.com", "password": "senha-123456"})
    return client, user


def test_contact_import_flow(auth_client):
    client, user = auth_client

    # 1. Create a sequence first to test auto-enrollment
    res_seq = client.post("/saas/sequences", json={"name": "Sequência de Boas-Vindas"})
    assert res_seq.status_code == 201
    seq_id = res_seq.get_json()["sequence"]["id"]

    # 2. List initial imports (empty)
    res = client.get("/saas/contacts/imports")
    assert res.status_code == 200
    assert res.get_json()["imports"] == []

    # 3. Process CSV import with mapping and error handling
    payload = {
        "name": "leads_vip_evento.csv",
        "mapping": {
            "Nome Completo": "nome",
            "Whatsapp Celular": "telefone",
            "Correio Eletronico": "email",
        },
        "assigned_tags": ["vip", "abril-2026"],
        "enroll_sequence_id": seq_id,
        "rows": [
            {
                "Nome Completo": "Maria Madalena",
                "Whatsapp Celular": "11988887777",
                "Correio Eletronico": "maria@example.com",
            },
            {
                "Nome Completo": "João Batista",
                "Whatsapp Celular": "+55 (21) 97777-6666",
                "Correio Eletronico": "joao@example.com",
            },
            {
                "Nome Completo": "Sem Telefone",
                "Whatsapp Celular": "",
                "Correio Eletronico": "fail@example.com",
            },
        ],
    }
    with patch("api.utils.task_queue.enqueue_contact_import", return_value=True):
        res = client.post("/saas/contacts/imports/process", json=payload)
    assert res.status_code == 202
    data = res.get_json()
    assert data["ok"] is True
    assert data["total_rows"] == 3
    assert data["status"] == "queued"
    process_contact_import_job(data["import_id"], user.tenant_id)

    # 4. Verify in DB
    db = SessionLocal()
    try:
        leads = db.query(models.Lead).filter_by(tenant_id=user.tenant_id).all()
        assert len(leads) == 2
        maria = db.query(models.Lead).filter_by(telefone="5511988887777").first()
        assert maria is not None
        assert maria.nome == "Maria Madalena"
        assert "vip" in maria.tags

        # Verify auto-enrollment in sequence
        enrollment = db.query(models.ContactOnSequence).filter_by(
            sequence_id=seq_id, lead_id=maria.id
        ).first()
        assert enrollment is not None
        assert enrollment.status == "active"
    finally:
        db.close()

    # 5. Verify import record in list
    res = client.get("/saas/contacts/imports")
    assert res.status_code == 200
    imports = res.get_json()["imports"]
    assert len(imports) == 1
    assert imports[0]["name"] == "leads_vip_evento.csv"
    assert imports[0]["success_rows"] == 2
    assert imports[0]["failed_rows"] == 1
    assert len(imports[0]["error_log"]) == 1

    # 6. Test sync whatsapp
    res_sync = client.post("/saas/contacts/imports/sync-whatsapp")
    assert res_sync.status_code == 501
    assert res_sync.get_json()["error"] == "whatsapp_history_sync_not_supported"
