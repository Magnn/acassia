"""
Operações comerciais admin: plan override + quota grants + feature flags
+ audit log writer/reader (Frente 1.5, 1.6, 1.10, 1.12).

Endpoints:
    POST /api/admin/tenants/<id>/plan-overrides
    DELETE /api/admin/tenants/<id>/plan-overrides/<override_id>
    GET /api/admin/tenants/<id>/plan-overrides

    POST /api/admin/tenants/<id>/quota-grants
    DELETE /api/admin/tenants/<id>/quota-grants/<grant_id>
    GET /api/admin/tenants/<id>/quota-grants

    GET /api/admin/feature-flags
    POST /api/admin/feature-flags                       (cria/edita global)
    PATCH /api/admin/tenants/<id>/feature-flags/<key>   (override por tenant)
    DELETE /api/admin/tenants/<id>/feature-flags/<key>  (remove override)
    GET /api/admin/tenants/<id>/feature-flags

    GET /api/admin/audit
    GET /api/admin/tenants/<id>/audit
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from api.admin.guard import require_admin
from db import models
from db.database import SessionLocal
import plans as plans_module


logger = logging.getLogger(__name__)
commercial_bp = Blueprint("admin_commercial", __name__, url_prefix="/api/admin")


# ─── Audit log helper ─────────────────────────────────────────────────


def write_audit(
    *,
    event_type: str,
    tenant_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict | None = None,
    db_session=None,
):
    """
    Helper pra qualquer endpoint admin gravar audit. Pega current_user +
    impersonator + ip + ua automaticamente do request context.
    """
    own = db_session is None
    db = db_session or SessionLocal()
    try:
        actor_id = getattr(current_user, "id", None)
        impersonator_id = getattr(current_user, "impersonator_id", None)
        impersonation_id = getattr(current_user, "impersonation_session_id", None)

        ev = models.AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=actor_id,
            impersonator_user_id=impersonator_id,
            impersonation_id=impersonation_id,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            payload=payload or {},
            ip_address=request.remote_addr if request else None,
            user_agent=(request.headers.get("User-Agent", "") if request else "")[:500] or None,
        )
        db.add(ev)
        if own:
            db.commit()
    except Exception as exc:
        logger.warning("[audit] falha gravando evento %s: %s", event_type, exc)
    finally:
        if own:
            db.close()


# ─── Plan overrides (Frente 1.5) ──────────────────────────────────────


@commercial_bp.route("/tenants/<tenant_id>/plan-overrides", methods=["POST"])
@login_required
@require_admin
def create_plan_override(tenant_id: str):
    body = request.get_json(silent=True) or {}
    plan = (body.get("plan") or "").strip().lower()
    duration_days = body.get("duration_days")  # None = permanente
    pauses_stripe = bool(body.get("pauses_stripe", True))
    reason = (body.get("reason") or "").strip()

    if plan not in plans_module.PLANS:
        return jsonify({"error": "plan_invalid", "valid": list(plans_module.PLANS.keys())}), 422
    if len(reason) < 5:
        return jsonify({"error": "reason_too_short", "min": 5}), 422
    if duration_days is not None:
        try:
            duration_days = int(duration_days)
            if duration_days < 1 or duration_days > 3650:  # 10 anos max
                return jsonify({"error": "duration_invalid"}), 422
        except (TypeError, ValueError):
            return jsonify({"error": "duration_invalid"}), 422

    db = SessionLocal()
    try:
        target = db.query(models.User).filter_by(tenant_id=tenant_id).first()
        if not target:
            return jsonify({"error": "tenant_not_found"}), 404
        if target.deleted_at:
            return jsonify({"error": "tenant_deleted"}), 409

        # Revoga qualquer override ativo anterior
        prev = db.query(models.TenantPlanOverride).filter(
            models.TenantPlanOverride.tenant_id == tenant_id,
            models.TenantPlanOverride.revoked_at.is_(None),
        ).all()
        now = datetime.now(timezone.utc)
        for p in prev:
            p.revoked_at = now
            p.revoked_by = current_user.id
            p.revoked_reason = "superseded_by_new_override"

        expires_at = (now + timedelta(days=duration_days)) if duration_days else None
        ovr = models.TenantPlanOverride(
            tenant_id=tenant_id,
            plan=plan,
            granted_by_admin_id=current_user.id,
            reason=reason,
            starts_at=now,
            expires_at=expires_at,
            pauses_stripe=pauses_stripe,
        )
        db.add(ovr)
        db.commit()
        db.refresh(ovr)

        write_audit(
            event_type="admin.plan_override.created",
            tenant_id=tenant_id,
            target_type="plan_override",
            target_id=str(ovr.id),
            payload={"plan": plan, "duration_days": duration_days, "pauses_stripe": pauses_stripe, "reason": reason},
            db_session=db,
        )
        db.commit()

        new_plan, source = plans_module.effective_plan(tenant_id, db_session=db)
        return jsonify({
            "ok": True,
            "override": {
                "id": ovr.id,
                "plan": ovr.plan,
                "expires_at": ovr.expires_at.isoformat() if ovr.expires_at else None,
                "starts_at": ovr.starts_at.isoformat(),
                "pauses_stripe": ovr.pauses_stripe,
                "reason": ovr.reason,
            },
            "effective_plan_now": new_plan,
            "effective_source": source,
        }), 201
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/plan-overrides/<int:override_id>", methods=["DELETE"])
@login_required
@require_admin
def revoke_plan_override(tenant_id: str, override_id: int):
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip() or "manual_revoke"

    db = SessionLocal()
    try:
        ovr = db.query(models.TenantPlanOverride).filter_by(
            id=override_id, tenant_id=tenant_id,
        ).first()
        if not ovr:
            return jsonify({"error": "override_not_found"}), 404
        if ovr.revoked_at:
            return jsonify({"error": "already_revoked"}), 409

        ovr.revoked_at = datetime.now(timezone.utc)
        ovr.revoked_by = current_user.id
        ovr.revoked_reason = reason
        db.commit()

        write_audit(
            event_type="admin.plan_override.revoked",
            tenant_id=tenant_id,
            target_type="plan_override",
            target_id=str(override_id),
            payload={"reason": reason},
            db_session=db,
        )
        db.commit()

        return jsonify({"ok": True})
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/plan-overrides", methods=["GET"])
@login_required
@require_admin
def list_plan_overrides(tenant_id: str):
    include_revoked = request.args.get("include") == "all"
    db = SessionLocal()
    try:
        q = db.query(models.TenantPlanOverride).filter_by(tenant_id=tenant_id)
        if not include_revoked:
            q = q.filter(models.TenantPlanOverride.revoked_at.is_(None))
        overrides = q.order_by(models.TenantPlanOverride.created_at.desc()).all()
        return jsonify({
            "overrides": [
                {
                    "id": o.id,
                    "plan": o.plan,
                    "reason": o.reason,
                    "starts_at": o.starts_at.isoformat(),
                    "expires_at": o.expires_at.isoformat() if o.expires_at else None,
                    "pauses_stripe": o.pauses_stripe,
                    "revoked_at": o.revoked_at.isoformat() if o.revoked_at else None,
                    "revoked_reason": o.revoked_reason,
                    "granted_by_admin_id": o.granted_by_admin_id,
                    "created_at": o.created_at.isoformat(),
                } for o in overrides
            ]
        })
    finally:
        db.close()


# ─── Quota grants (Frente 1.6) ────────────────────────────────────────


VALID_QUOTA_KINDS = {"gemini_tokens_month", "wa_msgs_month", "leads_month"}


@commercial_bp.route("/tenants/<tenant_id>/quota-grants", methods=["POST"])
@login_required
@require_admin
def create_quota_grant(tenant_id: str):
    body = request.get_json(silent=True) or {}
    kind = (body.get("kind") or "").strip()
    amount = body.get("amount")
    duration_days = body.get("duration_days")
    reason = (body.get("reason") or "").strip()

    if kind not in VALID_QUOTA_KINDS:
        return jsonify({"error": "kind_invalid", "valid": sorted(VALID_QUOTA_KINDS)}), 422
    try:
        amount = int(amount)
        if amount < 1 or amount > 100_000_000:
            return jsonify({"error": "amount_invalid"}), 422
    except (TypeError, ValueError):
        return jsonify({"error": "amount_invalid"}), 422
    if len(reason) < 5:
        return jsonify({"error": "reason_too_short", "min": 5}), 422
    expires_at = None
    if duration_days is not None:
        try:
            duration_days = int(duration_days)
            if duration_days < 1 or duration_days > 365:
                return jsonify({"error": "duration_invalid"}), 422
            expires_at = datetime.now(timezone.utc) + timedelta(days=duration_days)
        except (TypeError, ValueError):
            return jsonify({"error": "duration_invalid"}), 422

    db = SessionLocal()
    try:
        target = db.query(models.User).filter_by(tenant_id=tenant_id).first()
        if not target:
            return jsonify({"error": "tenant_not_found"}), 404

        grant = models.TenantQuotaGrant(
            tenant_id=tenant_id,
            kind=kind,
            amount=amount,
            expires_at=expires_at,
            granted_by=current_user.id,
            reason=reason,
        )
        db.add(grant)
        db.commit()
        db.refresh(grant)

        write_audit(
            event_type="admin.quota_grant.created",
            tenant_id=tenant_id,
            target_type="quota_grant",
            target_id=str(grant.id),
            payload={"kind": kind, "amount": amount, "duration_days": duration_days, "reason": reason},
            db_session=db,
        )
        db.commit()

        new_quota = plans_module.effective_quota(tenant_id, kind, db_session=db)
        return jsonify({
            "ok": True,
            "grant": {
                "id": grant.id, "kind": kind, "amount": amount,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "reason": reason,
            },
            "new_effective_quota": new_quota,
        }), 201
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/quota-grants/<int:grant_id>", methods=["DELETE"])
@login_required
@require_admin
def revoke_quota_grant(tenant_id: str, grant_id: int):
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip() or "manual_revoke"
    db = SessionLocal()
    try:
        g = db.query(models.TenantQuotaGrant).filter_by(id=grant_id, tenant_id=tenant_id).first()
        if not g:
            return jsonify({"error": "grant_not_found"}), 404
        # Soft-revoke: setar expires_at pra agora
        g.expires_at = datetime.now(timezone.utc)
        db.commit()

        write_audit(
            event_type="admin.quota_grant.revoked",
            tenant_id=tenant_id, target_type="quota_grant", target_id=str(grant_id),
            payload={"reason": reason}, db_session=db,
        )
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/quota-grants", methods=["GET"])
@login_required
@require_admin
def list_quota_grants(tenant_id: str):
    include_expired = request.args.get("include") == "all"
    db = SessionLocal()
    try:
        q = db.query(models.TenantQuotaGrant).filter_by(tenant_id=tenant_id)
        if not include_expired:
            now = datetime.now(timezone.utc)
            q = q.filter(or_(
                models.TenantQuotaGrant.expires_at.is_(None),
                models.TenantQuotaGrant.expires_at > now,
            ))
        grants = q.order_by(models.TenantQuotaGrant.created_at.desc()).all()
        return jsonify({
            "grants": [
                {
                    "id": g.id, "kind": g.kind, "amount": g.amount, "used_amount": g.used_amount,
                    "expires_at": g.expires_at.isoformat() if g.expires_at else None,
                    "reason": g.reason, "granted_by": g.granted_by,
                    "created_at": g.created_at.isoformat(),
                } for g in grants
            ]
        })
    finally:
        db.close()


# ─── Feature flags (Frente 1.10) ──────────────────────────────────────


@commercial_bp.route("/feature-flags", methods=["GET"])
@login_required
@require_admin
def list_global_flags():
    db = SessionLocal()
    try:
        flags = db.query(models.FeatureFlag).all()
        return jsonify({
            "flags": [
                {
                    "key": f.key,
                    "description": f.description,
                    "default_value": f.default_value,
                    "rollout_pct": f.rollout_pct,
                    "created_at": f.created_at.isoformat(),
                } for f in flags
            ]
        })
    finally:
        db.close()


@commercial_bp.route("/feature-flags", methods=["POST"])
@login_required
@require_admin
def upsert_global_flag():
    body = request.get_json(silent=True) or {}
    key = (body.get("key") or "").strip().lower()
    description = (body.get("description") or "").strip() or None
    default_value = bool(body.get("default_value", False))
    rollout_pct = int(body.get("rollout_pct", 0))

    if not key or not key.replace("_", "").replace(".", "").isalnum():
        return jsonify({"error": "key_invalid"}), 422
    if rollout_pct < 0 or rollout_pct > 100:
        return jsonify({"error": "rollout_pct_invalid"}), 422

    db = SessionLocal()
    try:
        flag = db.query(models.FeatureFlag).filter_by(key=key).first()
        if flag:
            flag.description = description
            flag.default_value = default_value
            flag.rollout_pct = rollout_pct
            action = "updated"
        else:
            flag = models.FeatureFlag(
                key=key, description=description,
                default_value=default_value, rollout_pct=rollout_pct,
            )
            db.add(flag)
            action = "created"
        db.commit()

        write_audit(
            event_type=f"admin.feature_flag.{action}",
            target_type="feature_flag", target_id=key,
            payload={"description": description, "default_value": default_value, "rollout_pct": rollout_pct},
            db_session=db,
        )
        db.commit()
        return jsonify({"ok": True, "action": action, "flag": {"key": key}})
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/feature-flags", methods=["GET"])
@login_required
@require_admin
def list_tenant_flags(tenant_id: str):
    """Resolve flags pra esse tenant (override > rollout > default)."""
    db = SessionLocal()
    try:
        all_flags = db.query(models.FeatureFlag).all()
        overrides = {
            o.flag_key: o for o in db.query(models.TenantFeatureFlag)
            .filter_by(tenant_id=tenant_id).all()
        }

        out = []
        for f in all_flags:
            if f.key in overrides:
                source = "tenant_override"
                value = overrides[f.key].enabled
            elif f.rollout_pct > 0:
                source = "rollout"
                value = (hash(tenant_id + f.key) % 100) < f.rollout_pct
            else:
                source = "default"
                value = f.default_value
            out.append({
                "key": f.key,
                "description": f.description,
                "value": value,
                "source": source,
                "default_value": f.default_value,
                "rollout_pct": f.rollout_pct,
                "tenant_override": (
                    {
                        "enabled": overrides[f.key].enabled,
                        "set_at": overrides[f.key].set_at.isoformat(),
                    } if f.key in overrides else None
                ),
            })
        return jsonify({"flags": out})
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/feature-flags/<key>", methods=["PUT"])
@login_required
@require_admin
def set_tenant_flag(tenant_id: str, key: str):
    body = request.get_json(silent=True) or {}
    enabled = body.get("enabled")
    if enabled is None or not isinstance(enabled, bool):
        return jsonify({"error": "enabled_required"}), 422

    db = SessionLocal()
    try:
        flag = db.query(models.FeatureFlag).filter_by(key=key).first()
        if not flag:
            return jsonify({"error": "flag_not_found"}), 404

        existing = db.query(models.TenantFeatureFlag).filter_by(
            tenant_id=tenant_id, flag_key=key,
        ).first()
        if existing:
            existing.enabled = enabled
            existing.set_by = current_user.id
            existing.set_at = datetime.now(timezone.utc)
        else:
            db.add(models.TenantFeatureFlag(
                tenant_id=tenant_id, flag_key=key, enabled=enabled,
                set_by=current_user.id,
            ))
        db.commit()

        write_audit(
            event_type="admin.feature_flag.tenant_set",
            tenant_id=tenant_id, target_type="feature_flag", target_id=key,
            payload={"enabled": enabled},
            db_session=db,
        )
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@commercial_bp.route("/tenants/<tenant_id>/feature-flags/<key>", methods=["DELETE"])
@login_required
@require_admin
def remove_tenant_flag(tenant_id: str, key: str):
    db = SessionLocal()
    try:
        existing = db.query(models.TenantFeatureFlag).filter_by(
            tenant_id=tenant_id, flag_key=key,
        ).first()
        if not existing:
            return jsonify({"error": "override_not_found"}), 404
        db.delete(existing)
        db.commit()

        write_audit(
            event_type="admin.feature_flag.tenant_removed",
            tenant_id=tenant_id, target_type="feature_flag", target_id=key,
            db_session=db,
        )
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Audit log viewer (Frente 1.12) ───────────────────────────────────


def _query_audit(tenant_id_filter: str | None = None):
    """Helper compartilhado pra /audit e /tenants/<id>/audit."""
    args = request.args
    limit = min(int(args.get("limit") or 50), 500)
    cursor = int(args.get("cursor") or 0)
    event_type = args.get("event_type")
    actor_id = args.get("actor_user_id")
    tenant_id = tenant_id_filter or args.get("tenant_id")
    since = args.get("since")
    until = args.get("until")
    search = (args.get("search") or "").strip()

    db = SessionLocal()
    try:
        q = db.query(models.AuditEvent)
        if event_type:
            if event_type.endswith("*"):
                q = q.filter(models.AuditEvent.event_type.like(event_type[:-1] + "%"))
            else:
                q = q.filter(models.AuditEvent.event_type == event_type)
        if actor_id and actor_id.isdigit():
            q = q.filter(models.AuditEvent.actor_user_id == int(actor_id))
        if tenant_id:
            q = q.filter(models.AuditEvent.tenant_id == tenant_id)
        if since:
            try:
                q = q.filter(models.AuditEvent.timestamp >= datetime.fromisoformat(since))
            except ValueError:
                return jsonify({"error": "since_invalid"}), 422
        if until:
            try:
                q = q.filter(models.AuditEvent.timestamp <= datetime.fromisoformat(until))
            except ValueError:
                return jsonify({"error": "until_invalid"}), 422
        if search:
            like = f"%{search.lower()}%"
            q = q.filter(or_(
                models.AuditEvent.event_type.like(like),
                models.AuditEvent.target_id.like(like),
            ))

        total = q.count()
        events = q.order_by(models.AuditEvent.timestamp.desc()).offset(cursor).limit(limit).all()
        return jsonify({
            "events": [
                {
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "tenant_id": e.tenant_id,
                    "actor_user_id": e.actor_user_id,
                    "impersonator_user_id": e.impersonator_user_id,
                    "impersonation_id": e.impersonation_id,
                    "event_type": e.event_type,
                    "target_type": e.target_type,
                    "target_id": e.target_id,
                    "payload": e.payload,
                    "ip_address": e.ip_address,
                } for e in events
            ],
            "total": total,
            "cursor_next": cursor + limit if (cursor + limit) < total else None,
        })
    finally:
        db.close()


@commercial_bp.route("/audit", methods=["GET"])
@login_required
@require_admin
def audit_log():
    return _query_audit()


@commercial_bp.route("/tenants/<tenant_id>/audit", methods=["GET"])
@login_required
@require_admin
def tenant_audit(tenant_id: str):
    return _query_audit(tenant_id_filter=tenant_id)
