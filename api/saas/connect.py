"""
Stripe Connect Express — onboarding KYC do tarólogo pra split end-user.

Endpoints:
    GET  /saas/connect/status     — mostra status do Connect (criar / reonboard / ok)
    POST /saas/connect/onboard    — cria account Express + redireciona pro Stripe KYC
    GET  /saas/connect/return     — landing após KYC (webhook account.updated faz o sync)
    GET  /saas/connect/refresh    — link expirou; refaz

Webhook ``account.updated`` está em ``api/payments/stripe_webhook.py`` —
salva ``stripe.connect_payouts_enabled`` e ``stripe.connect_charges_enabled``.
"""

from __future__ import annotations

import logging

import stripe
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from api.payments.stripe_client import _ensure_configured, is_configured
from api.tenant_config import clear_cache, get_tenant_config
from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

connect_bp = Blueprint("saas_connect", __name__, url_prefix="/saas/connect")


def _stripe_cfg(tenant_id: str) -> dict:
    cfg = get_tenant_config(tenant_id)
    return cfg.get("stripe") or {}


def _set_var(tenant_id: str, dotted_key: str, value) -> None:
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


@connect_bp.route("/status", methods=["GET"])
@login_required
def status():
    s = _stripe_cfg(current_user.tenant_id)
    return render_template(
        "connect/status.html",
        connect_account_id=s.get("connect_account_id"),
        payouts_enabled=bool(s.get("connect_payouts_enabled")),
        charges_enabled=bool(s.get("connect_charges_enabled")),
        stripe_configured=is_configured(),
    )


@connect_bp.route("/onboard", methods=["POST"])
@login_required
def onboard():
    if not is_configured():
        flash("Stripe não configurado. Defina STRIPE_SECRET_KEY no .env.", "error")
        return redirect(url_for("saas_connect.status"))

    tenant_id = current_user.tenant_id
    s = _stripe_cfg(tenant_id)
    account_id = s.get("connect_account_id")

    try:
        _ensure_configured()
        if not account_id:
            account = stripe.Account.create(
                type="express",
                country="BR",
                email=current_user.email,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                metadata={"tenant_id": tenant_id},
            )
            account_id = account.id
            _set_var(tenant_id, "stripe.connect_account_id", account_id)
            logger.info("[connect] account criado tenant=%s account=%s", tenant_id, account_id)

        link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=url_for("saas_connect.refresh", _external=True),
            return_url=url_for("saas_connect.return_landing", _external=True),
            type="account_onboarding",
        )
    except Exception:
        logger.exception("[connect] erro tenant=%s", tenant_id)
        flash("Erro ao iniciar Connect. Tente novamente em instantes.", "error")
        return redirect(url_for("saas_connect.status"))

    return redirect(link.url, code=303)


@connect_bp.route("/return", methods=["GET"])
@login_required
def return_landing():
    """User voltou do Stripe — webhook account.updated cuida do status real."""
    return render_template("connect/return.html")


@connect_bp.route("/refresh", methods=["GET"])
@login_required
def refresh():
    """Link expirou ou user clicou 'voltar' — gerar novo link."""
    return redirect(url_for("saas_connect.status"))
