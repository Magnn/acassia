"""Testes do webhook Stripe (subscription + connect events)."""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
from flask import Flask

from api.payments.stripe_webhook import stripe_webhook_bp
from db import models
from db.database import Base, SessionLocal, engine as db_engine

WEBHOOK_SECRET = "whsec_test_secret"


def _build_signature(payload_bytes: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Constrói header Stripe-Signature válido pra payload."""
    ts = int(time.time())
    signed = f"{ts}.".encode("utf-8") + payload_bytes
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _make_event(event_id: str, event_type: str, obj: dict) -> bytes:
    return json.dumps({
        "id": event_id,
        "type": event_type,
        "data": {"object": obj},
    }).encode("utf-8")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.PaymentEventReceipt).delete()
    db.query(models.TenantFlowVariable).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def app(monkeypatch) -> Flask:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", WEBHOOK_SECRET)
    flask_app = Flask("test_app")
    flask_app.config.update(SECRET_KEY="x", TESTING=True)
    flask_app.register_blueprint(stripe_webhook_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ─── Validação de signature ──────────────────────────────────────────────────

def test_sem_secret_configurado_retorna_503(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    flask_app = Flask("t")
    flask_app.config.update(SECRET_KEY="x", TESTING=True)
    flask_app.register_blueprint(stripe_webhook_bp)
    client = flask_app.test_client()

    payload = _make_event("evt_x", "checkout.session.completed", {})
    res = client.post(
        "/webhook/stripe",
        data=payload,
        headers={"Stripe-Signature": "fake"},
    )
    assert res.status_code == 503


def test_signature_invalida_retorna_400(client):
    payload = _make_event("evt_x", "checkout.session.completed", {})
    res = client.post(
        "/webhook/stripe",
        data=payload,
        headers={"Stripe-Signature": "lixo"},
    )
    assert res.status_code == 400


def test_payload_nao_json_retorna_400(client):
    payload = b"isso nao eh json"
    res = client.post(
        "/webhook/stripe",
        data=payload,
        headers={"Stripe-Signature": _build_signature(payload)},
    )
    assert res.status_code == 400


# ─── Idempotência ────────────────────────────────────────────────────────────

def test_evento_duplicado_eh_ignorado(client):
    payload = _make_event(
        "evt_dup", "checkout.session.completed",
        {"customer": "cus_x", "subscription": "sub_x", "metadata": {"tenant_id": "t1", "plan": "pro"}},
    )
    sig = _build_signature(payload)
    headers = {"Stripe-Signature": sig}

    res1 = client.post("/webhook/stripe", data=payload, headers=headers)
    assert res1.status_code == 200

    res2 = client.post("/webhook/stripe", data=payload, headers=headers)
    assert res2.status_code == 200
    assert res2.data == b"DUPLICATE"


# ─── Handler: checkout.session.completed ─────────────────────────────────────

def test_checkout_completed_salva_customer_subscription_status_active(client):
    payload = _make_event(
        "evt_c1", "checkout.session.completed",
        {
            "customer": "cus_abc",
            "subscription": "sub_abc",
            "client_reference_id": "tenant_a",
            "metadata": {"tenant_id": "tenant_a", "plan": "pro"},
        },
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        vars_ = {v.key: v.value_json for v in db.query(models.TenantFlowVariable).filter_by(tenant_id="tenant_a")}
        assert vars_["stripe.customer_id"] == "cus_abc"
        assert vars_["stripe.subscription_id"] == "sub_abc"
        assert vars_["stripe.subscription_status"] == "active"
        assert vars_["stripe.plan"] == "pro"
    finally:
        db.close()


def test_checkout_completed_usa_client_reference_se_metadata_ausente(client):
    payload = _make_event(
        "evt_c2", "checkout.session.completed",
        {
            "customer": "cus_xyz",
            "subscription": "sub_xyz",
            "client_reference_id": "tenant_via_ref",
            "metadata": {},
        },
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(
            tenant_id="tenant_via_ref", key="stripe.subscription_status"
        ).first()
        assert v is not None
    finally:
        db.close()


# ─── Handler: subscription.updated ───────────────────────────────────────────

def test_subscription_updated_atualiza_status(client):
    payload = _make_event(
        "evt_sub_up", "customer.subscription.updated",
        {"id": "sub_xyz", "status": "past_due", "metadata": {"tenant_id": "tenant_b"}},
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(
            tenant_id="tenant_b", key="stripe.subscription_status"
        ).first()
        assert v.value_json == "past_due"
    finally:
        db.close()


def test_subscription_updated_busca_tenant_via_customer_lookup(client):
    """Quando metadata não tem tenant_id, busca pelo customer_id na DB."""
    db = SessionLocal()
    try:
        db.add(models.TenantFlowVariable(
            tenant_id="tenant_lookup", key="stripe.customer_id", value_json="cus_lookup",
        ))
        db.commit()
    finally:
        db.close()

    payload = _make_event(
        "evt_lookup", "customer.subscription.updated",
        {"id": "sub_q", "status": "active", "customer": "cus_lookup", "metadata": {}},
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(
            tenant_id="tenant_lookup", key="stripe.subscription_status"
        ).first()
        assert v.value_json == "active"
    finally:
        db.close()


# ─── Handler: subscription.deleted ───────────────────────────────────────────

def test_subscription_deleted_marca_canceled(client):
    payload = _make_event(
        "evt_del", "customer.subscription.deleted",
        {"id": "sub_z", "metadata": {"tenant_id": "tenant_c"}},
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        v = db.query(models.TenantFlowVariable).filter_by(
            tenant_id="tenant_c", key="stripe.subscription_status"
        ).first()
        assert v.value_json == "canceled"
    finally:
        db.close()


# ─── Handler: account.updated (Connect) ──────────────────────────────────────

def test_account_updated_marca_payouts_enabled(client):
    payload = _make_event(
        "evt_acc", "account.updated",
        {
            "id": "acct_xyz",
            "payouts_enabled": True,
            "charges_enabled": True,
            "metadata": {"tenant_id": "tenant_d"},
        },
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200

    db = SessionLocal()
    try:
        vars_ = {v.key: v.value_json for v in db.query(models.TenantFlowVariable).filter_by(tenant_id="tenant_d")}
        assert vars_["stripe.connect_account_id"] == "acct_xyz"
        assert vars_["stripe.connect_payouts_enabled"] is True
        assert vars_["stripe.connect_charges_enabled"] is True
    finally:
        db.close()


# ─── Eventos não-tratados ────────────────────────────────────────────────────

def test_evento_nao_tratado_retorna_200(client):
    """Stripe vai mandar muitos tipos de eventos — não devemos rejeitar."""
    payload = _make_event(
        "evt_unk", "invoice.payment_succeeded",
        {"id": "in_x", "metadata": {}},
    )
    res = client.post("/webhook/stripe", data=payload, headers={"Stripe-Signature": _build_signature(payload)})
    assert res.status_code == 200


# ─── Resiliência: handler crasha, libera claim e retorna 500 para redelivery ──────

def test_handler_crash_retorna_500_e_libera_claim(client):
    """Se handler crasha, retorna 500 e libera a claim para permitir redelivery do Stripe."""
    payload = _make_event(
        "evt_crash", "checkout.session.completed",
        {"customer": "cus_x", "subscription": "sub_x", "metadata": {"tenant_id": "t1"}},
    )

    with patch("api.payments.stripe_webhook._handle_checkout_completed", side_effect=RuntimeError("boom")):
        res = client.post(
            "/webhook/stripe",
            data=payload,
            headers={"Stripe-Signature": _build_signature(payload)},
        )

    assert res.status_code == 500
    assert b"PROCESSING_ERROR" in res.data

