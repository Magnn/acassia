"""
api/saas/checkout_webhooks.py — Webhook de Checkout Nativo (DevZapp DevFunil)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recebe webhooks de Hotmart, Kiwify, Asaas, Stripe.
Dispara automações: confirmação, boleto/PIX, carrinho abandonado, reembolso.
"""
from __future__ import annotations
import logging, re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from db.database import SessionLocal
from db import models

logger = logging.getLogger(__name__)
checkout_bp = Blueprint("checkout_webhooks", __name__, url_prefix="/saas/checkout")


# ═══════ WEBHOOK RECEIVERS (Public — no auth, uses tenant token) ═══════

def _normalize_phone(phone: str) -> str:
    """Strip non-digits, ensure country code."""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11:  # BR mobile without country
        digits = "55" + digits
    elif len(digits) == 10:
        digits = "55" + digits
    return digits


def _find_or_create_lead(db, tenant_id, phone, name=None, email=None):
    """Find lead by phone or create new one."""
    phone = _normalize_phone(phone)
    if not phone:
        return None
    lead = db.query(models.Lead).filter_by(tenant_id=tenant_id, telefone=phone).first()
    if not lead:
        lead = models.Lead(
            tenant_id=tenant_id, telefone=phone,
            nome=name or "", genero="desconhecido",
            pipeline_stage="interessado",
        )
        db.add(lead)
        db.flush()
    return lead


@checkout_bp.route("/webhook/<tenant_id>/<platform>", methods=["POST"])
def receive_webhook(tenant_id: str, platform: str):
    """Public endpoint: receives checkout webhooks.

    URL pattern: /saas/checkout/webhook/{tenant_id}/{platform}
    Platforms: hotmart, kiwify, asaas, stripe
    """
    data = request.json or {}
    db = SessionLocal()
    try:
        parsed = _parse_webhook(platform, data)
        if not parsed:
            logger.warning("[checkout] Unknown platform or payload: %s", platform)
            return jsonify({"ok": False, "error": "unknown_platform"}), 400

        lead = _find_or_create_lead(
            db, tenant_id, parsed["phone"], parsed.get("name"), parsed.get("email")
        )

        evt = models.CheckoutWebhookEvent(
            tenant_id=tenant_id,
            platform=platform,
            event_type=parsed["event_type"],
            payload=data,
            buyer_name=parsed.get("name"),
            buyer_email=parsed.get("email"),
            buyer_phone=parsed.get("phone"),
            product_name=parsed.get("product"),
            product_id=parsed.get("product_id"),
            value=parsed.get("value", 0),
            payment_method=parsed.get("payment_method"),
            payment_url=parsed.get("payment_url"),
            lead_id=lead.id if lead else None,
            status="processed",
            processed_at=datetime.now(timezone.utc),
        )
        db.add(evt)

        # Update lead based on event
        if lead:
            if parsed["event_type"] == "purchase_approved":
                lead.convertido = True
                lead.pipeline_stage = "convertido"
                lead.deal_value = parsed.get("value", 0)
                lead.conversion_source = f"{platform}:{parsed.get('product', 'unknown')}"
                lead.conversion_at = datetime.now(timezone.utc)
                lead.produto_comprado = parsed.get("product")
                # Register conversion event
                conv = models.ConversionEvent(
                    tenant_id=tenant_id, lead_id=lead.id,
                    source_type="checkout", source_id=parsed.get("product_id"),
                    source_name=f"{platform} — {parsed.get('product', '?')}",
                    value=parsed.get("value", 0),
                )
                db.add(conv)

                # ── A/B Test Attribution Lookback (48h) ──
                # Se este lead passou por algum nó ab_split nas últimas 48h,
                # marca como convertido com o valor da compra.
                try:
                    from datetime import timedelta
                    lookback = datetime.now(timezone.utc) - timedelta(hours=48)
                    ab_exposures = db.query(models.ABTestExposure).filter(
                        models.ABTestExposure.tenant_id == tenant_id,
                        models.ABTestExposure.lead_id == lead.id,
                        models.ABTestExposure.exposed_at >= lookback,
                        models.ABTestExposure.converted == False,  # noqa: E712
                    ).all()
                    purchase_value = float(parsed.get("value", 0) or 0)
                    for exp in ab_exposures:
                        exp.converted = True
                        exp.conversion_value = purchase_value
                        exp.converted_at = datetime.now(timezone.utc)
                    if ab_exposures:
                        logger.info(
                            "[checkout] AB attribution: lead=%s variants=%s value=%.2f",
                            lead.id,
                            [(e.node_id, e.variant) for e in ab_exposures],
                            purchase_value,
                        )
                except Exception as ab_err:
                    logger.debug("[checkout] AB attribution failed (non-fatal): %s", ab_err)
            elif parsed["event_type"] == "billet_printed":
                lead.pipeline_stage = "proposta"
                tags = list(lead.tags or [])
                if "checkout:boleto" not in tags:
                    lead.tags = tags + ["checkout:boleto"]
            elif parsed["event_type"] == "pix_generated":
                lead.pipeline_stage = "proposta"
                tags = list(lead.tags or [])
                if "checkout:pix" not in tags:
                    lead.tags = tags + ["checkout:pix"]
            elif parsed["event_type"] == "cart_abandoned":
                tags = list(lead.tags or [])
                if "checkout:abandonou" not in tags:
                    lead.tags = tags + ["checkout:abandonou"]
            elif parsed["event_type"] == "refunded":
                lead.pipeline_stage = "perdido"
                tags = list(lead.tags or [])
                if "checkout:reembolso" not in tags:
                    lead.tags = tags + ["checkout:reembolso"]

        db.commit()
        logger.info("[checkout] %s/%s event=%s lead=%s",
                     tenant_id, platform, parsed["event_type"],
                     lead.id if lead else "none")
        return jsonify({"ok": True, "event_id": evt.id}), 200
    except Exception as e:
        logger.error("[checkout] Error: %s", e)
        db.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        db.close()


