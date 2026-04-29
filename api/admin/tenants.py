"""
Cross-tenant grid endpoints (Frente 1.3, 1.4).

GET /api/admin/tenants — lista paginada com filtros + busca
GET /api/admin/tenants/<tenant_id>/overview — dados resumidos do tenant
GET /api/admin/tenants/<tenant_id>/notes — notas internas
POST /api/admin/tenants/<tenant_id>/notes — criar nota
PATCH /api/admin/tenants/<tenant_id>/notes/<id> — editar nota
DELETE /api/admin/tenants/<tenant_id>/notes/<id> — deletar nota

Sem materialized view por enquanto (SQLite não suporta) — query direta com
índices + cache 30s no nível do endpoint.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_, and_, text

from api.admin.guard import require_admin
from db import models
from db.database import SessionLocal
import plans as plans_module


logger = logging.getLogger(__name__)
admin_tenants_bp = Blueprint("admin_tenants", __name__, url_prefix="/api/admin")


# ─── /tenants list ───────────────────────────────────────────────────


@admin_tenants_bp.route("/tenants", methods=["GET"])
@login_required
@require_admin
def list_tenants():
    """
    Lista paginada de tenants com agregados de leads/msgs/MRR.

    Query params:
        ?cursor=<int>          (offset)
        &limit=50              (max 200)
        &sort=mrr_brl:desc     (created_at|mrr_brl|leads_30d|last_login_at:asc|desc)
        &search=maria          (email|tenant_id|name)
        &filter[plan]=pro,enterprise
        &filter[status]=active|suspended|deleted
        &filter[last_login]=24h|7d|30d|>30d
    """
    args = request.args
    cursor = int(args.get("cursor") or 0)
    limit = min(int(args.get("limit") or 50), 200)
    search = (args.get("search") or "").strip()
    sort = args.get("sort") or "criado_em:desc"
    sort_field, _, sort_dir = sort.partition(":")
    sort_dir = sort_dir or "desc"

    plan_filter = args.get("filter[plan]")
    status_filter = args.get("filter[status]") or "active"  # default exclui deletados
    last_login_filter = args.get("filter[last_login]")

    db = SessionLocal()
    try:
        # Base query: users (não-deletados por default)
        q = db.query(models.User)

        if status_filter == "active":
            q = q.filter(models.User.deleted_at.is_(None))
            q = q.filter(models.User.suspended_at.is_(None))
        elif status_filter == "suspended":
            q = q.filter(models.User.suspended_at.isnot(None))
            q = q.filter(models.User.deleted_at.is_(None))
        elif status_filter == "deleted":
            q = q.filter(models.User.deleted_at.isnot(None))
        # status_filter == "all" → sem filtro

        if search:
            like = f"%{search.lower()}%"
            q = q.filter(or_(
                func.lower(models.User.email).like(like),
                func.lower(models.User.tenant_id).like(like),
                func.lower(models.User.name).like(like),
            ))

        if last_login_filter:
            now = datetime.now(timezone.utc)
            if last_login_filter == "24h":
                q = q.filter(models.User.last_login_at > now - timedelta(hours=24))
            elif last_login_filter == "7d":
                q = q.filter(models.User.last_login_at > now - timedelta(days=7))
            elif last_login_filter == "30d":
                q = q.filter(models.User.last_login_at > now - timedelta(days=30))
            elif last_login_filter == ">30d":
                q = q.filter(or_(
                    models.User.last_login_at < now - timedelta(days=30),
                    models.User.last_login_at.is_(None),
                ))

        total = q.count()

        # Sort
        sort_col_map = {
            "criado_em": models.User.criado_em,
            "last_login_at": models.User.last_login_at,
            "email": models.User.email,
            "name": models.User.name,
        }
        col = sort_col_map.get(sort_field, models.User.criado_em)
        q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())

        users = q.offset(cursor).limit(limit + 1).all()
        has_more = len(users) > limit
        users = users[:limit]

        # Para cada user, agrega leads_30d e msgs_30d em queries batch
        tenant_ids = [u.tenant_id for u in users]
        now = datetime.now(timezone.utc)
        since_30d = now - timedelta(days=30)

        leads_counts: dict[str, int] = {}
        msgs_counts: dict[str, int] = {}
        if tenant_ids:
            # leads_30d
            for tid, count in db.query(
                models.Lead.tenant_id,
                func.count(models.Lead.id),
            ).filter(
                models.Lead.tenant_id.in_(tenant_ids),
                models.Lead.criado_em > since_30d,
            ).group_by(models.Lead.tenant_id).all():
                leads_counts[tid] = count

            # msgs_30d (join via lead.tenant_id)
            for tid, count in db.query(
                models.Lead.tenant_id,
                func.count(models.Mensagem.id),
            ).join(
                models.Mensagem, models.Mensagem.lead_id == models.Lead.id,
            ).filter(
                models.Lead.tenant_id.in_(tenant_ids),
                models.Mensagem.timestamp > since_30d,
            ).group_by(models.Lead.tenant_id).all():
                msgs_counts[tid] = count

        # Filtra por plano (se especificado) — após agregação porque effective_plan
        # precisa do tenant_id e potencialmente DB session
        if plan_filter:
            wanted = set(p.strip() for p in plan_filter.split(",") if p.strip())
        else:
            wanted = None

        tenants_out = []
        for u in users:
            plan, source = plans_module.effective_plan(u.tenant_id, db_session=db)
            if wanted and plan not in wanted:
                continue
            cfg = plans_module.get_plan_config(plan)
            tenants_out.append({
                "tenant_id": u.tenant_id,
                "user_id": u.id,
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "plan": plan,
                "plan_label": cfg["label"],
                "plan_source": source,
                "plan_price_brl": cfg["price_brl"],
                "signup_at": u.criado_em.isoformat() if u.criado_em else None,
                "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
                "is_verified": bool(u.is_verified),
                "is_suspended": bool(u.suspended_at),
                "suspension_reason": u.suspension_reason,
                "is_deleted": bool(u.deleted_at),
                "trial_ends_at": u.trial_ends_at.isoformat() if u.trial_ends_at else None,
                "leads_30d": leads_counts.get(u.tenant_id, 0),
                "msgs_30d": msgs_counts.get(u.tenant_id, 0),
                "admin_subrole": u.admin_subrole,
            })

        return jsonify({
            "tenants": tenants_out,
            "total_count": total,
            "cursor_next": cursor + limit if has_more else None,
            "has_more": has_more,
        })
    finally:
        db.close()


# ─── /tenants/<id>/overview ───────────────────────────────────────────


@admin_tenants_bp.route("/tenants/<tenant_id>/overview", methods=["GET"])
@login_required
@require_admin
def tenant_overview(tenant_id: str):
    """Snapshot completo de um tenant pra detail page."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(tenant_id=tenant_id).first()
        if not user:
            return jsonify({"error": "tenant_not_found"}), 404

        plan, source = plans_module.effective_plan(tenant_id, db_session=db)
        cfg = plans_module.get_plan_config(plan)

        # Aggregates
        now = datetime.now(timezone.utc)
        since_30d = now - timedelta(days=30)

        leads_total = db.query(func.count(models.Lead.id)).filter_by(tenant_id=tenant_id).scalar() or 0
        leads_30d = db.query(func.count(models.Lead.id)).filter(
            models.Lead.tenant_id == tenant_id,
            models.Lead.criado_em > since_30d,
        ).scalar() or 0

        msgs_total = db.query(func.count(models.Mensagem.id)).join(
            models.Lead, models.Mensagem.lead_id == models.Lead.id,
        ).filter(models.Lead.tenant_id == tenant_id).scalar() or 0
        msgs_30d = db.query(func.count(models.Mensagem.id)).join(
            models.Lead, models.Mensagem.lead_id == models.Lead.id,
        ).filter(
            models.Lead.tenant_id == tenant_id,
            models.Mensagem.timestamp > since_30d,
        ).scalar() or 0

        # Active overrides + grants
        active_override = db.query(models.TenantPlanOverride).filter(
            models.TenantPlanOverride.tenant_id == tenant_id,
            models.TenantPlanOverride.revoked_at.is_(None),
        ).order_by(models.TenantPlanOverride.created_at.desc()).first()

        active_grants = db.query(models.TenantQuotaGrant).filter(
            models.TenantQuotaGrant.tenant_id == tenant_id,
            or_(
                models.TenantQuotaGrant.expires_at.is_(None),
                models.TenantQuotaGrant.expires_at > now,
            ),
        ).all()

        # Health
        health_row = db.query(models.TenantHealth).filter_by(tenant_id=tenant_id).first()

        # Notes count
        notes_count = db.query(func.count(models.TenantAdminNote.id)).filter_by(
            tenant_id=tenant_id,
        ).scalar() or 0

        return jsonify({
            "tenant_id": tenant_id,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "phone": user.phone,
                "timezone": user.timezone,
                "signup_at": user.criado_em.isoformat() if user.criado_em else None,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "totp_enabled": bool(user.totp_enabled_at),
            },
            "plan": {
                "key": plan,
                "label": cfg["label"],
                "source": source,
                "price_brl": cfg["price_brl"],
                "limits": cfg["limits"],
                "features": cfg["features"],
            },
            "lifecycle": {
                "is_suspended": bool(user.suspended_at),
                "suspended_at": user.suspended_at.isoformat() if user.suspended_at else None,
                "suspended_by": user.suspended_by,
                "suspension_reason": user.suspension_reason,
                "is_deleted": bool(user.deleted_at),
                "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None,
                "trial_ends_at": user.trial_ends_at.isoformat() if user.trial_ends_at else None,
                "dunning_status": user.dunning_status,
            },
            "metrics": {
                "leads_total": leads_total,
                "leads_30d": leads_30d,
                "msgs_total": msgs_total,
                "msgs_30d": msgs_30d,
            },
            "active_override": {
                "id": active_override.id,
                "plan": active_override.plan,
                "reason": active_override.reason,
                "expires_at": active_override.expires_at.isoformat() if active_override.expires_at else None,
            } if active_override else None,
            "active_grants": [
                {
                    "id": g.id, "kind": g.kind, "amount": g.amount,
                    "used_amount": g.used_amount,
                    "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                    "reason": g.reason,
                } for g in active_grants
            ],
            "health": {
                "score": health_row.score, "band": health_row.band,
                "components": health_row.components,
            } if health_row else None,
            "notes_count": notes_count,
        })
    finally:
        db.close()


