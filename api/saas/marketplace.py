"""
Marketplace de fluxos (Frente 7.14).

Endpoints públicos (logged):
    GET  /saas/marketplace                       — galeria de listings ativos
    GET  /saas/marketplace/<id>                  — detalhe + reviews
    POST /saas/marketplace/<id>/buy              — compra (Stripe ou Pix)
    POST /saas/marketplace/purchases/<id>/apply  — clona pro tenant comprador
    POST /saas/marketplace/<id>/review           — review pós-compra

Endpoints sellers:
    GET  /saas/marketplace/my/listings           — meus listings
    POST /saas/marketplace/listings              — criar listing (vai pra pending_review)
    GET  /saas/marketplace/my/sales              — minhas vendas
    GET  /saas/marketplace/my/payouts            — saldo a receber

Endpoints admin (review):
    GET  /api/admin/marketplace/pending          — listings pra aprovar
    POST /api/admin/marketplace/<id>/approve     — aprova
    POST /api/admin/marketplace/<id>/reject      — rejeita com motivo
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func

from api.admin.guard import require_admin
from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
marketplace_bp = Blueprint("saas_marketplace", __name__, url_prefix="/saas/marketplace")
admin_marketplace_bp = Blueprint("admin_marketplace", __name__, url_prefix="/api/admin/marketplace")


MEU_MISTERIO_FEE_PCT = 30  # 30% do preço fica com a Meu Mistério


# ─── Buyer flows ──────────────────────────────────────────────────────


@marketplace_bp.route("", methods=["GET"])
@login_required
def list_listings():
    """Galeria pública. Filtros: category, price_max, sort."""
    category = request.args.get("category")
    price_max = request.args.get("price_max")
    sort = request.args.get("sort", "popular")  # popular|recent|price_asc|price_desc|rating

    db = SessionLocal()
    try:
        q = db.query(models.MarketplaceListing).filter_by(status="active")
        if category:
            q = q.filter_by(category=category)
        if price_max and price_max.isdigit():
            q = q.filter(models.MarketplaceListing.price_brl_cents <= int(price_max) * 100)

        if sort == "recent":
            q = q.order_by(models.MarketplaceListing.created_at.desc())
        elif sort == "price_asc":
            q = q.order_by(models.MarketplaceListing.price_brl_cents.asc())
        elif sort == "price_desc":
            q = q.order_by(models.MarketplaceListing.price_brl_cents.desc())
        elif sort == "rating":
            q = q.order_by(models.MarketplaceListing.rating_avg.desc().nullslast())
        else:  # popular
            q = q.order_by(models.MarketplaceListing.total_sales.desc())

        items = q.limit(100).all()
        return jsonify({
            "listings": [
                {
                    "id": l.id,
                    "title": l.title,
                    "description": l.description,
                    "category": l.category,
                    "price_brl": l.price_brl_cents / 100,
                    "preview_image_url": l.preview_image_url,
                    "metrics": l.metrics,
                    "total_sales": l.total_sales,
                    "rating_avg": l.rating_avg,
                    "rating_count": l.rating_count,
                    "node_count": len((l.blueprint_json or {}).get("nodes", [])),
                } for l in items
            ]
        })
    finally:
        db.close()


@marketplace_bp.route("/<int:listing_id>", methods=["GET"])
@login_required
def get_listing(listing_id: int):
    """Detail + reviews."""
    db = SessionLocal()
    try:
        listing = db.query(models.MarketplaceListing).filter_by(id=listing_id).first()
        if not listing or listing.status not in ("active", "paused"):
            return jsonify({"error": "not_found"}), 404

        reviews = db.query(models.MarketplaceReview).filter_by(
            listing_id=listing_id,
        ).order_by(models.MarketplaceReview.created_at.desc()).limit(20).all()

        # Já comprei?
        already_bought = db.query(models.MarketplacePurchase).filter_by(
            buyer_user_id=current_user.id, listing_id=listing_id, status="paid",
        ).first() is not None

        return jsonify({
            "id": listing.id,
            "title": listing.title,
            "description": listing.description,
            "category": listing.category,
            "price_brl": listing.price_brl_cents / 100,
            "preview_image_url": listing.preview_image_url,
            "metrics": listing.metrics,
            "blueprint_json": listing.blueprint_json,
            "agent_json": listing.agent_json,
            "total_sales": listing.total_sales,
            "rating_avg": listing.rating_avg,
            "rating_count": listing.rating_count,
            "already_bought": already_bought,
            "reviews": [
                {
                    "id": r.id,
                    "rating": r.rating,
                    "comment": r.comment,
                    "created_at": r.created_at.isoformat(),
                } for r in reviews
            ],
        })
    finally:
        db.close()


@marketplace_bp.route("/<int:listing_id>/buy", methods=["POST"])
@login_required
def buy_listing(listing_id: int):
    """
    Compra via Pix Mercado Pago. V2: Stripe.
    Body opcional: {payment_provider: 'pix'|'stripe'}
    """
    body = request.get_json(silent=True) or {}
    provider = (body.get("payment_provider") or "pix").lower()

    if provider not in ("pix", "stripe"):
        return jsonify({"error": "provider_invalid"}), 422

    db = SessionLocal()
    try:
        listing = db.query(models.MarketplaceListing).filter_by(
            id=listing_id, status="active",
        ).first()
        if not listing:
            return jsonify({"error": "not_found"}), 404

        # Não vende pra você mesmo
        if listing.seller_user_id == current_user.id:
            return jsonify({"error": "self_purchase_forbidden"}), 403

        # Já comprou (idempotência)
        existing = db.query(models.MarketplacePurchase).filter_by(
            buyer_user_id=current_user.id, listing_id=listing_id, status="paid",
        ).first()
        if existing:
            return jsonify({
                "ok": True, "already_purchased": True,
                "purchase_id": existing.id,
                "applied_blueprint_id": existing.applied_blueprint_id,
            })

        amount_cents = listing.price_brl_cents
        fee_cents = int(amount_cents * MEU_MISTERIO_FEE_PCT / 100)
        seller_cents = amount_cents - fee_cents

        # Cria Purchase em pending
        purchase = models.MarketplacePurchase(
            buyer_tenant_id=current_user.tenant_id,
            buyer_user_id=current_user.id,
            listing_id=listing_id,
            amount_brl_cents=amount_cents,
            meumisterio_fee_cents=fee_cents,
            seller_payout_cents=seller_cents,
            payment_provider=provider,
            status="pending",
        )
        db.add(purchase)
        db.commit()
        db.refresh(purchase)

        # Gera Pix
        if provider == "pix":
            try:
                from api.payments.pix_provider import create_pix_mercadopago
                # Plataforma recebe → Meu Mistério, depois faz payout pro seller via affiliate-style
                result = create_pix_mercadopago(
                    tenant_id=current_user.tenant_id,
                    amount_brl=amount_cents / 100,
                    description=f"Marketplace: {listing.title[:80]}",
                    expires_min=30,
                    external_reference=f"mp_{purchase.id}",
                )
                purchase.pix_payment_id = result.provider_payment_id
                db.commit()

                return jsonify({
                    "ok": True,
                    "purchase_id": purchase.id,
                    "qr_code_image_url": result.qr_code_image_url,
                    "qr_code_text": result.qr_code_text,
                    "expires_at": result.expires_at.isoformat(),
                    "amount_brl": amount_cents / 100,
                })
            except Exception as exc:
                logger.exception("[marketplace.buy.pix] falha")
                purchase.status = "failed"
                db.commit()
                return jsonify({"error": "provider_error", "message": str(exc)[:200]}), 502

        # Stripe TBD
        return jsonify({"error": "stripe_not_implemented_yet"}), 501
    finally:
        db.close()


@marketplace_bp.route("/purchases/<int:purchase_id>/apply", methods=["POST"])
@login_required
def apply_purchase(purchase_id: int):
    """
    Clona blueprint da compra pro tenant. Idempotente.
    Só funciona se purchase.status == 'paid'.
    """
    import re
    import quota

    db = SessionLocal()
    try:
        purchase = db.query(models.MarketplacePurchase).filter_by(
            id=purchase_id, buyer_user_id=current_user.id,
        ).first()
        if not purchase:
            return jsonify({"error": "purchase_not_found"}), 404
        if purchase.status != "paid":
            return jsonify({"error": "purchase_not_paid", "status": purchase.status}), 409
        if purchase.applied_blueprint_id:
            return jsonify({
                "ok": True, "already_applied": True,
                "blueprint_id": purchase.applied_blueprint_id,
            })

        listing = db.query(models.MarketplaceListing).filter_by(
            id=purchase.listing_id,
        ).first()
        if not listing:
            return jsonify({"error": "listing_gone"}), 404

        # Quota check flows
        try:
            current = db.query(models.FlowBlueprint).filter_by(
                tenant_id=current_user.tenant_id,
            ).count()
            allowed, _, limit = quota.check_state_quota(
                current_user.tenant_id, "flows", current, db_session=db,
            )
            if not allowed:
                return jsonify({
                    "error": "quota_exceeded", "kind": "flows", "limit": limit,
                }), 402
        except Exception:
            pass

        # Slug único
        title = listing.title
        slug = re.sub(r"[^a-z0-9_]+", "_", title.lower()).strip("_")[:120] or "fluxo"
        base = slug
        n = 1
        while db.query(models.FlowBlueprint).filter_by(
            tenant_id=current_user.tenant_id, slug=slug,
        ).first():
            slug = f"{base}_{n}"
            n += 1

        bp = models.FlowBlueprint(
            tenant_id=current_user.tenant_id,
            slug=slug[:128],
            title=title[:300],
            body_json=listing.blueprint_json or {},
        )
        db.add(bp)
        db.flush()

        purchase.applied_blueprint_id = bp.id
        db.commit()

        return jsonify({
            "ok": True,
            "blueprint_id": bp.id,
            "slug": bp.slug,
            "redirect": f"/flows/{bp.id}",
        })
    finally:
        db.close()


@marketplace_bp.route("/<int:listing_id>/review", methods=["POST"])
@login_required
def submit_review(listing_id: int):
    """Review (1-5 + comentário). Apenas se comprou."""
    body = request.get_json(silent=True) or {}
    rating = body.get("rating")
    comment = (body.get("comment") or "").strip() or None

    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "rating_invalid"}), 422

    db = SessionLocal()
    try:
        purchase = db.query(models.MarketplacePurchase).filter_by(
            buyer_user_id=current_user.id, listing_id=listing_id, status="paid",
        ).first()
        if not purchase:
            return jsonify({"error": "must_purchase_first"}), 403

        existing = db.query(models.MarketplaceReview).filter_by(
            purchase_id=purchase.id,
        ).first()
        if existing:
            existing.rating = rating
            existing.comment = comment
            db.commit()
        else:
            db.add(models.MarketplaceReview(
                listing_id=listing_id,
                purchase_id=purchase.id,
                reviewer_user_id=current_user.id,
                rating=rating,
                comment=comment,
            ))
            db.commit()

        # Recompute rating_avg
        listing = db.query(models.MarketplaceListing).filter_by(id=listing_id).first()
        if listing:
            stats = db.query(
                func.avg(models.MarketplaceReview.rating),
                func.count(models.MarketplaceReview.id),
            ).filter_by(listing_id=listing_id).one()
            listing.rating_avg = float(stats[0]) if stats[0] else None
            listing.rating_count = stats[1] or 0
            db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Seller flows ─────────────────────────────────────────────────────


@marketplace_bp.route("/my/listings", methods=["GET"])
@login_required
def my_listings():
    db = SessionLocal()
    try:
        items = db.query(models.MarketplaceListing).filter_by(
            seller_user_id=current_user.id,
        ).order_by(models.MarketplaceListing.created_at.desc()).all()
        return jsonify({
            "listings": [
                {
                    "id": l.id, "title": l.title, "category": l.category,
                    "price_brl": l.price_brl_cents / 100,
                    "status": l.status,
                    "rejection_reason": l.rejection_reason,
                    "total_sales": l.total_sales,
                    "total_revenue_brl": l.total_revenue_brl_cents / 100,
                    "rating_avg": l.rating_avg,
                    "rating_count": l.rating_count,
                    "approved_at": l.approved_at.isoformat() if l.approved_at else None,
                    "created_at": l.created_at.isoformat(),
                } for l in items
            ]
        })
    finally:
        db.close()


@marketplace_bp.route("/listings", methods=["POST"])
@login_required
def create_listing():
    """
    Cria novo listing (vai pra pending_review).
    Feature gate: requires marketplace_sell=True (Pro+).
    Body: {title, description, category, price_brl, blueprint_json, agent_json?}
    """
    try:
        import plans
        if not plans.has_feature(plans.effective_plan(current_user.tenant_id)[0], "marketplace_sell"):
            return jsonify({
                "error": "feature_not_in_plan",
                "message": "Vender no marketplace é Pro+",
            }), 402
    except Exception:
        pass

    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    category = (body.get("category") or "").strip().lower() or None
    price_brl = body.get("price_brl")
    blueprint_json = body.get("blueprint_json") or body.get("blueprint") or {}
    agent_json = body.get("agent_json")

    if not title or len(title) < 5:
        return jsonify({"error": "title_too_short"}), 422
    if not description or len(description) < 30:
        return jsonify({"error": "description_too_short", "min": 30}), 422
    try:
        price_brl = float(price_brl)
        if price_brl < 9 or price_brl > 5000:
            return jsonify({"error": "price_out_of_range", "min": 9, "max": 5000}), 422
    except (TypeError, ValueError):
        return jsonify({"error": "price_invalid"}), 422
    if not blueprint_json or not isinstance(blueprint_json, dict):
        return jsonify({"error": "blueprint_required"}), 422

    db = SessionLocal()
    try:
        listing = models.MarketplaceListing(
            seller_tenant_id=current_user.tenant_id,
            seller_user_id=current_user.id,
            title=title[:200],
            description=description,
            category=category,
            price_brl_cents=int(round(price_brl * 100)),
            blueprint_json=blueprint_json,
            agent_json=agent_json,
            status="pending_review",
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)

        try:
            db.add(models.AuditEvent(
                tenant_id=current_user.tenant_id,
                actor_user_id=current_user.id,
                event_type="marketplace.listing.created",
                target_type="marketplace_listing",
                target_id=str(listing.id),
                payload={"title": title, "price_brl": price_brl},
            ))
            db.commit()
        except Exception:
            pass

        return jsonify({
            "ok": True, "id": listing.id, "status": listing.status,
            "message": "Listing criado e enviado pra review da equipe Meu Mistério.",
        }), 201
    finally:
        db.close()


@marketplace_bp.route("/my/sales", methods=["GET"])
@login_required
def my_sales():
    db = SessionLocal()
    try:
        # Sales = purchases dos meus listings
        my_listing_ids = [
            l.id for l in db.query(models.MarketplaceListing.id).filter_by(
                seller_user_id=current_user.id,
            ).all()
        ]
        if not my_listing_ids:
            return jsonify({"sales": [], "summary": {}})

        sales = db.query(models.MarketplacePurchase).filter(
            models.MarketplacePurchase.listing_id.in_(my_listing_ids),
            models.MarketplacePurchase.status == "paid",
        ).order_by(models.MarketplacePurchase.purchased_at.desc()).limit(200).all()

        total_revenue = sum(s.seller_payout_cents for s in sales)
        return jsonify({
            "sales": [
                {
                    "id": s.id,
                    "listing_id": s.listing_id,
                    "amount_brl": s.amount_brl_cents / 100,
                    "fee_brl": s.meumisterio_fee_cents / 100,
                    "payout_brl": s.seller_payout_cents / 100,
                    "purchased_at": s.purchased_at.isoformat(),
                } for s in sales
            ],
            "summary": {
                "total_sales": len(sales),
                "total_revenue_brl": total_revenue / 100,
            },
        })
    finally:
        db.close()


# ─── Admin review ─────────────────────────────────────────────────────


@admin_marketplace_bp.route("/pending", methods=["GET"])
@login_required
@require_admin
def admin_list_pending():
    db = SessionLocal()
    try:
        items = db.query(models.MarketplaceListing).filter_by(
            status="pending_review",
        ).order_by(models.MarketplaceListing.created_at.asc()).all()
        return jsonify({
            "listings": [
                {
                    "id": l.id, "title": l.title, "description": l.description,
                    "category": l.category,
                    "price_brl": l.price_brl_cents / 100,
                    "seller_tenant_id": l.seller_tenant_id,
                    "seller_user_id": l.seller_user_id,
                    "node_count": len((l.blueprint_json or {}).get("nodes", [])),
                    "created_at": l.created_at.isoformat(),
                } for l in items
            ]
        })
    finally:
        db.close()


@admin_marketplace_bp.route("/<int:listing_id>/approve", methods=["POST"])
@login_required
@require_admin
def admin_approve(listing_id: int):
    db = SessionLocal()
    try:
        listing = db.query(models.MarketplaceListing).filter_by(id=listing_id).first()
        if not listing:
            return jsonify({"error": "not_found"}), 404
        listing.status = "active"
        listing.approved_by_admin = current_user.id
        listing.approved_at = datetime.now(timezone.utc)
        listing.rejection_reason = None
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@admin_marketplace_bp.route("/<int:listing_id>/reject", methods=["POST"])
@login_required
@require_admin
def admin_reject(listing_id: int):
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip()
    if len(reason) < 10:
        return jsonify({"error": "reason_too_short", "min": 10}), 422

    db = SessionLocal()
    try:
        listing = db.query(models.MarketplaceListing).filter_by(id=listing_id).first()
        if not listing:
            return jsonify({"error": "not_found"}), 404
        listing.status = "removed"
        listing.rejection_reason = reason
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
