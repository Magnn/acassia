"""
Webhook Stripe — processa eventos de Subscriptions, Invoices e Connect.

Source-of-truth: TenantBilling table (Frente 2.16).
Idempotência durável via payment_event_receipts (Frente 1).

Eventos processados:
- ``checkout.session.completed``         → ativa assinatura SaaS (mode=subscription)
- ``customer.subscription.created``      → cria/sync TenantBilling
- ``customer.subscription.updated``      → sync status, plan, periods, cancel_at_period_end
- ``customer.subscription.deleted``      → status=canceled
- ``customer.subscription.trial_will_end`` → notifica D-3 trial Stripe
- ``invoice.payment_succeeded``          → limpa dunning + audit
- ``invoice.payment_failed``             → start dunning
- ``account.updated`` (Connect)          → marca payouts_enabled

Plan inference: usa Price ID → match em plans.py PLANS via stripe_price_id.

Cada evento processado é também gravado em AuditEvent pra rastreabilidade.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from flask import Blueprint, request

from api.payments.idempotency import claim_payment_event
from api.payments.signatures import verify_stripe_signature
from api.tenant_config import clear_cache
from db import models
from db.database import SessionLocal
import plans as plans_module

logger = logging.getLogger(__name__)

stripe_webhook_bp = Blueprint("stripe_webhook", __name__)


@stripe_webhook_bp.route("/webhook/stripe", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not secret:
        logger.error("[stripe_webhook] STRIPE_WEBHOOK_SECRET não configurado — rejeitando")
        return "WEBHOOK_NOT_CONFIGURED", 503

    if not verify_stripe_signature(payload, sig_header, secret):
        logger.warning("[stripe_webhook] assinatura inválida")
        return "INVALID_SIGNATURE", 400

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        return "INVALID_JSON", 400

    event_id = event.get("id") or ""
    event_type = event.get("type") or ""
    obj = (event.get("data") or {}).get("object") or {}

    tenant_id = _extract_tenant_id(event_type, obj)

    # Idempotência durável
    is_first = claim_payment_event(
        provider="stripe",
        event_id=event_id,
        tenant_id=tenant_id or "default",
        event_type=event_type,
        raw_payload=event,
    )
    if not is_first:
        logger.info("[stripe_webhook] duplicata ignorada event=%s", event_id)
        return "DUPLICATE", 200

    try:
        if event_type == "checkout.session.completed":
            _handle_checkout_completed(obj, event_id)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            _handle_subscription_upsert(obj, event_id)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(obj, event_id)
        elif event_type == "customer.subscription.trial_will_end":
            _handle_trial_will_end(obj, event_id)
        elif event_type == "invoice.payment_succeeded":
            _handle_invoice_succeeded(obj, event_id)
        elif event_type == "invoice.payment_failed":
            _handle_invoice_failed(obj, event_id)
        elif event_type == "account.updated":
            _handle_connect_account_updated(obj)
        else:
            logger.info("[stripe_webhook] event_type=%s não tratado (ack)", event_type)
    except Exception:
        logger.exception("[stripe_webhook] erro processando %s", event_type)
        # 200 mesmo: idempotency já foi reivindicada, evita reprocessamento.
        return "PROCESSED_WITH_ERROR", 200

    return "OK", 200


# ─── Helpers ──────────────────────────────────────────────────────────


def _extract_tenant_id(_event_type: str, obj: dict) -> str:
    """
    Resolve tenant_id de um payload Stripe via:
    - metadata.tenant_id (Subscription, Checkout Session)
    - client_reference_id (Checkout Session)
    - customer → lookup TenantBilling.customer_id
    """
    metadata = obj.get("metadata") or {}
    if metadata.get("tenant_id"):
        return metadata["tenant_id"]
    if obj.get("client_reference_id"):
        return obj["client_reference_id"]
    customer_id = obj.get("customer")
    if customer_id:
        tid = _tenant_id_by_customer(customer_id)
        if tid:
            return tid
    return "default"


def _tenant_id_by_customer(customer_id: str) -> Optional[str]:
    db = SessionLocal()
    try:
        billing = db.query(models.TenantBilling).filter_by(customer_id=customer_id).first()
        if billing:
            return billing.tenant_id
        # Fallback: legacy KV variables (compat)
        for v in db.query(models.TenantFlowVariable).filter_by(key="stripe.customer_id").all():
            if v.value_json == customer_id:
                return v.tenant_id
        return None
    finally:
        db.close()


def _ts_to_dt(ts: Any) -> Optional[datetime]:
    """Stripe envia Unix epoch — converte pra datetime aware."""
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _plan_from_price_id(price_id: str) -> Optional[str]:
    """Mapeia Stripe Price ID de volta pra plan_key via plans.PLANS."""
    if not price_id:
        return None
    for plan_key, cfg in plans_module.PLANS.items():
        if cfg.get("stripe_price_id") == price_id:
            return plan_key
        if cfg.get("stripe_price_id_annual") == price_id:
            return plan_key
    return None


def _billing_period_from_price_id(price_id: str) -> Optional[str]:
    """Detecta se o price_id é monthly ou annual."""
    if not price_id:
        return None
    for cfg in plans_module.PLANS.values():
        if cfg.get("stripe_price_id_annual") == price_id:
            return "annual"
        if cfg.get("stripe_price_id") == price_id:
            return "monthly"
    return None


def _upsert_billing(tenant_id: str, **patch) -> models.TenantBilling:
    """UPSERT em TenantBilling — atualiza campos passados em kwargs."""
    db = SessionLocal()
    try:
        billing = db.query(models.TenantBilling).filter_by(tenant_id=tenant_id).first()
        if not billing:
            billing = models.TenantBilling(tenant_id=tenant_id)
            db.add(billing)
        for k, v in patch.items():
            setattr(billing, k, v)
        billing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(billing)
        return billing
    finally:
        db.close()


def _audit(tenant_id: str, event_type: str, payload: dict) -> None:
    """Grava AuditEvent (silencioso em falha)."""
    try:
        db = SessionLocal()
        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=None,
                event_type=event_type,
                target_type="stripe",
                target_id=payload.get("id", ""),
                payload=payload,
            ))
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("[stripe_webhook.audit] falha: %s", exc)


def _set_dunning(tenant_id: str, status: Optional[str], attempts: int = 0) -> None:
    """Atualiza users.dunning_status."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(tenant_id=tenant_id).first()
        if user:
            user.dunning_status = status
            user.dunning_attempts = attempts
            db.commit()
    finally:
        db.close()


