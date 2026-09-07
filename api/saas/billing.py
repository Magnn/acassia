"""
Stripe billing — endpoints user-facing pra gerenciar assinatura.

Endpoints:
    GET  /saas/billing/plans              — lista planos (compat legacy)
    GET  /saas/billing/state              — estado atual de TenantBilling
    POST /saas/billing/checkout/<plan>    — cria Stripe Checkout Session
    POST /saas/billing/upgrade            — upgrade de plano com proration
    POST /saas/billing/downgrade          — downgrade end-of-period
    POST /saas/billing/cancel-pending     — cancela downgrade agendado
    POST /saas/billing/cancellation       — flow cancellation com survey
    POST /saas/billing/cancellation/abort — desfaz cancel_at_period_end
    POST /saas/billing/portal             — Stripe Customer Portal
    GET  /saas/billing/success            — landing pós-checkout
    GET  /saas/billing/cancel             — landing pós-cancel checkout
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from api.payments.stripe_client import (
    PLAN_LABELS,
    create_billing_portal_session,
    create_checkout_session,
    is_configured,
    price_id_for_plan,
    update_subscription_to_plan,
    schedule_subscription_cancellation,
    reactivate_subscription,
)
from db import models
from db.database import SessionLocal
import plans as plans_module

logger = logging.getLogger(__name__)

billing_bp = Blueprint("saas_billing", __name__, url_prefix="/saas/billing")


def _wants_json() -> bool:
    return request.is_json or (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    )


def _get_billing(tenant_id: str) -> models.TenantBilling | None:
    db = SessionLocal()
    try:
        return db.query(models.TenantBilling).filter_by(tenant_id=tenant_id).first()
    finally:
        db.close()


# ─── Estado ────────────────────────────────────────────────────────────


@billing_bp.route("/plans", methods=["GET"])
@login_required
def plans():
    """Compat legacy. /api/me/plan tem versão mais rica."""
    tenant_id = current_user.tenant_id
    plan_key, source = plans_module.effective_plan(tenant_id)
    billing = _get_billing(tenant_id)
    data = {
        "plan_labels": PLAN_LABELS,
        "current_status": billing.status if billing else None,
        "current_plan": plan_key,
        "current_source": source,
        "stripe_configured": is_configured(),
    }
    if _wants_json():
        return jsonify(data)
    return render_template("billing/plans.html", **data)


@billing_bp.route("/state", methods=["GET"])
@login_required
def billing_state():
    """Estado completo de TenantBilling pro frontend."""
    tenant_id = current_user.tenant_id
    plan_key, source = plans_module.effective_plan(tenant_id)
    cfg = plans_module.get_plan_config(plan_key)
    billing = _get_billing(tenant_id)

    payload = {
        "effective_plan": plan_key,
        "effective_label": cfg["label"],
        "effective_source": source,
        "effective_price_brl": cfg["price_brl"],
        "stripe_configured": is_configured(),
        "billing": None,
    }
    if billing:
        payload["billing"] = {
            "plan": billing.plan,
            "billing_period": billing.billing_period,
            "status": billing.status,
            "current_period_end": billing.current_period_end.isoformat() if billing.current_period_end else None,
            "trial_end": billing.trial_end.isoformat() if billing.trial_end else None,
            "cancel_at_period_end": bool(billing.cancel_at_period_end),
            "canceled_at": billing.canceled_at.isoformat() if billing.canceled_at else None,
            "pending_plan": billing.pending_plan,
            "pending_billing_period": billing.pending_billing_period,
            "pending_effective_at": billing.pending_effective_at.isoformat() if billing.pending_effective_at else None,
            "mrr_brl": (billing.mrr_brl_cents or 0) / 100,
            "has_subscription": bool(billing.subscription_id),
        }
    return jsonify(payload)


# ─── Checkout (novo subscriber) ────────────────────────────────────────


@billing_bp.route("/checkout/<plan>", methods=["POST"])
@login_required
def checkout(plan: str):
    """
    Cria Stripe Checkout Session pra novo subscriber.
    Body opcional: {billing_period: monthly|annual, coupon: string}
    """
    if not is_configured():
        msg = "Stripe não está configurado neste ambiente."
        if _wants_json():
            return jsonify({"error": msg}), 503
        flash(msg, "error")
        return redirect(url_for("saas_billing.plans"))

    body = request.get_json(silent=True) or {}
    billing_period = body.get("billing_period") or "monthly"
    coupon = (body.get("coupon") or "").strip() or None

    if billing_period not in ("monthly", "annual"):
        return jsonify({"error": "billing_period_invalid"}), 422

    price_id = price_id_for_plan(plan, billing_period=billing_period)
    if not price_id:
        msg = f"Plano '{plan}' ({billing_period}) não tem price_id configurado."
        if _wants_json():
            return jsonify({"error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("saas_billing.plans"))

    tenant_id = current_user.tenant_id
    billing = _get_billing(tenant_id)
    customer_id = billing.customer_id if billing else None

    # Trial 14d só pra primeira vez (signup) — se já tem TenantBilling, sem trial extra
    trial_days = None
    if not billing:
        trial_days = 14

    success = url_for("saas_billing.success", _external=True)
    cancel_url = url_for("saas_billing.cancel", _external=True)

    try:
        session = create_checkout_session(
            customer_id=customer_id,
            customer_email=current_user.email,
            price_id=price_id,
            success_url=success + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            client_reference_id=tenant_id,
            metadata={
                "tenant_id": tenant_id,
                "plan": plan,
                "billing_period": billing_period,
            },
            trial_period_days=trial_days,
            coupon=coupon,
        )
    except Exception:
        logger.exception("[billing] erro ao criar checkout session tenant=%s", tenant_id)
        msg = "Erro ao iniciar checkout. Tenta de novo em instantes."
        if _wants_json():
            return jsonify({"error": msg}), 500
        flash(msg, "error")
        return redirect(url_for("saas_billing.plans"))

    logger.info(
        "[billing.checkout] tenant=%s plan=%s period=%s session=%s",
        tenant_id, plan, billing_period, session.id,
    )

    if _wants_json():
        return jsonify({"ok": True, "url": session.url, "session_id": session.id})
    return redirect(session.url, code=303)


# ─── Self-service upgrade (Frente 2.17) ────────────────────────────────


@billing_bp.route("/upgrade", methods=["POST"])
@login_required
def upgrade():
    """
    Upgrade de plano com proration imediata.
    Body: {plan: 'pro'|'enterprise', billing_period: 'monthly'|'annual'}
    """
    body = request.get_json(silent=True) or {}
    new_plan = (body.get("plan") or "").strip().lower()
    billing_period = body.get("billing_period") or "monthly"

    if new_plan not in plans_module.PLANS:
        return jsonify({"error": "plan_invalid"}), 422
    if billing_period not in ("monthly", "annual"):
        return jsonify({"error": "billing_period_invalid"}), 422

    tenant_id = current_user.tenant_id
    billing = _get_billing(tenant_id)

    if not billing or not billing.subscription_id:
        # Sem subscription → manda pra checkout
        return jsonify({
            "error": "no_subscription",
            "redirect": url_for("saas_billing.checkout", plan=new_plan),
        }), 409

    # Validação rank: upgrade só aceita plan_rank > current
    current_plan_rank = plans_module.plan_rank(billing.plan or "free")
    new_plan_rank = plans_module.plan_rank(new_plan)
    if new_plan_rank <= current_plan_rank and not (
        billing.billing_period == "monthly" and billing_period == "annual"
    ):
        return jsonify({
            "error": "not_an_upgrade",
            "message": "Use /downgrade pra plano menor",
        }), 422

    new_price_id = price_id_for_plan(new_plan, billing_period=billing_period)
    if not new_price_id:
        return jsonify({"error": "price_not_configured"}), 503

    try:
        update_subscription_to_plan(
            billing.subscription_id,
            new_price_id,
            proration_behavior="create_prorations",
            metadata={
                "tenant_id": tenant_id,
                "plan": new_plan,
                "billing_period": billing_period,
                "upgraded_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as exc:
        logger.exception("[billing.upgrade] tenant=%s falha: %s", tenant_id, exc)
        return jsonify({"error": "stripe_error", "message": str(exc)[:200]}), 502

    # Webhook customer.subscription.updated vai sincronizar TenantBilling
    logger.info(
        "[billing.upgrade] tenant=%s %s/%s → %s/%s",
        tenant_id, billing.plan, billing.billing_period, new_plan, billing_period,
    )
    return jsonify({
        "ok": True,
        "message": "Upgrade processado — novo plano ativo. Cobranças prorated cobradas no cartão.",
    })


# ─── Self-service downgrade (Frente 2.18) ──────────────────────────────


@billing_bp.route("/downgrade", methods=["POST"])
@login_required
def downgrade():
    """
    Downgrade end-of-period: marca pending_plan, aplica no próximo ciclo.
    User mantém acesso ao plano atual até billing.current_period_end.
    """
    body = request.get_json(silent=True) or {}
    new_plan = (body.get("plan") or "").strip().lower()
    billing_period = body.get("billing_period") or "monthly"

    if new_plan not in plans_module.PLANS or new_plan == "free":
        return jsonify({"error": "plan_invalid"}), 422

    tenant_id = current_user.tenant_id
    billing = _get_billing(tenant_id)
    if not billing or not billing.subscription_id:
        return jsonify({"error": "no_subscription"}), 409

    current_rank = plans_module.plan_rank(billing.plan or "free")
    new_rank = plans_module.plan_rank(new_plan)
    if new_rank >= current_rank:
        return jsonify({
            "error": "not_a_downgrade",
            "message": "Use /upgrade pra plano maior",
        }), 422

    # Persiste pending_plan + pending_effective_at = current_period_end
    db = SessionLocal()
    try:
        billing_db = db.query(models.TenantBilling).filter_by(tenant_id=tenant_id).first()
        if not billing_db:
            return jsonify({"error": "billing_not_found"}), 404
        billing_db.pending_plan = new_plan
        billing_db.pending_billing_period = billing_period
        billing_db.pending_effective_at = billing_db.current_period_end
        db.commit()

        # Audit
        db.add(models.AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=current_user.id,
            event_type="billing.downgrade.scheduled",
            target_type="tenant_billing",
            target_id=tenant_id,
            payload={
                "from": billing.plan, "to": new_plan,
                "effective_at": billing_db.current_period_end.isoformat() if billing_db.current_period_end else None,
            },
        ))
        db.commit()
    finally:
        db.close()

    logger.info(
        "[billing.downgrade.scheduled] tenant=%s %s → %s effective_at=%s",
        tenant_id, billing.plan, new_plan,
        billing.current_period_end.isoformat() if billing.current_period_end else "?",
    )

    # Stripe: marca cancel_at_period_end=False mas atualiza price ID no fim
    # (Pra implementação completa: use Subscription Schedule. Por enquanto,
    # o cron roda em pending_effective_at e chama update_subscription_to_plan.)
    # TODO Frente 2.18: cron daily aplicando pending_plan quando current_period_end < NOW()

    return jsonify({
        "ok": True,
        "scheduled_for": billing.current_period_end.isoformat() if billing.current_period_end else None,
        "message": f"Downgrade pra {new_plan} agendado pra {billing.current_period_end.strftime('%d/%m/%Y') if billing.current_period_end else 'fim do ciclo'}.",
    })


@billing_bp.route("/cancel-pending", methods=["POST"])
@login_required
def cancel_pending_downgrade():
    """Desfaz downgrade agendado."""
    tenant_id = current_user.tenant_id
    db = SessionLocal()
    try:
        billing = db.query(models.TenantBilling).filter_by(tenant_id=tenant_id).first()
        if not billing or not billing.pending_plan:
            return jsonify({"error": "no_pending_change"}), 409
        billing.pending_plan = None
        billing.pending_billing_period = None
        billing.pending_effective_at = None
        db.commit()

        db.add(models.AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=current_user.id,
            event_type="billing.downgrade.cancelled",
            target_type="tenant_billing", target_id=tenant_id,
        ))
        db.commit()
    finally:
        db.close()
    return jsonify({"ok": True})


# ─── Cancellation flow + win-back (Frente 2.21) ───────────────────────


_VALID_CANCEL_REASONS = frozenset({
    "too_expensive", "not_using", "missing_feature",
    "switched_tool", "tech_issues", "other",
})


@billing_bp.route("/cancellation", methods=["POST"])
@login_required
def submit_cancellation():
    """
    Cancela assinatura ao fim do período + grava survey.
    Body: {reason_category, reason_text?, win_back_offered?, win_back_accepted?}
    """
    body = request.get_json(silent=True) or {}
    reason_category = (body.get("reason_category") or "").strip().lower()
    reason_text = (body.get("reason_text") or "").strip()
    win_back_offered = (body.get("win_back_offered") or "").strip() or None
    win_back_accepted = body.get("win_back_accepted")

    if reason_category and reason_category not in _VALID_CANCEL_REASONS:
        return jsonify({"error": "reason_category_invalid"}), 422

    tenant_id = current_user.tenant_id
    billing = _get_billing(tenant_id)
    if not billing or not billing.subscription_id:
        return jsonify({"error": "no_subscription"}), 409

    if win_back_accepted:
        # User aceitou oferta — NÃO cancela
        db = SessionLocal()
        try:
            survey = models.CancellationSurvey(
                tenant_id=tenant_id, user_id=current_user.id,
                reason_category=reason_category or None,
                reason_text=reason_text or None,
                win_back_offered=win_back_offered,
                win_back_accepted=True,
            )
            db.add(survey)
            db.add(models.AuditEvent(
                tenant_id=tenant_id, actor_user_id=current_user.id,
                event_type="billing.cancellation.win_back_accepted",
                target_type="tenant_billing", target_id=tenant_id,
                payload={"offer": win_back_offered, "reason": reason_category},
            ))
            db.commit()
        finally:
            db.close()
        return jsonify({"ok": True, "kept": True, "message": "Que bom que você ficou ❤️"})

    # Cancela ao fim do período
    try:
        schedule_subscription_cancellation(billing.subscription_id, at_period_end=True)
    except Exception as exc:
        logger.exception("[billing.cancellation] stripe error: %s", exc)
        return jsonify({"error": "stripe_error"}), 502

    db = SessionLocal()
    try:
        survey = models.CancellationSurvey(
            tenant_id=tenant_id, user_id=current_user.id,
            reason_category=reason_category or None,
            reason_text=reason_text or None,
            win_back_offered=win_back_offered,
            win_back_accepted=False if win_back_offered else None,
        )
        db.add(survey)

        # Marca cancel_at_period_end localmente (webhook vai confirmar)
        billing_db = db.query(models.TenantBilling).filter_by(tenant_id=tenant_id).first()
        if billing_db:
            billing_db.cancel_at_period_end = True

        db.add(models.AuditEvent(
            tenant_id=tenant_id, actor_user_id=current_user.id,
            event_type="billing.cancellation.confirmed",
            target_type="tenant_billing", target_id=tenant_id,
            payload={"reason": reason_category, "survey_id": survey.id},
        ))
        db.commit()
    finally:
        db.close()

    logger.info(
        "[billing.cancellation] tenant=%s reason=%s",
        tenant_id, reason_category,
    )
    return jsonify({
        "ok": True, "cancelled": True,
        "access_until": billing.current_period_end.isoformat() if billing.current_period_end else None,
        "message": "Sua assinatura será cancelada ao fim do ciclo. Você mantém acesso até lá.",
    })


@billing_bp.route("/cancellation/abort", methods=["POST"])
@login_required
def abort_cancellation():
    """Reativa: desfaz cancel_at_period_end."""
    tenant_id = current_user.tenant_id
    billing = _get_billing(tenant_id)
    if not billing or not billing.subscription_id:
        return jsonify({"error": "no_subscription"}), 409
    if not billing.cancel_at_period_end:
        return jsonify({"error": "not_cancelled"}), 409

    try:
        reactivate_subscription(billing.subscription_id)
    except Exception:
        logger.exception("[billing.cancellation.abort] stripe error")
        return jsonify({"error": "stripe_error"}), 502

    db = SessionLocal()
    try:
        billing_db = db.query(models.TenantBilling).filter_by(tenant_id=tenant_id).first()
        if billing_db:
            billing_db.cancel_at_period_end = False

        db.add(models.AuditEvent(
            tenant_id=tenant_id, actor_user_id=current_user.id,
            event_type="billing.cancellation.aborted",
            target_type="tenant_billing", target_id=tenant_id,
        ))
        db.commit()
    finally:
        db.close()

    return jsonify({"ok": True, "message": "Assinatura reativada"})


# ─── Customer Portal (Stripe-hosted) ───────────────────────────────────


@billing_bp.route("/portal", methods=["POST"])
@login_required
def portal():
    tenant_id = current_user.tenant_id
    billing = _get_billing(tenant_id)
    customer_id = billing.customer_id if billing else None

    if not customer_id:
        msg = "Você ainda não tem assinatura ativa."
        if _wants_json():
            return jsonify({"error": msg}), 400
        flash(msg, "error")
        return redirect(url_for("saas_billing.plans"))

    try:
        portal_session = create_billing_portal_session(
            customer_id=customer_id,
            return_url=url_for("saas_billing.plans", _external=True),
        )
    except Exception:
        logger.exception("[billing.portal] tenant=%s erro", tenant_id)
        msg = "Erro ao abrir portal."
        if _wants_json():
            return jsonify({"error": msg}), 500
        flash(msg, "error")
        return redirect(url_for("saas_billing.plans"))

    if _wants_json():
        return jsonify({"ok": True, "url": portal_session.url})
    return redirect(portal_session.url, code=303)


# ─── Landings ──────────────────────────────────────────────────────────


@billing_bp.route("/success", methods=["GET"])
@login_required
def success():
    return render_template("billing/success.html")


@billing_bp.route("/cancel", methods=["GET"])
@login_required
def cancel():
    return render_template("billing/cancel.html")
