"""
api/saas/content.py — Motor de Infoprodutos & Conteúdo Digital
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Resolve: venda de e-books, meditações gravadas, cursos, planilhas, oráculos.

Endpoints:
  GET    /saas/content/                        — lista infoprodutos
  POST   /saas/content/                        — cria infoproduto
  GET    /saas/content/<id>                    — detalhe + métricas
  PUT    /saas/content/<id>                    — edita
  DELETE /saas/content/<id>                    — arquiva
  POST   /saas/content/<id>/publish            — publica
  POST   /saas/content/<id>/purchase           — compra (gera acesso)
  GET    /saas/content/access/<token>          — acessa conteúdo (link único)
  GET    /saas/content/<id>/purchases          — lista compradores
  POST   /saas/content/<id>/deliver-whatsapp   — reenvia entrega via WA
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal
from extensions import limiter

logger = logging.getLogger(__name__)
content_bp = Blueprint("saas_content", __name__, url_prefix="/saas/content")


@content_bp.route("/", methods=["GET"])
@login_required
def list_content():
    db = SessionLocal()
    try:
        items = db.query(models.ContentAsset).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.ContentAsset.created_at.desc()).limit(50).all()

        return jsonify({
            "content": [_content_to_dict(c) for c in items]
        })
    finally:
        db.close()


@content_bp.route("/", methods=["POST"])
@login_required
def create_content():
    """
    Body: {title, description?, content_type?, price_cents?, is_free?,
           file_url?, cover_image_url?, preview_url?,
           delivery_method?, delivery_message?, metadata_json?}
    """
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()

    if not title or len(title) < 3:
        return jsonify({"error": "title_required"}), 422

    db = SessionLocal()
    try:
        content = models.ContentAsset(
            tenant_id=current_user.tenant_id,
            created_by_user_id=current_user.id,
            title=title[:200],
            description=(body.get("description") or "").strip() or None,
            content_type=body.get("content_type", "ebook"),
            price_cents=int(body.get("price_cents", 0)),
            is_free=bool(body.get("is_free", False)),
            file_url=body.get("file_url"),
            cover_image_url=body.get("cover_image_url"),
            preview_url=body.get("preview_url"),
            delivery_method=body.get("delivery_method", "download"),
            delivery_message=body.get("delivery_message"),
            metadata_json=body.get("metadata_json") or {},
            status="draft",
        )
        db.add(content)
        db.commit()
        db.refresh(content)

        return jsonify({"ok": True, "id": content.id}), 201
    finally:
        db.close()


@content_bp.route("/<int:content_id>", methods=["GET"])
@login_required
def get_content(content_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        result = _content_to_dict(c)

        # Stats
        purchases = db.query(models.ContentPurchase).filter_by(
            content_id=content_id, status="paid",
        ).count()
        revenue = db.query(
            models.ContentPurchase.amount_paid_cents,
        ).filter_by(content_id=content_id, status="paid").all()
        result["stats"] = {
            "total_purchases": purchases,
            "total_revenue_cents": sum(r[0] for r in revenue),
        }

        return jsonify(result)
    finally:
        db.close()


@content_bp.route("/<int:content_id>", methods=["PUT"])
@login_required
def update_content(content_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        editable = [
            "title", "description", "content_type", "price_cents", "is_free",
            "file_url", "cover_image_url", "preview_url",
            "delivery_method", "delivery_message", "metadata_json",
        ]
        for field in editable:
            if field in body:
                val = body[field]
                if field == "title":
                    val = (val or "").strip()[:200]
                setattr(c, field, val)

        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@content_bp.route("/<int:content_id>", methods=["DELETE"])
@login_required
def archive_content(content_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404
        c.status = "archived"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@content_bp.route("/<int:content_id>/publish", methods=["POST"])
@login_required
def publish_content(content_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404
        if not c.file_url and not c.is_free:
            return jsonify({"error": "file_url_required_for_paid"}), 422
        c.status = "published"
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@content_bp.route("/<int:content_id>/purchase", methods=["POST"])
@login_required
def purchase_content(content_id: int):
    """
    Registra compra de infoproduto. Gera access_token único.

    Body: {lead_id?, payment_method?, payment_id?, amount_paid_cents?, coupon_code?}
    """
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
            status="published",
        ).first()
        if not c:
            return jsonify({"error": "not_found_or_not_published"}), 404

        price = c.price_cents
        coupon_id = None

        # Cupom
        coupon_code = body.get("coupon_code")
        if coupon_code:
            coupon = db.query(models.Coupon).filter_by(
                tenant_id=current_user.tenant_id,
                code=coupon_code.upper().strip(),
                is_active=True,
            ).first()
            if coupon and (coupon.applies_to in ("content", "all", None)):
                if coupon.max_uses is None or coupon.used_count < coupon.max_uses:
                    if coupon.discount_type == "percent":
                        discount = int(price * coupon.discount_value / 100)
                    else:
                        discount = coupon.discount_value * 100
                    price = max(0, price - discount)
                    coupon.used_count += 1
                    coupon_id = coupon.id

        # Free ou já pago?
        final_status = "paid" if (c.is_free or price == 0) else "pending"
        access_token = secrets.token_urlsafe(32)

        purchase = models.ContentPurchase(
            content_id=content_id,
            tenant_id=current_user.tenant_id,
            lead_id=body.get("lead_id"),
            amount_paid_cents=body.get("amount_paid_cents", price),
            coupon_id=coupon_id,
            payment_method=body.get("payment_method"),
            payment_id=body.get("payment_id"),
            status=final_status,
            access_token=access_token,
        )
        db.add(purchase)

        if final_status == "paid":
            c.total_sales += 1
            c.total_revenue_cents += price
            purchase.delivered = True
            purchase.delivered_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(purchase)

        result = {
            "ok": True,
            "purchase_id": purchase.id,
            "status": final_status,
            "amount_cents": price,
        }

        if final_status == "paid":
            result["access_token"] = access_token
            result["access_url"] = f"/saas/content/access/{access_token}"
            result["file_url"] = c.file_url
            result["delivery_message"] = c.delivery_message

            # Entrega via WhatsApp se configurado
            if c.delivery_method == "whatsapp_send" and body.get("lead_id"):
                _deliver_via_whatsapp(db, c, body["lead_id"], current_user.tenant_id)

        return jsonify(result), 201
    finally:
        db.close()


@content_bp.route("/access/<token>", methods=["GET"])
def access_content(token: str):
    """
    Acesso público ao conteúdo via token único (sem login necessário).
    """
    db = SessionLocal()
    try:
        purchase = db.query(models.ContentPurchase).filter_by(
            access_token=token, status="paid",
        ).first()
        if not purchase:
            return jsonify({"error": "invalid_or_expired_token"}), 404

        content = db.query(models.ContentAsset).filter_by(
            id=purchase.content_id,
        ).first()
        if not content:
            return jsonify({"error": "content_not_found"}), 404

        return jsonify({
            "title": content.title,
            "description": content.description,
            "content_type": content.content_type,
            "file_url": content.file_url,
            "delivery_message": content.delivery_message,
            "purchased_at": purchase.purchased_at.isoformat(),
        })
    finally:
        db.close()


@content_bp.route("/<int:content_id>/purchases", methods=["GET"])
@login_required
def list_purchases(content_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        purchases = db.query(models.ContentPurchase).filter_by(
            content_id=content_id,
        ).order_by(models.ContentPurchase.purchased_at.desc()).limit(100).all()

        # Enrich
        lead_ids = [p.lead_id for p in purchases if p.lead_id]
        leads_map = {}
        if lead_ids:
            for lead in db.query(models.Lead).filter(models.Lead.id.in_(lead_ids)).all():
                leads_map[lead.id] = lead

        return jsonify({
            "purchases": [
                {
                    "id": p.id, "lead_id": p.lead_id,
                    "lead_name": leads_map.get(p.lead_id) and leads_map[p.lead_id].nome,
                    "amount_cents": p.amount_paid_cents,
                    "status": p.status,
                    "delivered": p.delivered,
                    "purchased_at": p.purchased_at.isoformat(),
                } for p in purchases
            ],
            "summary": {
                "total": len(purchases),
                "paid": sum(1 for p in purchases if p.status == "paid"),
                "revenue_cents": sum(p.amount_paid_cents for p in purchases if p.status == "paid"),
            },
        })
    finally:
        db.close()


@content_bp.route("/<int:content_id>/deliver-whatsapp", methods=["POST"])
@login_required
@limiter.limit("30/hour")
def deliver_whatsapp(content_id: int):
    """
    Reenvia conteúdo via WhatsApp para um lead.
    Body: {lead_id}
    """
    body = request.get_json(silent=True) or {}
    lead_id = body.get("lead_id")
    if not lead_id:
        return jsonify({"error": "lead_id_required"}), 422

    db = SessionLocal()
    try:
        c = db.query(models.ContentAsset).filter_by(
            id=content_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404

        ok = _deliver_via_whatsapp(db, c, int(lead_id), current_user.tenant_id)
        return jsonify({"ok": ok})
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# CUPONS — CRUD rápido
# ═══════════════════════════════════════════════════════════════════════

coupons_bp = Blueprint("saas_coupons", __name__, url_prefix="/saas/coupons")


@coupons_bp.route("/", methods=["GET"])
@login_required
def list_coupons():
    db = SessionLocal()
    try:
        coupons = db.query(models.Coupon).filter_by(
            tenant_id=current_user.tenant_id,
        ).order_by(models.Coupon.created_at.desc()).all()

        return jsonify({
            "coupons": [
                {
                    "id": c.id, "code": c.code,
                    "discount_type": c.discount_type,
                    "discount_value": c.discount_value,
                    "applies_to": c.applies_to,
                    "max_uses": c.max_uses, "used_count": c.used_count,
                    "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                    "is_active": c.is_active,
                    "created_at": c.created_at.isoformat(),
                } for c in coupons
            ]
        })
    finally:
        db.close()


@coupons_bp.route("/", methods=["POST"])
@login_required
def create_coupon():
    """
    Body: {code, discount_type, discount_value, applies_to?, target_id?,
           max_uses?, valid_from?, valid_until?}
    """
    body = request.get_json(silent=True) or {}
    code = (body.get("code") or "").strip().upper()
    if not code or len(code) < 3:
        return jsonify({"error": "code_required"}), 422

    db = SessionLocal()
    try:
        existing = db.query(models.Coupon).filter_by(
            tenant_id=current_user.tenant_id, code=code,
        ).first()
        if existing:
            return jsonify({"error": "code_already_exists"}), 409

        coupon = models.Coupon(
            tenant_id=current_user.tenant_id,
            code=code[:32],
            discount_type=body.get("discount_type", "percent"),
            discount_value=int(body.get("discount_value", 10)),
            applies_to=body.get("applies_to", "all"),
            target_id=body.get("target_id"),
            max_uses=body.get("max_uses"),
            valid_from=_parse_dt(body.get("valid_from")),
            valid_until=_parse_dt(body.get("valid_until")),
        )
        db.add(coupon)
        db.commit()
        db.refresh(coupon)

        return jsonify({"ok": True, "id": coupon.id, "code": coupon.code}), 201
    finally:
        db.close()


@coupons_bp.route("/<int:coupon_id>", methods=["DELETE"])
@login_required
def deactivate_coupon(coupon_id: int):
    db = SessionLocal()
    try:
        c = db.query(models.Coupon).filter_by(
            id=coupon_id, tenant_id=current_user.tenant_id,
        ).first()
        if not c:
            return jsonify({"error": "not_found"}), 404
        c.is_active = False
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@coupons_bp.route("/validate", methods=["POST"])
@login_required
def validate_coupon():
    """
    Valida cupom sem usar.
    Body: {code, applies_to?, price_cents?}
    """
    body = request.get_json(silent=True) or {}
    code = (body.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "code_required"}), 422

    db = SessionLocal()
    try:
        coupon = db.query(models.Coupon).filter_by(
            tenant_id=current_user.tenant_id,
            code=code, is_active=True,
        ).first()
        if not coupon:
            return jsonify({"valid": False, "reason": "not_found"}), 404

        now = datetime.now(timezone.utc)
        if coupon.valid_from and now < coupon.valid_from:
            return jsonify({"valid": False, "reason": "not_yet_active"})
        if coupon.valid_until and now > coupon.valid_until:
            return jsonify({"valid": False, "reason": "expired"})
        if coupon.max_uses and coupon.used_count >= coupon.max_uses:
            return jsonify({"valid": False, "reason": "max_uses_reached"})

        # Calcular desconto se price fornecido
        price = body.get("price_cents")
        discount = 0
        if price:
            if coupon.discount_type == "percent":
                discount = int(int(price) * coupon.discount_value / 100)
            else:
                discount = coupon.discount_value * 100

        return jsonify({
            "valid": True,
            "discount_type": coupon.discount_type,
            "discount_value": coupon.discount_value,
            "discount_cents": discount,
            "final_price_cents": max(0, int(price or 0) - discount),
            "uses_remaining": (coupon.max_uses - coupon.used_count) if coupon.max_uses else None,
        })
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _content_to_dict(c: models.ContentAsset) -> dict:
    return {
        "id": c.id, "title": c.title, "description": c.description,
        "content_type": c.content_type,
        "price_cents": c.price_cents,
        "price_brl": c.price_cents / 100,
        "is_free": c.is_free,
        "cover_image_url": c.cover_image_url,
        "preview_url": c.preview_url,
        "delivery_method": c.delivery_method,
        "status": c.status,
        "total_sales": c.total_sales,
        "total_revenue_brl": c.total_revenue_cents / 100,
        "created_at": c.created_at.isoformat(),
    }


def _deliver_via_whatsapp(db, content: models.ContentAsset, lead_id: int, tenant_id: str) -> bool:
    """Envia conteúdo via WhatsApp para o lead."""
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id, tenant_id=tenant_id).first()
        if not lead or not lead.telefone:
            return False

        import horoscope
        client = horoscope._get_whatsapp_client(tenant_id)
        if not client:
            return False

        msg = content.delivery_message or f"🎁 Aqui está seu conteúdo: {content.title}"
        client.enviar_mensagem(lead.telefone, msg, formato="texto")

        if content.file_url:
            client.enviar_mensagem(
                lead.telefone, content.file_url, formato="documento",
            )
        return True
    except Exception as exc:
        logger.warning("[content.deliver_wa] falhou: %s", exc)
        return False


def _parse_dt(val) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val).replace("Z", "+00:00"))
    except Exception:
        return None
