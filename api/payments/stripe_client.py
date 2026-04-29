"""
Wrapper do SDK Stripe — leitura preguiçosa de credenciais via env.

**Nunca** colocar chave Stripe (sk_live_*, sk_test_*) em código. Use ``.env``
ou secret manager. O ``.env`` está em ``.gitignore`` neste projeto.

Variáveis de ambiente esperadas:
    STRIPE_SECRET_KEY        — sk_live_... ou sk_test_...
    STRIPE_WEBHOOK_SECRET    — whsec_... (validação de signature)
    STRIPE_PRICE_STARTER     — price_... pro plano Starter R$97/mês
    STRIPE_PRICE_PRO         — price_... pro plano Pro R$297/mês
    STRIPE_PRICE_PREMIUM     — price_... pro plano Premium R$497/mês
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import stripe

logger = logging.getLogger(__name__)

PLAN_LABELS = {
    "starter": "Starter — R$ 97/mês",
    "pro": "Pro — R$ 297/mês",
    "premium": "Premium — R$ 497/mês",
}


def _ensure_configured() -> None:
    """Configura ``stripe.api_key`` na primeira chamada (lazy)."""
    if stripe.api_key:
        return
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError(
            "STRIPE_SECRET_KEY não configurado. Defina no .env (gitignored) ou via secret manager."
        )
    stripe.api_key = key


def is_configured() -> bool:
    """Retorna True se a chave Stripe está disponível."""
    return bool(stripe.api_key or os.environ.get("STRIPE_SECRET_KEY"))


def price_id_for_plan(plan: str) -> Optional[str]:
    """Mapeia ``starter|pro|premium`` → Price ID do Stripe (configurado em .env)."""
    plan = (plan or "").strip().lower()
    if plan not in PLAN_LABELS:
        return None
    return os.environ.get(f"STRIPE_PRICE_{plan.upper()}") or None


def create_checkout_session(
    *,
    customer_id: Optional[str],
    customer_email: Optional[str],
    price_id: str,
    success_url: str,
    cancel_url: str,
    client_reference_id: Optional[str] = None,
    metadata: Optional[dict] = None,
):
    """
    Cria Checkout Session em modo subscription.

    Se ``customer_id`` for None, Stripe cria customer novo no checkout
    (usando ``customer_email`` como hint).
    """
    _ensure_configured()
    kwargs = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": client_reference_id,
        "metadata": metadata or {},
        "subscription_data": {"metadata": metadata or {}},
    }
    if customer_id:
        kwargs["customer"] = customer_id
    elif customer_email:
        kwargs["customer_email"] = customer_email
    return stripe.checkout.Session.create(**kwargs)


def create_billing_portal_session(*, customer_id: str, return_url: str):
    """Cria portal session pra cliente gerenciar assinatura/cartão/cancelamento."""
    _ensure_configured()
    return stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )


def construct_event_from_payload(payload_bytes: bytes, sig_header: str, webhook_secret: str):
    """
    Valida signature e parseia evento Stripe — atalho do SDK que combina ambos.

    Usar em alternativa a ``verify_stripe_signature`` quando se quer o objeto
    Event do SDK (typed access) ao invés de só validar.
    """
    _ensure_configured()
    return stripe.Webhook.construct_event(payload_bytes, sig_header, webhook_secret)
