import os

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
