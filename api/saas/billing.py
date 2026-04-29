"""
Stripe Subscriptions — assinatura SaaS do tarólogo (R$97-497/mês).

Endpoints:
    GET  /saas/billing/plans              — seletor de plano
    POST /saas/billing/checkout/{plan}    — cria Checkout Session, redirect Stripe
    GET  /saas/billing/success            — landing pós-pagamento (webhook que faz o trabalho real)
    GET  /saas/billing/cancel             — landing se user cancelar
    POST /saas/billing/portal             — Customer Portal pra gerenciar assinatura

Webhook efetivo está em ``api/payments/stripe_webhook.py``.
"""

from __future__ import annotations

import logging

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from api.payments.stripe_client import (
    PLAN_LABELS,
    create_billing_portal_session,
    create_checkout_session,
    is_configured,
    price_id_for_plan,
)
from api.tenant_config import clear_cache, get_tenant_config
from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

billing_bp = Blueprint("saas_billing", __name__, url_prefix="/saas/billing")


def _stripe_var(tenant_id: str, key: str):
    cfg = get_tenant_config(tenant_id)
    stripe_cfg = cfg.get("stripe") or {}
    return stripe_cfg.get(key)


def _set_var(tenant_id: str, dotted_key: str, value) -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFlowVariable).filter_by(
            tenant_id=tenant_id, key=dotted_key
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


# ─── Endpoints ───────────────────────────────────────────────────────────────


@billing_bp.route("/plans", methods=["GET"])
@login_required
def plans():
    """Seletor de plano. Renderiza template com 3 cards."""
    tenant_id = current_user.tenant_id
    current_status = _stripe_var(tenant_id, "subscription_status")
    return render_template(
        "billing/plans.html",
        plan_labels=PLAN_LABELS,
        current_status=current_status,
        stripe_configured=is_configured(),
    )


@billing_bp.route("/checkout/<plan>", methods=["POST"])
@login_required
def checkout(plan: str):
    if not is_configured():
        flash("Stripe não está configurado neste ambiente.", "error")
        return redirect(url_for("saas_billing.plans"))

    price_id = price_id_for_plan(plan)
    if not price_id:
        flash(f"Plano '{plan}' não tem price_id configurado.", "error")
        return redirect(url_for("saas_billing.plans"))

    tenant_id = current_user.tenant_id
    customer_id = _stripe_var(tenant_id, "customer_id")

    success = url_for("saas_billing.success", _external=True)
    cancel = url_for("saas_billing.cancel", _external=True)

    try:
        session = create_checkout_session(
            customer_id=customer_id,
            customer_email=current_user.email,
            price_id=price_id,
            success_url=success,
            cancel_url=cancel,
            client_reference_id=tenant_id,
            metadata={"tenant_id": tenant_id, "plan": plan},
        )
    except Exception:
        logger.exception("[billing] erro ao criar checkout session tenant=%s", tenant_id)
        flash("Erro ao iniciar checkout. Tenta de novo em instantes.", "error")
        return redirect(url_for("saas_billing.plans"))

    return redirect(session.url, code=303)


@billing_bp.route("/success", methods=["GET"])
@login_required
def success():
    """
    Landing pós-pagamento. O trabalho real (atualizar tenant) acontece no
    webhook ``checkout.session.completed`` — esta página só dá feedback visual.
    """
    return render_template("billing/success.html")


@billing_bp.route("/cancel", methods=["GET"])
@login_required
def cancel():
    return render_template("billing/cancel.html")


@billing_bp.route("/portal", methods=["POST"])
@login_required
def portal():
    """Customer Portal — user gerencia cartão, troca plano, cancela."""
    tenant_id = current_user.tenant_id
    customer_id = _stripe_var(tenant_id, "customer_id")
    if not customer_id:
        flash("Você ainda não tem assinatura ativa.", "error")
        return redirect(url_for("saas_billing.plans"))

    try:
        portal_session = create_billing_portal_session(
            customer_id=customer_id,
            return_url=url_for("saas_billing.plans", _external=True),
        )
    except Exception:
        logger.exception("[billing] erro ao criar portal session tenant=%s", tenant_id)
        flash("Erro ao abrir portal de cobrança.", "error")
        return redirect(url_for("saas_billing.plans"))

    return redirect(portal_session.url, code=303)