# ─── /tenants/<id>/notes (CRUD) ───────────────────────────────────────


@admin_tenants_bp.route("/tenants/<tenant_id>/notes", methods=["GET"])
@login_required
@require_admin
def list_notes(tenant_id: str):
    db = SessionLocal()
    try:
        notes = db.query(models.TenantAdminNote).filter_by(
            tenant_id=tenant_id,
        ).order_by(
            models.TenantAdminNote.pinned.desc(),
            models.TenantAdminNote.created_at.desc(),
        ).all()
        return jsonify({
            "notes": [
                {
                    "id": n.id,
                    "content": n.content,
                    "pinned": n.pinned,
                    "author_admin_id": n.author_admin_id,
                    "created_at": n.created_at.isoformat(),
                    "updated_at": n.updated_at.isoformat() if n.updated_at else None,
                } for n in notes
            ]
        })
    finally:
        db.close()


@admin_tenants_bp.route("/tenants/<tenant_id>/notes", methods=["POST"])
@login_required
@require_admin
def create_note(tenant_id: str):
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    pinned = bool(body.get("pinned"))
    if not content:
        return jsonify({"error": "content_required"}), 422
    if len(content) > 10_000:
        return jsonify({"error": "content_too_long"}), 422

    db = SessionLocal()
    try:
        n = models.TenantAdminNote(
            tenant_id=tenant_id,
            author_admin_id=current_user.id,
            content=content,
            pinned=pinned,
        )
        db.add(n); db.commit(); db.refresh(n)
        return jsonify({
            "id": n.id, "content": n.content, "pinned": n.pinned,
            "created_at": n.created_at.isoformat(),
        }), 201
    finally:
        db.close()


@admin_tenants_bp.route("/tenants/<tenant_id>/notes/<int:note_id>", methods=["PATCH"])
@login_required
@require_admin
def update_note(tenant_id: str, note_id: int):
    body = request.get_json(silent=True) or {}
    db = SessionLocal()
    try:
        n = db.query(models.TenantAdminNote).filter_by(
            id=note_id, tenant_id=tenant_id,
        ).first()
        if not n:
            return jsonify({"error": "note_not_found"}), 404
        if "content" in body:
            content = (body["content"] or "").strip()
            if not content or len(content) > 10_000:
                return jsonify({"error": "content_invalid"}), 422
            n.content = content
        if "pinned" in body:
            n.pinned = bool(body["pinned"])
        n.updated_at = datetime.now(timezone.utc)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@admin_tenants_bp.route("/tenants/<tenant_id>/notes/<int:note_id>", methods=["DELETE"])
@login_required
@require_admin
def delete_note(tenant_id: str, note_id: int):
    db = SessionLocal()
    try:
        n = db.query(models.TenantAdminNote).filter_by(
            id=note_id, tenant_id=tenant_id,
        ).first()
        if not n:
            return jsonify({"error": "note_not_found"}), 404
        db.delete(n); db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
