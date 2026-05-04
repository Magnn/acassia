"""
Pix endpoints user-facing (Frente 7.1).

POST /saas/pix/create               — gera QR Pix dinâmico
GET  /saas/pix/<id>                 — status de um pagamento
GET  /saas/pix/                     — lista pagamentos do tenant
POST /saas/pix/<id>/cancel          — cancela (se ainda pending)
POST /saas/pix/webhook/mercadopago  — webhook MP (público, dispatch via reference)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from api.payments.pix_provider import (
    PixProviderError,
    create_pix_mercadopago,
    get_payment_status_mercadopago,
)
from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
pix_bp = Blueprint("saas_pix", __name__, url_prefix="/saas/pix")


@pix_bp.route("/create", methods=["POST"])
@login_required
def create_pix():
    """
    Cria Pix QR dinâmico.
    Body: {amount_brl, description?, lead_id?, expires_min?, payer_email?}
    """
    body = request.get_json(silent=True) or {}
    try:
        amount_brl = float(body.get("amount_brl") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "amount_brl_invalid"}), 422
    if amount_brl < 1 or amount_brl > 50_000:
        return jsonify({"error": "amount_brl_out_of_range", "min": 1, "max": 50000}), 422

    description = (body.get("description") or "Pagamento Meu Mistério").strip()[:200]
    lead_id = body.get("lead_id")
    expires_min = int(body.get("expires_min") or 30)
    if expires_min < 5 or expires_min > 1440:
        return jsonify({"error": "expires_min_invalid"}), 422
    payer_email = (body.get("payer_email") or "").strip() or None

    tenant_id = current_user.tenant_id

    try:
        result = create_pix_mercadopago(
            tenant_id=tenant_id,
            amount_brl=amount_brl,
            description=description,
            expires_min=expires_min,
            payer_email=payer_email,
            external_reference=f"tenant_{tenant_id}_lead_{lead_id or 'manual'}",
        )
    except PixProviderError as exc:
        logger.warning("[pix.create] falha tenant=%s: %s", tenant_id, exc)
        return jsonify({"error": "provider_error", "message": str(exc)}), 502
    except Exception as exc:
        logger.exception("[pix.create] erro inesperado")
        return jsonify({"error": "internal", "message": str(exc)[:200]}), 500

    db = SessionLocal()
    try:
        pix = models.PixPayment(
            tenant_id=tenant_id,
            lead_id=int(lead_id) if lead_id else None,
            provider="mercadopago",
            provider_payment_id=result.provider_payment_id,
            amount_brl_cents=result.amount_brl_cents,
            description=description,
            qr_code_image_url=result.qr_code_image_url,
            qr_code_text=result.qr_code_text,
            expires_at=result.expires_at,
            status="pending",
            raw_response=result.raw,
        )
        db.add(pix)
        db.commit()
        db.refresh(pix)

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=current_user.id,
                event_type="pix.created",
                target_type="pix_payment", target_id=str(pix.id),
                payload={"amount_brl": amount_brl, "lead_id": lead_id, "expires_min": expires_min},
            ))
            db.commit()
        except Exception:
            pass

        return jsonify({
            "ok": True,
            "id": pix.id,
            "qr_code_image_url": pix.qr_code_image_url,
            "qr_code_text": pix.qr_code_text,
            "amount_brl": amount_brl,
            "expires_at": pix.expires_at.isoformat() if pix.expires_at else None,
            "status": pix.status,
        }), 201
    finally:
        db.close()


@pix_bp.route("/<int:pix_id>", methods=["GET"])
@login_required
def get_pix(pix_id: int):
    """Retorna status atual + sincroniza com MP se ainda pending."""
    db = SessionLocal()
    try:
        pix = db.query(models.PixPayment).filter_by(
            id=pix_id, tenant_id=current_user.tenant_id,
        ).first()
        if not pix:
            return jsonify({"error": "not_found"}), 404

        # Se ainda pending, consulta MP pra sincronizar
        if pix.status == "pending":
            mp_status = get_payment_status_mercadopago(
                tenant_id=current_user.tenant_id,
                provider_payment_id=pix.provider_payment_id,
            )
            new_status = _map_mp_status(mp_status)
            if new_status != pix.status:
                pix.status = new_status
                if new_status == "approved":
                    pix.paid_at = datetime.now(timezone.utc)
                db.commit()

        return jsonify({
            "id": pix.id,
            "status": pix.status,
            "amount_brl": pix.amount_brl_cents / 100,
            "qr_code_image_url": pix.qr_code_image_url,
            "qr_code_text": pix.qr_code_text,
            "expires_at": pix.expires_at.isoformat() if pix.expires_at else None,
            "paid_at": pix.paid_at.isoformat() if pix.paid_at else None,
            "lead_id": pix.lead_id,
            "description": pix.description,
        })
    finally:
        db.close()


@pix_bp.route("/", methods=["GET"])
@login_required
def list_pix():
    """Lista pagamentos Pix do tenant. Filtros: status, lead_id."""
    status = request.args.get("status")
    lead_id = request.args.get("lead_id")
    limit = min(int(request.args.get("limit") or 50), 500)

    db = SessionLocal()
    try:
        q = db.query(models.PixPayment).filter_by(tenant_id=current_user.tenant_id)
        if status:
            q = q.filter_by(status=status)
        if lead_id and lead_id.isdigit():
            q = q.filter_by(lead_id=int(lead_id))
        items = q.order_by(models.PixPayment.created_at.desc()).limit(limit).all()
        return jsonify({
            "items": [
                {
                    "id": p.id,
                    "status": p.status,
                    "amount_brl": p.amount_brl_cents / 100,
                    "description": p.description,
                    "lead_id": p.lead_id,
                    "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                    "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                    "created_at": p.created_at.isoformat(),
                } for p in items
            ]
        })
    finally:
        db.close()


@pix_bp.route("/<int:pix_id>/cancel", methods=["POST"])
@login_required
def cancel_pix(pix_id: int):
    """Marca Pix como cancelled localmente. NÃO chama MP cancel API (V2)."""
    db = SessionLocal()
    try:
        pix = db.query(models.PixPayment).filter_by(
            id=pix_id, tenant_id=current_user.tenant_id,
        ).first()
        if not pix:
            return jsonify({"error": "not_found"}), 404
        if pix.status != "pending":
            return jsonify({"error": "not_pending"}), 409
        pix.status = "cancelled"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Webhook Mercado Pago ─────────────────────────────────────────────


@pix_bp.route("/webhook/mercadopago", methods=["POST"])
def mp_webhook():
    """
    Webhook público do Mercado Pago.

    MP envia POST com {action, type, data: {id}}.
    Buscamos PixPayment por provider_payment_id, atualizamos status.

    NOTA: V1 sem signature validation (MP usa secret na URL ou validates webhook
    de outras formas). Adicionar HMAC quando MP suportar.
    """
    body = request.get_json(silent=True) or {}
    action = body.get("action") or body.get("type") or ""
    data = body.get("data") or {}
    provider_payment_id = str(data.get("id") or "")

    if not provider_payment_id:
        return "MISSING_ID", 400

    db = SessionLocal()
    try:
        pix = db.query(models.PixPayment).filter_by(
            provider_payment_id=provider_payment_id,
        ).first()
        if not pix:
            # Não-fatal: pode ser webhook de outro tenant ou test
            logger.info("[pix.webhook] payment_id=%s não encontrado", provider_payment_id)
            return "NOT_FOUND", 200

        # Sincroniza status via API
        mp_status = get_payment_status_mercadopago(
            tenant_id=pix.tenant_id,
            provider_payment_id=provider_payment_id,
        )
        new_status = _map_mp_status(mp_status)
        if new_status != pix.status:
            pix.status = new_status
            if new_status == "approved" and not pix.paid_at:
                pix.paid_at = datetime.now(timezone.utc)
                # Se vinculado a lead, marca conversão
                if pix.lead_id:
                    lead = db.query(models.Lead).filter_by(id=pix.lead_id).first()
                    if lead:
                        lead.convertido = True
            db.commit()

            # Audit
            try:
                db.add(models.AuditEvent(
                    tenant_id=pix.tenant_id,
                    actor_user_id=None,
                    event_type=f"pix.{new_status}",
                    target_type="pix_payment", target_id=str(pix.id),
                    payload={"provider_payment_id": provider_payment_id, "action": action},
                ))
                db.commit()
            except Exception:
                pass

            logger.info(
                "[pix.webhook] tenant=%s pix=%s status_change=%s→%s",
                pix.tenant_id, pix.id, pix.status, new_status,
            )

        return "OK", 200
    finally:
        db.close()


def _map_mp_status(mp_status: str) -> str:
    """Mapeia status MP → nosso vocabulário."""
    if mp_status == "approved":
        return "approved"
    if mp_status in ("cancelled", "rejected", "refunded"):
        return "cancelled"
    if mp_status in ("expired",):
        return "expired"
    return "pending"
