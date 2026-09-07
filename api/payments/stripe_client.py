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

# Compat — labels legados. Source of truth = plans.PLANS.
PLAN_LABELS = {
    "starter": "Starter — R$ 97/mês",
    "pro": "Pro — R$ 197/mês",
    "enterprise": "Enterprise — R$ 497/mês",
    "premium": "Premium — R$ 497/mês",  # alias legado
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


def price_id_for_plan(plan: str, *, billing_period: str = "monthly") -> Optional[str]:
    """
    Mapeia plan_key → Stripe Price ID.

    Resolução em ordem:
        1. plans.PLANS[plan][stripe_price_id|stripe_price_id_annual] (canonical)
        2. env var STRIPE_PRICE_{plan_upper} (legacy override)

    Usa env var como fallback pra ambientes onde plans.py tem placeholder.
    """
    plan_norm = (plan or "").strip().lower()
    try:
        import plans as plans_mod
        cfg = plans_mod.PLANS.get(plan_norm)
        if cfg:
            key = "stripe_price_id_annual" if billing_period == "annual" else "stripe_price_id"
            pid = cfg.get(key)
            # Se for placeholder ("price_starter_monthly_brl"), prefere env var
            if pid and not pid.startswith("price_") or pid and pid.startswith("price_") and not pid.startswith("price_1"):
                env_pid = os.environ.get(f"STRIPE_PRICE_{plan_norm.upper()}")
                if env_pid:
                    return env_pid
            if pid and pid.startswith("price_1"):
                return pid
    except Exception:
        pass
    return os.environ.get(f"STRIPE_PRICE_{plan_norm.upper()}") or None


def create_checkout_session(
    *,
    customer_id: Optional[str],
    customer_email: Optional[str],
    price_id: str,
    success_url: str,
    cancel_url: str,
    client_reference_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    trial_period_days: Optional[int] = None,
    coupon: Optional[str] = None,
    allow_promotion_codes: bool = True,
    locale: str = "pt-BR",
):
    """
    Cria Checkout Session em modo subscription.

    Se ``customer_id`` for None, Stripe cria customer novo no checkout
    (usando ``customer_email`` como hint).
    """
    _ensure_configured()
    sub_data = {"metadata": metadata or {}}
    if trial_period_days and trial_period_days > 0:
        sub_data["trial_period_days"] = trial_period_days

    kwargs = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": client_reference_id,
        "metadata": metadata or {},
        "subscription_data": sub_data,
        "locale": locale,
        "allow_promotion_codes": allow_promotion_codes,
        "billing_address_collection": "required",
    }
    if customer_id:
        kwargs["customer"] = customer_id
    elif customer_email:
        kwargs["customer_email"] = customer_email
    if coupon:
        kwargs["discounts"] = [{"coupon": coupon}]
    return stripe.checkout.Session.create(**kwargs)


def update_subscription_to_plan(
    subscription_id: str,
    new_price_id: str,
    *,
    proration_behavior: str = "create_prorations",
    metadata: Optional[dict] = None,
):
    """
    Faz upgrade/downgrade do plano de uma subscription existente.

    proration_behavior:
        - 'create_prorations'  → cobra/credita pro-rated imediatamente (upgrade)
        - 'none'               → muda no próximo period (downgrade default)
        - 'always_invoice'     → fecha invoice imediato
    """
    _ensure_configured()
    sub = stripe.Subscription.retrieve(subscription_id)
    items = sub.get("items", {}).get("data") or []
    if not items:
        raise RuntimeError("Subscription sem items — Stripe state inconsistent")
    current_item_id = items[0]["id"]
    return stripe.Subscription.modify(
        subscription_id,
        items=[{"id": current_item_id, "price": new_price_id}],
        proration_behavior=proration_behavior,
        metadata=metadata or {},
    )


def schedule_subscription_cancellation(subscription_id: str, at_period_end: bool = True):
    """
    Cancela subscription. Default: ao fim do período (user mantém acesso).
    `at_period_end=False` → cancela imediato (sem refund automático).
    """
    _ensure_configured()
    if at_period_end:
        return stripe.Subscription.modify(
            subscription_id, cancel_at_period_end=True,
        )
    return stripe.Subscription.delete(subscription_id)


def reactivate_subscription(subscription_id: str):
    """
    Desfaz cancel_at_period_end (user mudou de ideia antes do fim do ciclo).
    """
    _ensure_configured()
    return stripe.Subscription.modify(
        subscription_id, cancel_at_period_end=False,
    )


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