def _set_legacy_kv(tenant_id: str, key: str, value: Any) -> None:
    """Compat: ainda escreve em KV pra clientes que dependam."""
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=key,
        ).first()
        if existing:
            existing.value_json = value
        else:
            db.add(models.TenantFlowVariable(
                tenant_id=tenant_id, key=key, value_json=value,
            ))
        db.commit()
    finally:
        db.close()
    clear_cache(tenant_id)


# ─── Handlers ─────────────────────────────────────────────────────────


def _handle_checkout_completed(session: dict, event_id: str) -> None:
    """Ativação inicial: Stripe Checkout completou."""
    tenant_id = (session.get("metadata") or {}).get("tenant_id") or session.get("client_reference_id") or "default"
    customer_id = session.get("customer") or ""
    subscription_id = session.get("subscription") or ""
    plan_meta = (session.get("metadata") or {}).get("plan") or ""

    patch = {
        "customer_id": customer_id or None,
        "subscription_id": subscription_id or None,
        "status": "active",
    }
    if plan_meta:
        patch["plan"] = plan_meta

    _upsert_billing(tenant_id, **patch)

    # Compat KV
    if customer_id:
        _set_legacy_kv(tenant_id, "stripe.customer_id", customer_id)
    if subscription_id:
        _set_legacy_kv(tenant_id, "stripe.subscription_id", subscription_id)
        _set_legacy_kv(tenant_id, "stripe.subscription_status", "active")
    if plan_meta:
        _set_legacy_kv(tenant_id, "stripe.plan", plan_meta)

    _audit(tenant_id, "stripe.checkout.completed", {
        "id": event_id, "subscription_id": subscription_id, "plan": plan_meta,
    })
    logger.info(
        "[stripe_webhook] checkout completed tenant=%s plan=%s sub=%s",
        tenant_id, plan_meta, subscription_id,
    )


def _handle_subscription_upsert(sub: dict, event_id: str) -> None:
    """Sincroniza TenantBilling com Stripe subscription state."""
    tenant_id = _extract_tenant_id("customer.subscription.updated", sub)
    items = (sub.get("items") or {}).get("data") or []
    price_id = items[0].get("price", {}).get("id") if items else None
    plan_key = _plan_from_price_id(price_id or "")
    billing_period = _billing_period_from_price_id(price_id or "")

    # MRR cents — usa price unit_amount (em cents da currency, ex: BRL 19700 = R$197)
    unit_amount = items[0].get("price", {}).get("unit_amount", 0) if items else 0
    if billing_period == "annual" and unit_amount:
        # Stripe annual price é total; MRR mensal = total/12
        mrr_cents = int(unit_amount / 12)
    else:
        mrr_cents = int(unit_amount or 0)

    patch = {
        "subscription_id": sub.get("id"),
        "customer_id": sub.get("customer"),
        "price_id": price_id,
        "plan": plan_key,
        "billing_period": billing_period,
        "status": sub.get("status"),
        "trial_start": _ts_to_dt(sub.get("trial_start")),
        "trial_end": _ts_to_dt(sub.get("trial_end")),
        "current_period_start": _ts_to_dt(sub.get("current_period_start")),
        "current_period_end": _ts_to_dt(sub.get("current_period_end")),
        "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
        "canceled_at": _ts_to_dt(sub.get("canceled_at")),
        "mrr_brl_cents": mrr_cents,
    }
    _upsert_billing(tenant_id, **patch)

    # Compat KV
    if sub.get("status"):
        _set_legacy_kv(tenant_id, "stripe.subscription_status", sub["status"])
    if plan_key:
        _set_legacy_kv(tenant_id, "stripe.plan", plan_key)

    # Se status voltou pra "active", limpa dunning
    if sub.get("status") == "active":
        _set_dunning(tenant_id, None, 0)

    _audit(tenant_id, "stripe.subscription.updated", {
        "id": event_id, "subscription_id": sub.get("id"),
        "status": sub.get("status"), "plan": plan_key,
        "cancel_at_period_end": sub.get("cancel_at_period_end"),
    })
    logger.info(
        "[stripe_webhook] subscription upsert tenant=%s plan=%s status=%s cape=%s",
        tenant_id, plan_key, sub.get("status"), sub.get("cancel_at_period_end"),
    )


