import pytest
import hashlib
import uuid
from app import app
from db.database import SessionLocal
from db.models import PublicApiKey, Lead, Sequence, SequenceStep, ContactOnSequence
from datetime import datetime, timezone

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_data(db_session):
    tenant_id = f"test_v1_{uuid.uuid4().hex[:8]}"

    # API Key
    raw_key = f"test_api_key_{uuid.uuid4().hex[:12]}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = PublicApiKey(
        tenant_id=tenant_id,
        key_hash=key_hash,
        key_prefix="mm_pk_test",
        label="Test Key",
        tier="pro",
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()

    return {
        "tenant_id": tenant_id,
        "raw_key": raw_key,
    }

def test_ping_no_auth(client):
    rv = client.get('/api/v1/ping')
    assert rv.status_code == 401
    assert "error" in rv.json

def test_ping_with_auth(client, test_data):
    rv = client.get('/api/v1/ping', headers={"X-API-Key": test_data["raw_key"]})
    assert rv.status_code == 200
    assert rv.json["ok"] is True
    assert rv.json["tenant_id"] == test_data["tenant_id"]

def test_create_and_update_contact(client, test_data):
    # Create
    payload = {
        "phone": "5511900000001",
        "name": "João",
        "tags": ["vip"],
        "custom_fields": {"empresa": "Acme"}
    }
    rv = client.post('/api/v1/contacts', json=payload, headers={"X-API-Key": test_data["raw_key"]})
    assert rv.status_code == 201
    assert rv.json["ok"] is True
    assert rv.json["created"] is True
    contact_id = rv.json["contact"]["id"]

    # Update
    payload_update = {
        "phone": "5511900000001",
        "name": "João Silva",
        "tags": ["cliente"],
        "custom_fields": {"cargo": "CEO"}
    }
    rv2 = client.post('/api/v1/contacts', json=payload_update, headers={"X-API-Key": test_data["raw_key"]})
    assert rv2.status_code == 200
    assert rv2.json["created"] is False
    assert "vip" in rv2.json["contact"]["tags"]
    assert "cliente" in rv2.json["contact"]["tags"]
    assert rv2.json["contact"]["custom_fields"]["empresa"] == "Acme"
    assert rv2.json["contact"]["custom_fields"]["cargo"] == "CEO"

def test_add_contact_tags(client, test_data, db_session):
    lead = Lead(tenant_id=test_data["tenant_id"], telefone="5511900000002", nome="Maria", tags=[])
    db_session.add(lead)
    db_session.commit()

    rv = client.post(f'/api/v1/contacts/{lead.telefone}/tags', json={"tags": ["promo"]}, headers={"X-API-Key": test_data["raw_key"]})
    assert rv.status_code == 200
    assert "promo" in rv.json["tags"]

def test_send_message_missing_data(client, test_data):
    rv = client.post('/api/v1/messages/send', json={"channel": "webchat"}, headers={"X-API-Key": test_data["raw_key"]})
    assert rv.status_code == 400

# Minimal mock for channel adapter send_message
def test_send_message_webchat(client, test_data, monkeypatch):
    class MockResult:
        def __init__(self):
            self.ok = True
            self.message_id = "test-msg-id"
            self.error = None

    class MockAdapter:
        def send_message(self, msg):
            return MockResult()
            
    def mock_get_channel_adapter(channel, tenant_id):
        return MockAdapter()

    monkeypatch.setattr("api.channels.registry.get_channel_adapter", mock_get_channel_adapter)

    rv = client.post('/api/v1/messages/send', json={
        "recipient": "5511900000003",
        "text": "Hello test",
        "channel": "webchat"
    }, headers={"X-API-Key": test_data["raw_key"]})
    
    assert rv.status_code == 200
    assert rv.json["ok"] is True
    assert rv.json["message_id"] == "test-msg-id"
