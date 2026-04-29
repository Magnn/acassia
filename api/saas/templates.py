"""
Endpoints de Flow Templates (Frente 5.3).

Lista templates pré-construídos pra acelerar onboarding e clona pro tenant.

Endpoints:
    GET /saas/templates              — lista templates oficiais + marketplace
    GET /saas/templates/<id>         — detalhes de um template
    POST /saas/templates/<id>/apply  — clona template pro tenant
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
templates_bp = Blueprint("saas_templates", __name__, url_prefix="/saas/templates")


@templates_bp.route("", methods=["GET"])
@login_required
def list_templates():
    """Lista templates disponíveis. Filtros opcionais: category, official_only."""
    category = request.args.get("category")
    official_only = request.args.get("official_only", "true").lower() == "true"

    db = SessionLocal()
    try:
        q = db.query(models.FlowTemplate)
        if official_only:
            q = q.filter_by(is_official=True)
        if category:
            q = q.filter_by(category=category)
        items = q.order_by(models.FlowTemplate.usage_count.desc()).all()
        return jsonify({
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "ticket_brl_avg": t.ticket_brl_avg,
                    "preview_image_url": t.preview_image_url,
                    "usage_count": t.usage_count,
                    "is_official": t.is_official,
                    "node_count": len((t.blueprint_json or {}).get("nodes", [])),
                    "price_brl_cents": t.price_brl_cents,
                } for t in items
            ]
        })
    finally:
        db.close()


@templates_bp.route("/<template_id>", methods=["GET"])
@login_required
def get_template(template_id: str):
    db = SessionLocal()
    try:
        t = db.query(models.FlowTemplate).filter_by(id=template_id).first()
        if not t:
            return jsonify({"error": "template_not_found"}), 404
        return jsonify({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category,
            "ticket_brl_avg": t.ticket_brl_avg,
            "blueprint_json": t.blueprint_json,
            "agent_json": t.agent_json,
            "usage_count": t.usage_count,
            "is_official": t.is_official,
            "node_count": len((t.blueprint_json or {}).get("nodes", [])),
        })
    finally:
        db.close()


@templates_bp.route("/<template_id>/apply", methods=["POST"])
@login_required
def apply_template(template_id: str):
    """
    Clona template pro tenant: cria FlowBlueprint + StudioAgent.
    Body opcional: {custom_title?: string, custom_slug?: string}.

    Quota check: respeita state quota de flows.
    """
    body = request.get_json(silent=True) or {}
    custom_title = (body.get("custom_title") or "").strip()
    custom_slug = (body.get("custom_slug") or "").strip().lower()

    tenant_id = current_user.tenant_id

    db = SessionLocal()
    try:
        tpl = db.query(models.FlowTemplate).filter_by(id=template_id).first()
        if not tpl:
            return jsonify({"error": "template_not_found"}), 404

        # Quota check (Frente 2.7)
        try:
            import quota
            current = db.query(models.FlowBlueprint).filter_by(tenant_id=tenant_id).count()
            allowed, current_count, limit = quota.check_state_quota(
                tenant_id, "flows", current, db_session=db,
            )
            if not allowed:
                return jsonify({
                    "error": "quota_exceeded", "kind": "flows",
                    "current": current_count, "limit": limit,
                    "message": f"Seu plano permite {limit} fluxo(s). Faça upgrade pra criar mais.",
                }), 402
        except Exception:
            pass

        # Slug único
        import re
        title = custom_title or tpl.name
        slug = custom_slug or re.sub(r"[^a-z0-9_]+", "_", tpl.name.lower()).strip("_")[:120] or "fluxo"
        # Garante unicidade
        base_slug = slug
        suffix = 1
        while db.query(models.FlowBlueprint).filter_by(tenant_id=tenant_id, slug=slug).first():
            slug = f"{base_slug}_{suffix}"
            suffix += 1

        # Cria blueprint
        bp = models.FlowBlueprint(
            tenant_id=tenant_id,
            slug=slug[:128],
            title=title[:300],
            body_json=tpl.blueprint_json or {},
        )
        db.add(bp)

        # Cria agente (se template tem agent_json)
        agent_id = None
        if tpl.agent_json:
            try:
                agents_quota_current = db.query(models.StudioAgent).filter_by(tenant_id=tenant_id).count()
                allowed_agent, _, _ = quota.check_state_quota(
                    tenant_id, "agents", agents_quota_current, db_session=db,
                )
                if allowed_agent:
                    agent = models.StudioAgent(
                        tenant_id=tenant_id,
                        name=f"{tpl.name} — Persona",
                        avatar="#7c3aed",
                        draft_json=tpl.agent_json,
                    )
                    db.add(agent)
                    db.flush()
                    agent_id = agent.id
            except Exception:
                pass  # falha em agente não bloqueia template apply

        # Increment usage_count
        tpl.usage_count = (tpl.usage_count or 0) + 1

        db.commit()
        db.refresh(bp)

        # Audit
        try:
            db.add(models.AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=current_user.id,
                event_type="template.applied",
                target_type="flow_template",
                target_id=tpl.id,
                payload={"template_name": tpl.name, "blueprint_id": bp.id, "agent_id": agent_id},
            ))
            db.commit()
        except Exception:
            pass

        logger.info(
            "[templates.applied] tenant=%s template=%s blueprint=%s agent=%s",
            tenant_id, template_id, bp.id, agent_id,
        )

        return jsonify({
            "ok": True,
            "blueprint_id": bp.id,
            "blueprint_slug": bp.slug,
            "agent_id": agent_id,
            "redirect": f"/flows/{bp.id}",
        }), 201
    finally:
        db.close()
