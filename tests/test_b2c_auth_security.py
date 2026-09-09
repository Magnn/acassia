import os
from datetime import datetime, timezone, timedelta
from flask import Flask

from api.b2c_marketplace import b2c_bp
from db import models
from db.database import Base, SessionLocal, engine


def test_consumer_vault_requires_token_and_blocks_other_consumer(monkeypatch):
    monkeypatch.setenv("B2C_TOKEN_SECRET", "test-secret-long-enough")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(models.ConsumerProfile).filter(models.ConsumerProfile.phone.in_(["55110001", "55110002"])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    app = Flask("b2c-security")
    app.config.update(TESTING=True, SECRET_KEY="test")
    app.register_blueprint(b2c_bp)
    client = app.test_client()
    one = client.post("/api/b2c/auth/signup", json={"phone": "55110001", "password": "password-123", "name": "Um"}).get_json()
    two = client.post("/api/b2c/auth/signup", json={"phone": "55110002", "password": "password-123", "name": "Dois"}).get_json()
    assert client.get(f"/api/b2c/me/{one['consumer']['id']}/vault").status_code == 401
    response = client.get(
        f"/api/b2c/me/{two['consumer']['id']}/vault",
        headers={"Authorization": f"Bearer {one['access_token']}"},
    )
    assert response.status_code == 403


def test_consumer_auth_me_and_appointments(monkeypatch):
    monkeypatch.setenv("B2C_TOKEN_SECRET", "test-secret-long-enough")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    phone = "551188880001"
    tenant_id = "tenant-expert-b2c"
    try:
        db.query(models.ConsumerProfile).filter_by(phone=phone).delete(synchronize_session=False)
        db.query(models.Appointment).filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        db.query(models.User).filter_by(tenant_id=tenant_id).delete(synchronize_session=False)
        db.commit()

        # Criar expert user
        expert = models.User(
            email="expert-b2c@test.com",
            password_hash="test-hash",
            tenant_id=tenant_id,
            is_active=True,
            name="Dra. Serena Mística",
        )
        db.add(expert)
        db.commit()
    finally:
        db.close()

    app = Flask("b2c-auth-me-test")
    app.config.update(TESTING=True, SECRET_KEY="test")
    app.register_blueprint(b2c_bp)
    client = app.test_client()

    # 1. /auth/me sem token retorna 401
    assert client.get("/api/b2c/auth/me").status_code == 401

    # 2. Cadastro de consumidor
    signup_res = client.post("/api/b2c/auth/signup", json={
        "phone": phone,
        "password": "password-secure-123",
        "name": "Maria Consumidora",
    }).get_json()
    token = signup_res["access_token"]
    consumer_id = signup_res["consumer_id"] if "consumer_id" in signup_res else signup_res["consumer"]["id"]

    # 3. /auth/me com token válido retorna dados do consumidor
    me_res = client.get("/api/b2c/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.get_json()
    assert me_data["ok"] is True
    assert me_data["consumer"]["id"] == consumer_id
    assert me_data["consumer"]["name"] == "Maria Consumidora"
    assert me_data["consumer"]["phone"] == phone

    # 4. Criar Appointment associado ao telefone do consumidor
    db = SessionLocal()
    try:
        scheduled_dt = datetime.now(timezone.utc) + timedelta(days=2)
        appt = models.Appointment(
            tenant_id=tenant_id,
            client_name="Maria Consumidora",
            client_phone=phone,
            scheduled_at=scheduled_dt,
            status="confirmed",
            appointment_type="tarot_reading",
            modality="online",
        )
        db.add(appt)
        db.commit()
    finally:
        db.close()

    # 5. /me/<id>/appointments deve retornar o agendamento unificado com nome do expert
    appts_res = client.get(
        f"/api/b2c/me/{consumer_id}/appointments",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert appts_res.status_code == 200
    appts_data = appts_res.get_json()
    assert len(appts_data["appointments"]) == 1
    first_appt = appts_data["appointments"][0]
    assert first_appt["expert_tenant_id"] == tenant_id
    assert first_appt["expert_name"] == "Dra. Serena Mística"
    assert first_appt["title"] == "tarot_reading"
    assert first_appt["status"] == "scheduled"
