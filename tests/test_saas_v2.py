"""Testes consolidados das novas features SaaS: Connect, Inbox, Settings, Metrics."""

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import stripe
from flask import Flask

from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.billing import billing_bp
from api.saas.connect import connect_bp
from api.saas.inbox import inbox_bp
from api.saas.metrics import compute_kpis, metrics_bp
from api.saas.settings import _parse_cadence, settings_bp
from db import models
from db.database import Base, SessionLocal, engine as db_engine

_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.User).delete()
    db.query(models.Lead).delete()
    db.query(models.Mensagem).delete()
    db.query(models.TenantFlowVariable).delete()
    db.query(models.TenantFlowSecret).delete()
    db.commit()
    db.close()
    stripe.api_key = None
    from api import tenant_config
    tenant_config.clear_cache()
    yield


@pytest.fixture
def app() -> Flask:
    flask_app = Flask("test_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="t", TESTING=True, SERVER_NAME="localhost")
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(billing_bp)
    flask_app.register_blueprint(connect_bp)
    flask_app.register_blueprint(inbox_bp)
    flask_app.register_blueprint(settings_bp)
    flask_app.register_blueprint(metrics_bp)
    return flask_app


@pytest.fixture
def logged_in(app):
    user = signup_user("op@x.com", "senha-1234")
    client = app.test_client()
    with app.test_request_context():
        client.post("/saas/login", data={"email": "op@x.com", "password": "senha-1234"})
    return client, user


def _seed_lead(tenant_id: str, telefone: str = "5511999999999", **kwargs):
    db = SessionLocal()
    try:
        lead = models.Lead(tenant_id=tenant_id, telefone=telefone, **kwargs)
        db.add(lead)
        db.commit()
        return lead.id
    finally:
        db.close()


def _seed_msg(lead_id: int, texto: str, remetente: str = "user"):
    db = SessionLocal()
    try:
        m = models.Mensagem(
            lead_id=lead_id, remetente=remetente, texto=texto,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(m)
        db.commit()
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# CONNECT (γ)
# ─────────────────────────────────────────────────────────────────────────────

def test_connect_status_renderiza(logged_in, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    client, _ = logged_in
    res = client.get("/saas/connect/status")
    assert res.status_code == 200
    assert b"Stripe Connect" in res.data


def test_connect_status_avisa_sem_stripe(logged_in, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    stripe.api_key = None
    client, _ = logged_in
    res = client.get("/saas/connect/status")
    assert res.status_code == 200


def test_connect_onboard_sem_stripe_redireciona(logged_in, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    stripe.api_key = None
    client, _ = logged_in
    res = client.post("/saas/connect/onboard", follow_redirects=False)
    assert res.status_code == 302


def test_connect_onboard_cria_account_e_link(logged_in, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    fake_account = SimpleNamespace(id="acct_test")
    fake_link = SimpleNamespace(url="https://connect.stripe.com/setup/abc")

    with patch("api.saas.connect.stripe.Account.create", return_value=fake_account) as m_acc, \
         patch("api.saas.connect.stripe.AccountLink.create", return_value=fake_link) as m_link:
        client, user = logged_in
        res = client.post("/saas/connect/onboard", follow_redirects=False)

    assert res.status_code == 303
    assert "connect.stripe.com" in res.headers.get("Location", "")
    # account criado com country=BR e metadata.tenant_id
    assert m_acc.call_args.kwargs["country"] == "BR"
    assert m_acc.call_args.kwargs["metadata"]["tenant_id"] == user.tenant_id
    # link criado com refresh+return
    assert m_link.called


def test_connect_onboard_reusa_account_existente(logged_in, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    client, user = logged_in

    db = SessionLocal()
    try:
        db.add(models.TenantFlowVariable(
            tenant_id=user.tenant_id, key="stripe.connect_account_id", value_json="acct_existing",
        ))
        db.commit()
    finally:
        db.close()
    from api import tenant_config
    tenant_config.clear_cache()

    fake_link = SimpleNamespace(url="https://connect.stripe.com/setup/x")
    with patch("api.saas.connect.stripe.Account.create") as m_acc, \
         patch("api.saas.connect.stripe.AccountLink.create", return_value=fake_link):
        res = client.post("/saas/connect/onboard", follow_redirects=False)

    assert res.status_code == 303
    m_acc.assert_not_called()  # não cria de novo


def test_connect_return_renderiza(logged_in):
    client, _ = logged_in
    res = client.get("/saas/connect/return")
    assert res.status_code == 200
    assert "Recebemos teus dados".encode("utf-8") in res.data


def test_connect_refresh_redireciona_pra_status(logged_in):
    client, _ = logged_in
    res = client.get("/saas/connect/refresh", follow_redirects=False)
    assert res.status_code == 302


# ─────────────────────────────────────────────────────────────────────────────
# INBOX (α)
# ─────────────────────────────────────────────────────────────────────────────

def test_inbox_list_vazia(logged_in):
    client, _ = logged_in
    res = client.get("/saas/inbox/")
    assert res.status_code == 200
    assert b"Inbox" in res.data


def test_inbox_list_mostra_leads_do_tenant(logged_in):
    client, user = logged_in
    _seed_lead(user.tenant_id, "5511111111111", nome="Ana")
    _seed_lead(user.tenant_id, "5522222222222", nome="Beatriz")
    _seed_lead("outro_tenant", "5533333333333", nome="Carla")  # não deve aparecer

    res = client.get("/saas/inbox/")
    assert res.status_code == 200
    assert b"Ana" in res.data
    assert b"Beatriz" in res.data
    assert b"Carla" not in res.data


def test_inbox_filtro_convertidas(logged_in):
    client, user = logged_in
    _seed_lead(user.tenant_id, "5511111111111", nome="Ana", convertido=True)
    _seed_lead(user.tenant_id, "5522222222222", nome="Beatriz", convertido=False)

    res = client.get("/saas/inbox/?filtro=convertidas")
    assert res.status_code == 200
    assert b"Ana" in res.data
    assert b"Beatriz" not in res.data


def test_inbox_filtro_pausadas(logged_in):
    client, user = logged_in
    _seed_lead(user.tenant_id, "5511111111111", nome="Pausada", bot_pausado=True)
    _seed_lead(user.tenant_id, "5522222222222", nome="Ativa", bot_pausado=False)

    res = client.get("/saas/inbox/?filtro=pausadas")
    assert b"Pausada" in res.data
    assert b"Ativa" not in res.data


def test_inbox_conversation_renderiza(logged_in):
    client, user = logged_in
    lead_id = _seed_lead(user.tenant_id, "5511999999999", nome="Maria")
    _seed_msg(lead_id, "ola cigana")
    _seed_msg(lead_id, "oi minha querida", remetente="bot")

    res = client.get(f"/saas/inbox/{lead_id}")
    assert res.status_code == 200
    assert b"Maria" in res.data
    assert "ola cigana".encode("utf-8") in res.data
    assert "oi minha querida".encode("utf-8") in res.data


def test_inbox_conversation_lead_de_outro_tenant_404(logged_in):
    client, _ = logged_in
    other_lead_id = _seed_lead("outro_tenant", nome="X")
    res = client.get(f"/saas/inbox/{other_lead_id}")
    assert res.status_code == 404


def test_inbox_conversation_nao_existente_404(logged_in):
    client, _ = logged_in
    res = client.get("/saas/inbox/99999")
    assert res.status_code == 404


def test_inbox_takeover_alterna_bot_pausado(logged_in):
    client, user = logged_in
    lead_id = _seed_lead(user.tenant_id, nome="X", bot_pausado=False)

    res = client.post(f"/saas/inbox/{lead_id}/takeover", follow_redirects=False)
    assert res.status_code == 302

    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        assert lead.bot_pausado is True
    finally:
        db.close()

    # Toggle de novo: volta pra False
    client.post(f"/saas/inbox/{lead_id}/takeover", follow_redirects=False)
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        assert lead.bot_pausado is False
    finally:
        db.close()


def test_inbox_takeover_lead_de_outro_tenant_404(logged_in):
    client, _ = logged_in
    other_lead_id = _seed_lead("outro_tenant", nome="X")
    res = client.post(f"/saas/inbox/{other_lead_id}/takeover")
    assert res.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS (ε)
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_cadence_aceita_valores_validos():
    assert _parse_cadence("5, 60, 180") == [5, 60, 180]
    assert _parse_cadence("5") == [5]


def test_parse_cadence_rejeita_vazio():
    with pytest.raises(ValueError, match="vazia"):
        _parse_cadence("")
    with pytest.raises(ValueError, match="vazia"):
        _parse_cadence("   ")


def test_parse_cadence_rejeita_menor_que_5():
    with pytest.raises(ValueError, match="mínimo"):
        _parse_cadence("4")
    with pytest.raises(ValueError, match="mínimo"):
        _parse_cadence("5, 3, 60")


def test_parse_cadence_rejeita_acima_de_7_toques():
    with pytest.raises(ValueError, match="máximo"):
        _parse_cadence("5, 6, 7, 8, 9, 10, 11, 12")


def test_parse_cadence_rejeita_alfanumerico():
    with pytest.raises(ValueError, match="inválido"):
        _parse_cadence("5, abc, 60")


def test_settings_index_renderiza(logged_in):
    client, _ = logged_in
    res = client.get("/saas/settings/")
    assert res.status_code == 200
    assert "Cadência de recovery".encode("utf-8") in res.data


def test_settings_recovery_atualiza_cadence(logged_in):
    client, user = logged_in
    res = client.post("/saas/settings/recovery", data={"cadence_minutes": "10, 120, 360"}, follow_redirects=False)
    assert res.status_code == 302

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=user.tenant_id, key="recovery.cadence_minutes",
        ).first()
        assert v.value_json == [10, 120, 360]
    finally:
        db.close()


def test_settings_recovery_invalida_nao_grava(logged_in):
    client, user = logged_in
    res = client.post("/saas/settings/recovery", data={"cadence_minutes": "abc"}, follow_redirects=False)
    assert res.status_code == 302

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=user.tenant_id, key="recovery.cadence_minutes",
        ).first()
        assert v is None
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# METRICS (ζ)
# ─────────────────────────────────────────────────────────────────────────────

def test_compute_kpis_zerados_pra_tenant_sem_leads():
    kpis = compute_kpis("vazio")
    assert kpis["total_leads"] == 0
    assert kpis["leads_7d"] == 0
    assert kpis["convertidos"] == 0
    assert kpis["conversion_rate"] == 0


def test_compute_kpis_conta_corretamente():
    _seed_lead("t1", "5511111111111", convertido=True)
    _seed_lead("t1", "5522222222222", convertido=False)
    _seed_lead("t1", "5533333333333", convertido=True, bot_pausado=True)
    _seed_lead("t1", "5544444444444", opt_out=True)
    _seed_lead("outro", "5555555555555")  # outro tenant — não conta

    kpis = compute_kpis("t1")
    assert kpis["total_leads"] == 4
    assert kpis["convertidos"] == 2
    assert kpis["pausadas"] == 1
    assert kpis["opt_out"] == 1
    assert kpis["conversion_rate"] == 50.0


def test_compute_kpis_node_distribution():
    _seed_lead("t1", "1", node_atual="1_apresentacao")
    _seed_lead("t1", "2", node_atual="1_apresentacao")
    _seed_lead("t1", "3", node_atual="8_oferta_principal")

    kpis = compute_kpis("t1")
    nodes = {nd["node"]: nd["count"] for nd in kpis["node_distribution"]}
    assert nodes["1_apresentacao"] == 2
    assert nodes["8_oferta_principal"] == 1


def test_metrics_dashboard_renderiza(logged_in):
    client, user = logged_in
    _seed_lead(user.tenant_id, convertido=True)
    res = client.get("/saas/metrics/")
    assert res.status_code == 200
    assert "Métricas".encode("utf-8") in res.data


def test_metrics_isolamento_tenant(logged_in):
    """Tenants diferentes têm KPIs isolados."""
    client, user = logged_in
    _seed_lead(user.tenant_id, "1", convertido=True)
    _seed_lead("outro", "9", convertido=True)

    kpis_meu = compute_kpis(user.tenant_id)
    kpis_outro = compute_kpis("outro")
    assert kpis_meu["convertidos"] == 1
    assert kpis_outro["convertidos"] == 1
