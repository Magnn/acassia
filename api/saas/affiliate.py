"""
Affiliate program endpoints (Frente 7.15).

Endpoints:
    GET  /saas/affiliate/me              — meu link de afiliado + métricas
    POST /saas/affiliate/enroll          — vira afiliado
    PATCH /saas/affiliate/me             — atualiza pix_key
    GET  /saas/affiliate/referrals       — lista de referrals
    GET  /saas/affiliate/payouts         — histórico de payouts
    GET  /r/<ref_code>                   — landing público (track + redirect)

Lógica:
    - User vira afiliado → recebe ref_code (8 chars)
    - Visitor com ?ref=XXX → cookie 30d salva ref_code
    - Signup com cookie → cria Referral linkado ao Affiliate
    - Webhook Stripe payment.succeeded → recompute commission
    - Cron mensal → calcula payouts pendentes
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, request, make_response
from flask_login import current_user, login_required
from sqlalchemy import func

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
affiliate_bp = Blueprint("saas_affiliate", __name__, url_prefix="/saas/affiliate")
referral_bp = Blueprint("referral_track", __name__)


COMMISSION_TIERS = {
    "standard": {"pct": 30, "min_active": 0},
    "silver": {"pct": 40, "min_active": 10},
    "gold": {"pct": 50, "min_active": 50},
}


def _calc_tier(active_referrals: int) -> str:
    if active_referrals >= 50:
        return "gold"
    if active_referrals >= 10:
        return "silver"
    return "standard"


def _generate_ref_code() -> str:
    """8-char alphanumeric code, único."""
    db = SessionLocal()
    try:
        for _ in range(20):
            code = secrets.token_hex(4).upper()
            if not db.query(models.Affiliate).filter_by(ref_code=code).first():
                return code
        raise RuntimeError("falha gerando ref_code único")
    finally:
        db.close()


# ─── Endpoints ─────────────────────────────────────────────────────────


@affiliate_bp.route("/me", methods=["GET"])
@login_required
def my_affiliate():
    """Retorna info do afiliado atual ou null se não cadastrado."""
    db = SessionLocal()
    try:
        aff = db.query(models.Affiliate).filter_by(user_id=current_user.id).first()
        if not aff:
            return jsonify({"enrolled": False})

        # Recompute counts (não confiar em denormalizado pra UI)
        total = db.query(func.count(models.Referral.id)).filter_by(affiliate_id=aff.id).scalar() or 0
        active = db.query(func.count(models.Referral.id)).filter_by(
            affiliate_id=aff.id, status="paid",
        ).scalar() or 0

        # Tier auto-update
        new_tier = _calc_tier(active)
        if new_tier != aff.tier:
            aff.tier = new_tier
            aff.commission_pct = COMMISSION_TIERS[new_tier]["pct"]
            db.commit()

        from os import getenv
        app_url = getenv("APP_URL", "http://localhost:5000")
        return jsonify({
            "enrolled": True,
            "ref_code": aff.ref_code,
            "ref_link": f"{app_url}/r/{aff.ref_code}",
            "pix_key": aff.pix_key,
            "pix_key_type": aff.pix_key_type,
            "tier": aff.tier,
            "commission_pct": aff.commission_pct,
            "total_referrals": total,
            "active_referrals": active,
            "total_earned_brl": (aff.total_earned_brl_cents or 0) / 100,
            "total_paid_out_brl": (aff.total_paid_out_brl_cents or 0) / 100,
            "pending_brl": ((aff.total_earned_brl_cents or 0) - (aff.total_paid_out_brl_cents or 0)) / 100,
            "tier_progress": {
                "current": aff.tier,
                "next_tier": (
                    "silver" if aff.tier == "standard" else
                    ("gold" if aff.tier == "silver" else None)
                ),
                "needed_for_next": (
                    max(0, 10 - active) if aff.tier == "standard" else
                    max(0, 50 - active) if aff.tier == "silver" else
                    None
                ),
            },
        })
    finally:
        db.close()


@affiliate_bp.route("/enroll", methods=["POST"])
@login_required
def enroll():
    """Cadastra current_user como afiliado (idempotente)."""
    body = request.get_json(silent=True) or {}
    pix_key = (body.get("pix_key") or "").strip() or None
    pix_key_type = (body.get("pix_key_type") or "").strip().lower() or None

    if pix_key_type and pix_key_type not in ("cpf", "email", "phone", "random"):
        return jsonify({"error": "pix_key_type_invalid"}), 422

    db = SessionLocal()
    try:
        existing = db.query(models.Affiliate).filter_by(user_id=current_user.id).first()
        if existing:
            return jsonify({"ok": True, "already_enrolled": True, "ref_code": existing.ref_code})

        ref_code = _generate_ref_code()
        aff = models.Affiliate(
            user_id=current_user.id,
            ref_code=ref_code,
            pix_key=pix_key,
            pix_key_type=pix_key_type,
            commission_pct=COMMISSION_TIERS["standard"]["pct"],
        )
        db.add(aff)
        db.commit()
        db.refresh(aff)

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="affiliate.enrolled",
                target_type="affiliate", target_id=str(aff.id),
                payload={"ref_code": ref_code},
            ))
            db.commit()
        except Exception:
            pass

        return jsonify({"ok": True, "ref_code": ref_code}), 201
    finally:
        db.close()


@affiliate_bp.route("/me", methods=["PATCH"])
@login_required
def update_affiliate():
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        aff = db.query(models.Affiliate).filter_by(user_id=current_user.id).first()
        if not aff:
            return jsonify({"error": "not_enrolled"}), 404
        if "pix_key" in body:
            aff.pix_key = (body["pix_key"] or "").strip() or None
        if "pix_key_type" in body:
            t = (body["pix_key_type"] or "").strip().lower() or None
            if t and t not in ("cpf", "email", "phone", "random"):
                return jsonify({"error": "pix_key_type_invalid"}), 422
            aff.pix_key_type = t
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@affiliate_bp.route("/referrals", methods=["GET"])
@login_required
def list_referrals():
    db = SessionLocal()
    try:
        aff = db.query(models.Affiliate).filter_by(user_id=current_user.id).first()
        if not aff:
            return jsonify({"error": "not_enrolled"}), 404

        rows = db.query(models.Referral).filter_by(
            affiliate_id=aff.id,
        ).order_by(models.Referral.signed_up_at.desc()).limit(200).all()

        return jsonify({
            "items": [
                {
                    "id": r.id,
                    "referred_email": r.referred_email,
                    "signed_up_at": r.signed_up_at.isoformat() if r.signed_up_at else None,
                    "first_payment_at": r.first_payment_at.isoformat() if r.first_payment_at else None,
                    "status": r.status,
                    "total_commission_brl": (r.total_commission_earned_cents or 0) / 100,
                    "last_recurrence_at": r.last_recurrence_at.isoformat() if r.last_recurrence_at else None,
                } for r in rows
            ]
        })
    finally:
        db.close()


@affiliate_bp.route("/payouts", methods=["GET"])
@login_required
def list_payouts():
    db = SessionLocal()
    try:
        aff = db.query(models.Affiliate).filter_by(user_id=current_user.id).first()
        if not aff:
            return jsonify({"error": "not_enrolled"}), 404

        rows = db.query(models.AffiliatePayout).filter_by(
            affiliate_id=aff.id,
        ).order_by(models.AffiliatePayout.period_yyyymm.desc()).limit(48).all()
        return jsonify({
            "items": [
                {
                    "id": p.id,
                    "period_yyyymm": p.period_yyyymm,
                    "amount_brl": (p.amount_brl_cents or 0) / 100,
                    "status": p.status,
                    "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                    "pix_receipt_url": p.pix_receipt_url,
                    "notes": p.notes,
                } for p in rows
            ]
        })
    finally:
        db.close()


# ─── Public landing pra tracking ──────────────────────────────────────


@referral_bp.route("/r/<ref_code>", methods=["GET"])
def referral_landing(ref_code):
    """Track + redirect pra landing/signup. Cookie 30d."""
    code = (ref_code or "").strip().upper()[:40]
    if not code:
        return redirect("/")

    db = SessionLocal()
    try:
        aff = db.query(models.Affiliate).filter_by(ref_code=code).first()
        if not aff:
            return redirect("/")
    finally:
        db.close()

    # Set cookie 30d e redirect pro signup
    target = "/saas/signup"
    resp = make_response(redirect(target))
    resp.set_cookie(
        "meumisterio_ref",
        code,
        max_age=30 * 24 * 3600,
        httponly=False,  # Frontend pode ler pra UI
        samesite="Lax",
        secure=request.is_secure,
        path="/",
    )
    logger.info("[referral] track ref_code=%s ip=%s", code, request.remote_addr)
    return resp


# ─── Helper pra usar no signup_user ────────────────────────────────────


def attach_referral_to_signup(referred_user_id: int, referred_email: str) -> None:
    """
    Chamado em api/saas/auth.signup_user após criar User.
    Lê cookie meumisterio_ref, cria Referral entry se válido.
    """
    ref_code = (request.cookies.get("meumisterio_ref") or "").strip().upper() if request else None
    if not ref_code:
        return

    db = SessionLocal()
    try:
        aff = db.query(models.Affiliate).filter_by(ref_code=ref_code).first()
        if not aff:
            return
        # Don't self-refer
        if aff.user_id == referred_user_id:
            return

        # Idempotência (referral por user)
        existing = db.query(models.Referral).filter_by(
            referred_user_id=referred_user_id,
        ).first()
        if existing:
            return

        ref = models.Referral(
            affiliate_id=aff.id,
            referred_user_id=referred_user_id,
            referred_email=referred_email,
            status="signup",
            cookie_ip=request.remote_addr if request else None,
        )
        db.add(ref)
        # Increment denormalized total
        aff.total_referrals = (aff.total_referrals or 0) + 1
        db.commit()
        logger.info(
            "[referral.signup_attached] affiliate_id=%s ref_code=%s referred=%s",
            aff.id, ref_code, referred_user_id,
        )
    except Exception as exc:
        logger.warning("[referral] attach falhou: %s", exc)
    finally:
        db.close()


def record_referral_payment(referred_user_id: int, amount_brl_cents: int) -> None:
    """
    Chamado em webhook Stripe quando referred user paga.
    Calcula commission_pct e adiciona ao Affiliate.
    """
    db = SessionLocal()
    try:
        ref = db.query(models.Referral).filter_by(
            referred_user_id=referred_user_id,
        ).first()
        if not ref:
            return

        aff = db.query(models.Affiliate).filter_by(id=ref.affiliate_id).first()
        if not aff:
            return

        commission = int(amount_brl_cents * aff.commission_pct / 100)
        now = datetime.now(timezone.utc)

        # Marca primeira venda
        if not ref.first_payment_at:
            ref.first_payment_at = now
            ref.status = "paid"

        ref.last_recurrence_at = now
        ref.total_commission_earned_cents = (ref.total_commission_earned_cents or 0) + commission

        # Aff totals
        aff.total_earned_brl_cents = (aff.total_earned_brl_cents or 0) + commission
        # Active count (only if status=paid)
        if ref.status == "paid":
            aff.active_referrals = (aff.active_referrals or 0) + 1 if not ref.first_payment_at else aff.active_referrals

        db.commit()

        logger.info(
            "[referral.payment] affiliate=%s referred=%s amount=%s commission=%s",
            aff.id, referred_user_id, amount_brl_cents, commission,
        )
    finally:
        db.close()
