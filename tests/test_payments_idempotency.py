"""Testes da idempotência durável de eventos de pagamento."""

import pytest

from api.payments.idempotency import claim_payment_event
from db import models
from db.database import Base, SessionLocal, engine


@pytest.fixture(autouse=True)
def _reset_payment_receipts():
    """Garante que cada teste roda com tabela limpa."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(models.PaymentEventReceipt).delete()
    db.commit()
    db.close()
    yield


def test_primeiro_claim_retorna_true():
    assert claim_payment_event("stripe", "evt_first") is True


def test_segundo_claim_mesmo_evento_retorna_false():
    assert claim_payment_event("stripe", "evt_dup") is True
    assert claim_payment_event("stripe", "evt_dup") is False


def test_terceiro_e_quarto_claim_continuam_false():
    claim_payment_event("stripe", "evt_x")
    assert claim_payment_event("stripe", "evt_x") is False
    assert claim_payment_event("stripe", "evt_x") is False


def test_event_id_em_providers_diferentes_sao_distintos():
    assert claim_payment_event("stripe", "evt_shared") is True
    assert claim_payment_event("cakto",  "evt_shared") is True


def test_event_id_em_tenants_diferentes_sao_distintos():
    assert claim_payment_event("stripe", "evt_t", tenant_id="tenant_a") is True
    assert claim_payment_event("stripe", "evt_t", tenant_id="tenant_b") is True
    # mas claim repetido NO MESMO tenant é bloqueado
    assert claim_payment_event("stripe", "evt_t", tenant_id="tenant_a") is False


def test_metadata_eh_persistida():
    claim_payment_event(
        "stripe", "evt_meta",
        event_type="payment_intent.succeeded",
        raw_payload={"foo": "bar", "amount": 1990},
    )
    db = SessionLocal()
    rec = db.query(models.PaymentEventReceipt).filter_by(event_id="evt_meta").first()
    assert rec is not None
    assert rec.provider == "stripe"
    assert rec.event_type == "payment_intent.succeeded"
    assert rec.raw_payload == {"foo": "bar", "amount": 1990}
    db.close()


def test_lead_id_eh_persistido_quando_fornecido():
    claim_payment_event("cakto", "evt_lead", lead_id=12345)
    db = SessionLocal()
    rec = db.query(models.PaymentEventReceipt).filter_by(event_id="evt_lead").first()
    assert rec is not None
    assert rec.lead_id == 12345
    db.close()


def test_provider_vazio_levanta():
    with pytest.raises(ValueError, match="provider e event_id"):
        claim_payment_event("", "evt_x")


def test_event_id_vazio_levanta():
    with pytest.raises(ValueError, match="provider e event_id"):
        claim_payment_event("stripe", "")
