"""Testes do módulo Stripe Subscriptions (billing)."""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import stripe
from flask import Flask

from api.payments.stripe_client import (
    PLAN_LABELS,
    is_configured,
    price_id_for_plan,
)
from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.billing import billing_bp
from db import models
from db.database import Base, SessionLocal, engine as db_engine

_TEMPLATE_DIR = str(Path(__file__).resolve().parent.parent / "templates")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.User).delete()
    db.query(models.TenantFlowVariable).delete()
    db.query(models.TenantBilling).delete()
    db.commit()
    db.close()
    # Resetar stripe.api_key entre testes
    stripe.api_key = None
    yield


@pytest.fixture
def app() -> Flask:
    flask_app = Flask("test_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        SERVER_NAME="localhost",
    )
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(billing_bp)
    return flask_app


@pytest.fixture
def logged_in_client(app):
    user = signup_user("tarologo@x.com", "senha-1234", "Maria")
    client = app.test_client()
    with app.test_request_context():
        client.post("/saas/login", data={"email": "tarologo@x.com", "password": "senha-1234"})
    return client, user


# ─── stripe_client funções puras ─────────────────────────────────────────────

def test_plan_labels_tem_3_planos():
    assert set(PLAN_LABELS.keys()) == {"starter", "pro", "enterprise", "premium"}


def test_price_id_for_plan_le_env(monkeypatch):
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_test_starter")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_test_pro")
    assert price_id_for_plan("starter") == "price_test_starter"
    assert price_id_for_plan("pro") == "price_test_pro"


def test_price_id_for_plan_invalido_retorna_none():
    assert price_id_for_plan("nao_existe") is None
    assert price_id_for_plan("") is None


def test_price_id_for_plan_sem_env_retorna_none(monkeypatch):
    monkeypatch.delenv("STRIPE_PRICE_STARTER", raising=False)
    assert price_id_for_plan("starter") is None


def test_is_configured_true_com_env(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    assert is_configured() is True


def test_is_configured_false_sem_env(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert is_configured() is False


# ─── Endpoint /plans ─────────────────────────────────────────────────────────

def test_plans_renderiza_3_planos(logged_in_client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    client, _ = logged_in_client
    res = client.get("/saas/billing/plans")
    assert res.status_code == 200
    assert b"Starter" in res.data
    assert b"Pro" in res.data
    assert b"Premium" in res.data


def test_plans_avisa_sem_stripe_configured(logged_in_client, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    stripe.api_key = None
    client, _ = logged_in_client
    res = client.get("/saas/billing/plans")
    assert res.status_code == 200
    assert b"STRIPE_SECRET_KEY" in res.data


def test_plans_sem_login_redireciona(app):
    client = app.test_client()
    res = client.get("/saas/billing/plans", follow_redirects=False)
    assert res.status_code == 302
    assert "/saas/login" in res.headers.get("Location", "")


# ─── Endpoint /checkout/<plan> ───────────────────────────────────────────────

def test_checkout_sem_stripe_configured_redireciona(logged_in_client, monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    client, _ = logged_in_client
    res = client.post("/saas/billing/checkout/starter", follow_redirects=False)
    assert res.status_code == 302
    # redireciona pra plans
    assert "/saas/billing/plans" in res.headers.get("Location", "")


def test_checkout_plano_invalido_redireciona(logged_in_client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_test_starter")
    client, _ = logged_in_client
    res = client.post("/saas/billing/checkout/inexistente", follow_redirects=False)
    assert res.status_code == 302


def test_checkout_sem_price_id_redireciona(logged_in_client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.delenv("STRIPE_PRICE_STARTER", raising=False)
    client, _ = logged_in_client
    res = client.post("/saas/billing/checkout/starter", follow_redirects=False)
    assert res.status_code == 302


def test_checkout_caminho_feliz_redireciona_pra_stripe(logged_in_client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_test_starter")

    fake_session = SimpleNamespace(url="https://checkout.stripe.com/c/xyz", id="sess_fake_123")
    with patch("api.saas.billing.create_checkout_session", return_value=fake_session) as m:
        client, user = logged_in_client
        res = client.post("/saas/billing/checkout/starter", follow_redirects=False)

    assert res.status_code == 303
    assert "checkout.stripe.com" in res.headers.get("Location", "")
    # Conferir args da sessão
    kwargs = m.call_args.kwargs
    assert kwargs["price_id"] == "price_test_starter"
    assert kwargs["client_reference_id"] == user.tenant_id
    assert kwargs["metadata"]["tenant_id"] == user.tenant_id
    assert kwargs["metadata"]["plan"] == "starter"


def test_checkout_falha_no_stripe_volta_pra_plans(logged_in_client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_test_starter")
    with patch("api.saas.billing.create_checkout_session", side_effect=RuntimeError("boom")):
        client, _ = logged_in_client
        res = client.post("/saas/billing/checkout/starter", follow_redirects=False)
    assert res.status_code == 302
    assert "/saas/billing/plans" in res.headers.get("Location", "")


# ─── Endpoint /portal ────────────────────────────────────────────────────────

def test_portal_sem_customer_id_redireciona(logged_in_client):
    client, _ = logged_in_client
    res = client.post("/saas/billing/portal", follow_redirects=False)
    assert res.status_code == 302


def test_portal_com_customer_id_redireciona_pro_stripe(logged_in_client, monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_xxx")
    client, user = logged_in_client

    db = SessionLocal()
    try:
        db.add(models.TenantFlowVariable(
            tenant_id=user.tenant_id, key="stripe.customer_id", value_json="cus_test_xxx",
        ))
        db.add(models.TenantBilling(
            tenant_id=user.tenant_id,
            plan="starter",
            billing_period="monthly",
            status="active",
            customer_id="cus_test_xxx"
        ))
        db.commit()
    finally:
        db.close()

    fake_session = SimpleNamespace(url="https://billing.stripe.com/portal/abc")
    with patch("api.saas.billing.create_billing_portal_session", return_value=fake_session) as m:
        from api.tenant_config import clear_cache
        clear_cache()  # invalida cache pra ler customer_id recém-inserido
        res = client.post("/saas/billing/portal", follow_redirects=False)

    assert res.status_code == 303
    assert "billing.stripe.com" in res.headers.get("Location", "")
    assert m.call_args.kwargs["customer_id"] == "cus_test_xxx"


# ─── Páginas de feedback ─────────────────────────────────────────────────────

def test_success_renderiza(logged_in_client):
    client, _ = logged_in_client
    res = client.get("/saas/billing/success")
    assert res.status_code == 200
    assert "Assinatura ativada".encode("utf-8") in res.data


def test_cancel_renderiza(logged_in_client):
    client, _ = logged_in_client
    res = client.get("/saas/billing/cancel")
    assert res.status_code == 200
    assert "Pagamento cancelado".encode("utf-8") in res.data