def _handle_subscription_deleted(sub: dict, event_id: str) -> None:
    """Cancelamento total — tenant volta pra free."""
    tenant_id = _extract_tenant_id("customer.subscription.deleted", sub)
    _upsert_billing(
        tenant_id,
        status="canceled",
        canceled_at=datetime.now(timezone.utc),
        cancel_at_period_end=False,
    )
    _set_legacy_kv(tenant_id, "stripe.subscription_status", "canceled")
    _audit(tenant_id, "stripe.subscription.deleted", {"id": event_id})
    logger.info("[stripe_webhook] subscription canceled tenant=%s", tenant_id)


def _handle_trial_will_end(sub: dict, event_id: str) -> None:
    """Stripe envia D-3 antes do trial expirar."""
    tenant_id = _extract_tenant_id("customer.subscription.trial_will_end", sub)
    trial_end = _ts_to_dt(sub.get("trial_end"))
    _audit(tenant_id, "stripe.trial.will_end", {
        "id": event_id, "trial_end": trial_end.isoformat() if trial_end else None,
    })
    # TODO Frente 7.25: send email "trial expira em 3 dias"


def _handle_invoice_succeeded(inv: dict, event_id: str) -> None:
    """Pagamento OK — limpa dunning + audit + record affiliate commission."""
    tenant_id = _extract_tenant_id("invoice.payment_succeeded", inv)
    amount = inv.get("amount_paid", 0)
    _set_dunning(tenant_id, None, 0)
    _audit(tenant_id, "stripe.invoice.succeeded", {
        "id": event_id, "amount_paid": amount, "invoice_id": inv.get("id"),
    })

    # Affiliate commission (Frente 7.15)
    # Stripe amounts vêm em centavos da currency (BRL → BRL cents == BRL cents)
    try:
        db = SessionLocal()
        try:
            user = db.query(models.User).filter_by(tenant_id=tenant_id).first()
            if user:
                from api.saas.affiliate import record_referral_payment
                record_referral_payment(user.id, int(amount))
        finally:
            db.close()
    except Exception as exc:
        logger.debug("[stripe.affiliate] record_referral_payment falhou: %s", exc)

    logger.info(
        "[stripe_webhook] invoice succeeded tenant=%s amount=%s",
        tenant_id, amount,
    )


def _handle_invoice_failed(inv: dict, event_id: str) -> None:
    """Pagamento falhou — start dunning."""
    tenant_id = _extract_tenant_id("invoice.payment_failed", inv)
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(tenant_id=tenant_id).first()
        if user:
            attempts = (user.dunning_attempts or 0) + 1
            user.dunning_status = "past_due"
            user.dunning_attempts = attempts
            db.commit()
    finally:
        db.close()

    _audit(tenant_id, "stripe.invoice.failed", {
        "id": event_id, "invoice_id": inv.get("id"),
        "amount_due": inv.get("amount_due", 0),
        "next_payment_attempt": _ts_to_dt(inv.get("next_payment_attempt")).isoformat()
            if inv.get("next_payment_attempt") else None,
    })
    logger.warning(
        "[stripe_webhook] invoice failed tenant=%s — dunning iniciado", tenant_id,
    )


def _handle_connect_account_updated(account: dict) -> None:
    """Connect Express: KYC concluído."""
    tenant_id = (account.get("metadata") or {}).get("tenant_id") or "default"
    payouts_enabled = bool(account.get("payouts_enabled"))
    charges_enabled = bool(account.get("charges_enabled"))
    _set_legacy_kv(tenant_id, "stripe.connect_account_id", account.get("id") or "")
    _set_legacy_kv(tenant_id, "stripe.connect_payouts_enabled", payouts_enabled)
    _set_legacy_kv(tenant_id, "stripe.connect_charges_enabled", charges_enabled)
    logger.info(
        "[stripe_webhook] connect updated tenant=%s payouts=%s charges=%s",
        tenant_id, payouts_enabled, charges_enabled,
    )
