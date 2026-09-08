"""tests/test_growth_links.py — Testes do gerador de links WhatsApp e QR Code."""
import pytest
from app import app
from db.database import SessionLocal
from db import models

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


def test_create_and_list_growth_links(client, monkeypatch):
    # Mock current_user
    class FakeUser:
        is_authenticated = True
        tenant_id = "test_growth_tenant"
        id = 999

    import flask_login.utils
    monkeypatch.setattr(flask_login.utils, "_get_user", lambda: FakeUser())

    # Create link
    payload = {
        "name": "Panfleto Feira",
        "phone": "+55 (11) 98765-4321",
        "message": "Olá! Gostaria de saber mais sobre a mentoria.",
        "tags": ["feira", "evento"],
    }
    resp = client.post("/saas/growth/links", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["ok"] is True
    link = data["link"]
    assert link["name"] == "Panfleto Feira"
    assert link["phone"] == "5511987654321"
    assert "qr_code" in link
    assert link["qr_code"].startswith("data:image/png;base64,")
    assert "https://wa.me/5511987654321" in link["wa_url"]

    # List links
    list_resp = client.get("/saas/growth/links")
    assert list_resp.status_code == 200
    links = list_resp.get_json()["links"]
    assert len(links) >= 1
    assert any(l["id"] == link["id"] for l in links)

    # Redirect tracking
    redirect_resp = client.get(f"/saas/growth/r/{link['id']}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert "wa.me" in redirect_resp.headers["Location"]

    # Delete link
    del_resp = client.delete(f"/saas/growth/links/{link['id']}")
    assert del_resp.status_code == 200
    assert del_resp.get_json()["ok"] is True


def test_redirect_growth_link_dual_read_legacy(client, db_session):
    legacy_id = "legacy_link_123"
    db_session.query(models.GrowthLink).filter_by(id=legacy_id).delete()
    db_session.query(models.TenantFlowVariable).filter_by(tenant_id="legacy_tenant", key="growth.links").delete()
    
    # Insert legacy TenantFlowVariable
    db_session.add(models.TenantFlowVariable(
        tenant_id="legacy_tenant",
        key="growth.links",
        value_json=[{
            "id": legacy_id,
            "name": "Link Legado",
            "phone": "5511999998888",
            "message": "Mensagem antiga",
            "wa_url": "https://wa.me/5511999998888?text=Mensagem",
            "short_url": "http://localhost:5000/saas/growth/r/legacy_link_123",
            "clicks": 5,
        }]
    ))
    db_session.commit()

    # Public redirect should dual-read from legacy and succeed 302
    resp = client.get(f"/saas/growth/r/{legacy_id}", follow_redirects=False)
    assert resp.status_code == 302
    assert "https://wa.me/5511999998888" in resp.headers["Location"]

    # Verify that GrowthLink row was created and click was incremented (5 + 1 = 6)
    migrated = db_session.get(models.GrowthLink, legacy_id)
    assert migrated is not None
    assert migrated.clicks == 6