def _parse_webhook(platform: str, data: dict) -> dict | None:
    """Parse webhook payload for each platform."""
    if platform == "hotmart":
        return _parse_hotmart(data)
    elif platform == "kiwify":
        return _parse_kiwify(data)
    elif platform == "asaas":
        return _parse_asaas(data)
    elif platform == "stripe":
        return _parse_stripe(data)
    elif platform == "manual":
        return data  # passthrough
    return None


def _parse_hotmart(data: dict) -> dict:
    """Parse Hotmart webhook (v2 format)."""
    event_map = {
        "PURCHASE_APPROVED": "purchase_approved",
        "PURCHASE_COMPLETE": "purchase_approved",
        "PURCHASE_BILLET_PRINTED": "billet_printed",
        "PURCHASE_CANCELED": "refunded",
        "PURCHASE_REFUNDED": "refunded",
        "PURCHASE_CHARGEBACK": "refunded",
        "PURCHASE_DELAYED": "cart_abandoned",
        "PURCHASE_PROTEST": "refunded",
    }
    raw_event = data.get("event", data.get("hottok", ""))
    buyer = data.get("data", {}).get("buyer", data.get("buyer", {}))
    product = data.get("data", {}).get("product", data.get("product", {}))
    purchase = data.get("data", {}).get("purchase", data.get("purchase", {}))
    return {
        "event_type": event_map.get(raw_event, "unknown"),
        "name": buyer.get("name", ""),
        "email": buyer.get("email", ""),
        "phone": buyer.get("checkout_phone", buyer.get("phone", "")),
        "product": product.get("name", ""),
        "product_id": str(product.get("id", "")),
        "value": purchase.get("price", {}).get("value", 0) if isinstance(purchase.get("price"), dict) else purchase.get("price", 0),
        "payment_method": purchase.get("payment", {}).get("type", "") if isinstance(purchase.get("payment"), dict) else "",
        "payment_url": purchase.get("payment", {}).get("billet_url", "") if isinstance(purchase.get("payment"), dict) else "",
    }


def _parse_kiwify(data: dict) -> dict:
    """Parse Kiwify webhook."""
    event_map = {
        "order_approved": "purchase_approved",
        "order_completed": "purchase_approved",
        "order_refunded": "refunded",
        "waiting_payment": "billet_printed",
        "cart_abandoned": "cart_abandoned",
    }
    customer = data.get("Customer", data.get("customer", {}))
    product = data.get("Product", data.get("product", {}))
    return {
        "event_type": event_map.get(data.get("order_status", ""), "unknown"),
        "name": customer.get("full_name", ""),
        "email": customer.get("email", ""),
        "phone": customer.get("mobile", customer.get("phone", "")),
        "product": product.get("name", ""),
        "product_id": str(product.get("id", "")),
        "value": float(data.get("Commissions", {}).get("product_base_price", 0) or data.get("order_value", 0)),
        "payment_method": data.get("payment_method", ""),
        "payment_url": data.get("boleto_URL", data.get("pix_code", "")),
    }


