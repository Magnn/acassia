from flask import Flask

from api.saas import checkout_webhooks
from db import models
from db.database import SessionLocal


class _ImmediateThread:
    def __init__(self, target, args=(), kwargs=None, **_options):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}

    def start(self):
        self.target(*self.args, **self.kwargs)


class _FlowEngineSpy:
    def __init__(self):
        self.calls = []

    def processar_evento_fluxo(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def test_checkout_purchase_dispatches_published_flow_event(monkeypatch):
    tenant_id = "tenant-checkout-flow-test"
    engine_spy = _FlowEngineSpy()
    app = Flask("checkout-flow-test")
    app.config.update(SECRET_KEY="test", TESTING=True)
    app.register_blueprint(checkout_webhooks.checkout_bp)
    app.extensions["flow_engine"] = engine_spy
    monkeypatch.setattr(checkout_webhooks.threading, "Thread", _ImmediateThread)

    payload = {
        "event": "PURCHASE_APPROVED",
        "data": {
            "buyer": {
                "name": "Bia",
                "email": "bia@example.com",
                "checkout_phone": "92999999999",
            },
            "product": {"id": 77, "name": "Consulta"},
            "purchase": {"price": {"value": 149.9}, "payment": {"type": "PIX"}},
        },
    }

    response = app.test_client().post(
        f"/saas/checkout/webhook/{tenant_id}/hotmart",
        json=payload,
    )

    assert response.status_code == 200
    assert len(engine_spy.calls) == 1
    args, kwargs = engine_spy.calls[0]
    assert args[1] == "purchase_approved"
    assert args[2]["platform"] == "hotmart"
    assert args[2]["product"] == "Consulta"
    assert kwargs == {"tenant_id": tenant_id}

    db = SessionLocal()
    try:
        lead_id = args[0]
        db.query(models.ConversionEvent).filter_by(tenant_id=tenant_id).delete()
        db.query(models.CheckoutWebhookEvent).filter_by(tenant_id=tenant_id).delete()
        db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).delete()
        db.commit()
    finally:
        db.close()
