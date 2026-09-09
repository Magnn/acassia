"""
tests/test_multi_tenant_isolation.py — Matriz de Isolamento Multi-Tenant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Valida que tenants distintos (Alpha e Beta) jamais têm acesso a dados,
contatos, campanhas, sequências, links ou webhooks um do outro.
"""
from pathlib import Path
import uuid
import pytest
from flask import Flask
from db.database import SessionLocal, Base, engine as db_engine
from db import models
from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.broadcast import broadcast_bp
from api.saas.sequences import sequences_bp
from api.payments.dispatch import payments_bp
from api.saas.growth_links import growth_links_bp

_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture
def app():
    flask_app = Flask("test_isolation_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="test_isolation_key", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(flask_app)

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(broadcast_bp)
    flask_app.register_blueprint(sequences_bp)
    flask_app.register_blueprint(payments_bp)
    flask_app.register_blueprint(growth_links_bp)

    with flask_app.app_context():
        Base.metadata.create_all(bind=db_engine)
        yield flask_app


@pytest.fixture
def setup_tenants():
    # Gerar sufixo aleatório para isolar entre testes
    suffix = uuid.uuid4().hex[:6]
    u_alpha = signup_user(f"admin_alpha_{suffix}@isolation.com", "senha123456")
    u_beta = signup_user(f"admin_beta_{suffix}@isolation.com", "senha123456")

    t_alpha_id = u_alpha.tenant_id
    t_beta_id = u_beta.tenant_id

    db = SessionLocal()
    try:
        lead_alpha = models.Lead(
            tenant_id=t_alpha_id,
            nome="Contato Alpha",
            telefone="5511999990001",
        )
        db.add(lead_alpha)
        db.flush()

        camp_alpha = models.BroadcastCampaign(
            tenant_id=t_alpha_id,
            created_by_user_id=u_alpha.id,
            title="Campanha Alpha",
            message_text="Ola Alpha",
            status="draft",
        )
        db.add(camp_alpha)

        seq_alpha = models.Sequence(
            tenant_id=t_alpha_id,
            name="Sequencia Alpha",
            active=True,
        )
        db.add(seq_alpha)

        link_id = f"link_alpha_{suffix}"
        link_alpha = models.GrowthLink(
            id=link_id,
            tenant_id=t_alpha_id,
            name="Link Alpha",
            phone="5511999990001",
            wa_url="https://wa.me/5511999990001",
            short_url=f"/saas/growth/r/{link_id}",
        )
        db.add(link_alpha)

        deliv_alpha = models.PaymentDelivery(
            tenant_id=t_alpha_id,
            lead_id=lead_alpha.id,
            provider="cakto",
            event_id=f"evt_alpha_{suffix}",
            status="pending",
        )
        db.add(deliv_alpha)

        db.commit()
        db.refresh(lead_alpha)
        db.refresh(camp_alpha)
        db.refresh(seq_alpha)
        db.refresh(link_alpha)
        db.refresh(deliv_alpha)

        yield {
            "u_alpha": u_alpha,
            "u_beta": u_beta,
            "lead_alpha_id": lead_alpha.id,
            "camp_alpha_id": camp_alpha.id,
            "seq_alpha_id": seq_alpha.id,
            "link_alpha_id": link_alpha.id,
            "deliv_alpha_id": deliv_alpha.id,
            "evt_id": f"evt_alpha_{suffix}",
        }
    finally:
        db.close()


def test_tenant_beta_cannot_access_alpha_campaign(app, setup_tenants):
    client = app.test_client()
    beta_email = setup_tenants["u_beta"].email
    client.post("/saas/login", data={"email": beta_email, "password": "senha123456"})

    # Tenta obter campanha do Alpha
    camp_id = setup_tenants["camp_alpha_id"]
    res = client.get(f"/saas/broadcast/{camp_id}")
    assert res.status_code == 404

    # Tenta atualizar campanha do Alpha (PUT)
    res_put = client.put(f"/saas/broadcast/{camp_id}", json={"title": "Hacked"})
    assert res_put.status_code == 404

    # Tenta deletar campanha do Alpha
    res_del = client.delete(f"/saas/broadcast/{camp_id}")
    assert res_del.status_code == 404


def test_tenant_beta_cannot_access_alpha_sequence(app, setup_tenants):
    client = app.test_client()
    beta_email = setup_tenants["u_beta"].email
    client.post("/saas/login", data={"email": beta_email, "password": "senha123456"})

    seq_id = setup_tenants["seq_alpha_id"]
    res = client.get(f"/saas/sequences/{seq_id}")
    assert res.status_code == 404

    res_del = client.delete(f"/saas/sequences/{seq_id}")
    assert res_del.status_code == 404


def test_tenant_beta_cannot_access_alpha_payment_deliveries(app, setup_tenants):
    client = app.test_client()
    beta_email = setup_tenants["u_beta"].email
    client.post("/saas/login", data={"email": beta_email, "password": "senha123456"})

    # Listagem de deliveries como Beta não deve conter os de Alpha
    res = client.get("/saas/payments/deliveries")
    assert res.status_code == 200
    deliveries = res.get_json().get("deliveries", [])
    alpha_events = [d for d in deliveries if d["event_id"] == setup_tenants["evt_id"]]
    assert len(alpha_events) == 0

    # Retry de delivery do Alpha como Beta deve falhar com 404
    deliv_id = setup_tenants["deliv_alpha_id"]
    res_retry = client.post(f"/saas/payments/deliveries/{deliv_id}/retry")
    assert res_retry.status_code == 404