def _parse_asaas(data: dict) -> dict:
    """Parse Asaas webhook."""
    event_map = {
        "PAYMENT_CONFIRMED": "purchase_approved",
        "PAYMENT_RECEIVED": "purchase_approved",
        "PAYMENT_CREATED": "billet_printed",
        "PAYMENT_OVERDUE": "billet_printed",
        "PAYMENT_REFUNDED": "refunded",
    }
    payment = data.get("payment", data)
    return {
        "event_type": event_map.get(data.get("event", ""), "unknown"),
        "name": payment.get("customer", ""),
        "email": "",
        "phone": "",
        "product": payment.get("description", ""),
        "product_id": str(payment.get("id", "")),
        "value": float(payment.get("value", 0)),
        "payment_method": payment.get("billingType", ""),
        "payment_url": payment.get("bankSlipUrl", payment.get("invoiceUrl", "")),
    }


def _parse_stripe(data: dict) -> dict:
    """Parse Stripe webhook (simplified)."""
    event_type = data.get("type", "")
    obj = data.get("data", {}).get("object", {})
    e = "unknown"
    if "checkout.session.completed" in event_type:
        e = "purchase_approved"
    elif "payment_intent.payment_failed" in event_type:
        e = "cart_abandoned"
    elif "charge.refunded" in event_type:
        e = "refunded"
    return {
        "event_type": e,
        "name": obj.get("customer_details", {}).get("name", ""),
        "email": obj.get("customer_details", {}).get("email", ""),
        "phone": obj.get("customer_details", {}).get("phone", ""),
        "product": "",
        "product_id": obj.get("id", ""),
        "value": (obj.get("amount_total", 0) or 0) / 100,
        "payment_method": obj.get("payment_method_types", [""])[0] if obj.get("payment_method_types") else "",
        "payment_url": "",
    }


# ═══════ MANAGEMENT ENDPOINTS (Auth required) ═══════

@checkout_bp.route("/events", methods=["GET"])
@login_required
def list_events():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        platform = request.args.get("platform")
        event_type = request.args.get("event_type")
        q = db.query(models.CheckoutWebhookEvent).filter_by(tenant_id=tid)
        if platform:
            q = q.filter_by(platform=platform)
        if event_type:
            q = q.filter_by(event_type=event_type)
        events = q.order_by(models.CheckoutWebhookEvent.received_at.desc()).limit(100).all()
        return jsonify({"events": [{
            "id": e.id, "platform": e.platform, "event_type": e.event_type,
            "buyer_name": e.buyer_name, "buyer_phone": e.buyer_phone,
            "product_name": e.product_name, "value": e.value,
            "payment_method": e.payment_method, "status": e.status,
            "lead_id": e.lead_id,
            "received_at": e.received_at.isoformat() if e.received_at else None,
        } for e in events], "total": len(events)})
    finally:
        db.close()


@checkout_bp.route("/setup-info", methods=["GET"])
@login_required
def setup_info():
    """Returns webhook URLs for each platform for the current tenant."""
    tid = current_user.tenant_id
    base = request.host_url.rstrip("/")
    return jsonify({
        "tenant_id": tid,
        "webhooks": {
            "hotmart": f"{base}/saas/checkout/webhook/{tid}/hotmart",
            "kiwify": f"{base}/saas/checkout/webhook/{tid}/kiwify",
            "asaas": f"{base}/saas/checkout/webhook/{tid}/asaas",
            "stripe": f"{base}/saas/checkout/webhook/{tid}/stripe",
        },
        "instructions": {
            "hotmart": "Acesse Hotmart > Ferramentas > Webhooks > Cole a URL acima",
            "kiwify": "Acesse Kiwify > Produto > Webhooks > Cole a URL acima",
            "asaas": "Acesse Asaas > Configurações > Webhooks > Cole a URL acima",
            "stripe": "Acesse Stripe > Developers > Webhooks > Cole a URL acima",
        }
    })


@checkout_bp.route("/stats", methods=["GET"])
@login_required
def checkout_stats():
    db = SessionLocal()
    try:
        tid = current_user.tenant_id
        by_platform = dict(
            db.query(models.CheckoutWebhookEvent.platform, func.count(models.CheckoutWebhookEvent.id))
            .filter_by(tenant_id=tid).group_by(models.CheckoutWebhookEvent.platform).all()
        )
        by_event = dict(
            db.query(models.CheckoutWebhookEvent.event_type, func.count(models.CheckoutWebhookEvent.id))
            .filter_by(tenant_id=tid).group_by(models.CheckoutWebhookEvent.event_type).all()
        )
        total_revenue = db.query(func.sum(models.CheckoutWebhookEvent.value)).filter(
            models.CheckoutWebhookEvent.tenant_id == tid,
            models.CheckoutWebhookEvent.event_type == "purchase_approved",
        ).scalar() or 0
        return jsonify({
            "by_platform": by_platform, "by_event": by_event,
            "total_revenue": round(float(total_revenue), 2),
            "total_events": sum(by_platform.values()) if by_platform else 0,
        })
    finally:
        db.close()
