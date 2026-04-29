"""
Webhook Stripe — processa eventos de Subscriptions e Connect.

Combina:
- ``signatures.verify_stripe_signature`` pra validar header (G4)
- ``idempotency.claim_payment_event`` pra deduplicação durável (G4)
- ``stripe_client`` pro SDK

Eventos processados:
- ``checkout.session.completed``         → ativa assinatura SaaS (mode=subscription)
- ``customer.subscription.updated``      → sincroniza status (active/past_due/canceled)
- ``customer.subscription.deleted``      → desativa
- ``account.updated``                    → Connect Express: marca payouts_enabled

Todos os outros eventos são logged + 200 OK (Stripe espera ack rápido).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from flask import Blueprint, request

from api.payments.idempotency import claim_payment_event
from api.payments.signatures import verify_stripe_signature
from api.tenant_config import clear_cache
from db import models
from db.database import SessionLocal

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

    # Idempotência durável: rejeitamos retries do Stripe pro mesmo event_id
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
            _handle_checkout_completed(obj)
        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            _handle_subscription_updated(obj)
        elif event_type == "customer.subscription.deleted":
            _handle_subscription_deleted(obj)
        elif event_type == "account.updated":
            _handle_connect_account_updated(obj)
        else:
            logger.info("[stripe_webhook] event_type=%s não tratado (ack)", event_type)
    except Exception:
        logger.exception("[stripe_webhook] erro processando %s", event_type)
        # NÃO retornar 500 — Stripe vai reprocessar. Idempotência já foi reivindicada.
        return "PROCESSED_WITH_ERROR", 200

    return "OK", 200


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _extract_tenant_id(_event_type: str, obj: dict) -> str:
    """
    Tenta extrair tenant_id do payload em vários locais que o Stripe usa:
    - metadata.tenant_id (Subscription, Checkout Session)
    - client_reference_id (Checkout Session)
    - metadata.tenant_id em customer (linkado via customer_id lookup local)

    ``_event_type`` reservado pra customização futura por tipo de evento.
    """
    metadata = obj.get("metadata") or {}
    if metadata.get("tenant_id"):
        return metadata["tenant_id"]
    if obj.get("client_reference_id"):
        return obj["client_reference_id"]
    # Fallback: lookup via customer_id se temos a var
    customer_id = obj.get("customer")
    if customer_id:
        return _tenant_id_by_customer(customer_id) or "default"
    return "default"


def _tenant_id_by_customer(customer_id: str) -> str | None:
    """
    Procura tenant que tem ``stripe.customer_id == customer_id``.

    Coluna JSON não suporta filter_by com valor cru (compara forma serializada).
    Carregamos todos os entries de ``stripe.customer_id`` e comparamos em Python
    após deserialização. N é pequeno (1 por tenant).
    """
    db = SessionLocal()
    try:
        for v in db.query(models.TenantFlowVariable).filter_by(key="stripe.customer_id").all():
            if v.value_json == customer_id:
                return v.tenant_id
        return None
    finally:
        db.close()


def _set_tenant_var(tenant_id: str, dotted_key: str, value: Any) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=dotted_key,
        ).first()
        if existing:
            existing.value_json = value
        else:
            db.add(models.TenantFlowVariable(
                tenant_id=tenant_id, key=dotted_key, value_json=value,
            ))
        db.commit()
    finally:
        db.close()
    clear_cache(tenant_id)


# ─── Handlers por tipo de evento ────────────────────────────────────────────


def _handle_checkout_completed(session: dict) -> None:
    """Ativação inicial da assinatura: Stripe Checkout terminou com sucesso."""
    tenant_id = (session.get("metadata") or {}).get("tenant_id") or session.get("client_reference_id") or "default"
    customer_id = session.get("customer") or ""
    subscription_id = session.get("subscription") or ""
    plan = (session.get("metadata") or {}).get("plan") or ""

    if customer_id:
        _set_tenant_var(tenant_id, "stripe.customer_id", customer_id)
    if subscription_id:
        _set_tenant_var(tenant_id, "stripe.subscription_id", subscription_id)
    if plan:
        _set_tenant_var(tenant_id, "stripe.plan", plan)
    _set_tenant_var(tenant_id, "stripe.subscription_status", "active")
    logger.info(
        "[stripe_webhook] checkout completed tenant=%s plan=%s subscription=%s",
        tenant_id, plan, subscription_id,
    )


def _handle_subscription_updated(subscription: dict) -> None:
    """Atualização de status (active → past_due → canceled etc)."""
    tenant_id = _extract_tenant_id("customer.subscription.updated", subscription)
    status = subscription.get("status") or ""
    _set_tenant_var(tenant_id, "stripe.subscription_status", status)
    _set_tenant_var(tenant_id, "stripe.subscription_id", subscription.get("id") or "")
    logger.info("[stripe_webhook] subscription updated tenant=%s status=%s", tenant_id, status)


def _handle_subscription_deleted(subscription: dict) -> None:
    """Cancelamento total — tenant perde acesso (mas dados ficam por 30d antes de deletar)."""
    tenant_id = _extract_tenant_id("customer.subscription.deleted", subscription)
    _set_tenant_var(tenant_id, "stripe.subscription_status", "canceled")
    logger.info("[stripe_webhook] subscription canceled tenant=%s", tenant_id)


def _handle_connect_account_updated(account: dict) -> None:
    """
    Connect Express: KYC concluído → ``payouts_enabled=true``.
    (Endpoint de criação do account vem em batch separado — ver connect.py futuro.)
    """
    tenant_id = (account.get("metadata") or {}).get("tenant_id") or "default"
    payouts_enabled = bool(account.get("payouts_enabled"))
    charges_enabled = bool(account.get("charges_enabled"))
    _set_tenant_var(tenant_id, "stripe.connect_account_id", account.get("id") or "")
    _set_tenant_var(tenant_id, "stripe.connect_payouts_enabled", payouts_enabled)
    _set_tenant_var(tenant_id, "stripe.connect_charges_enabled", charges_enabled)
    logger.info(
        "[stripe_webhook] connect updated tenant=%s payouts=%s charges=%s",
        tenant_id, payouts_enabled, charges_enabled,
    )
