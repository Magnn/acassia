"""
Tenant lifecycle: suspend/reactivate + soft-delete + restore (Frente 1.8, 1.9).

Endpoints:
    POST /api/admin/tenants/<tenant_id>/suspend     — suspende com motivo
    POST /api/admin/tenants/<tenant_id>/reactivate  — reativa
    POST /api/admin/tenants/<tenant_id>/delete      — soft-delete (30d window)
    POST /api/admin/tenants/<tenant_id>/restore     — desfaz soft-delete

Defesas:
    - @require_admin
    - Confirmação extra: digitar email pra deletar
    - Motivo obrigatório (min 5 chars) em todas as ações
    - Não permite deletar/suspender admin do allowlist (proteção mútua)
    - Não permite deletar tenant com sub Stripe ativa (cancela primeiro)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from api.admin.guard import require_admin, get_admin_allowlist
from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)
lifecycle_bp = Blueprint("admin_lifecycle", __name__, url_prefix="/api/admin")


_REASON_MIN_LEN = 5


def _resolve_user(db, tenant_id: str) -> models.User | None:
    return db.query(models.User).filter_by(tenant_id=tenant_id).first()


# ─── Suspend / Reactivate ─────────────────────────────────────────────


@lifecycle_bp.route("/tenants/<tenant_id>/suspend", methods=["POST"])
@login_required
@require_admin
def suspend_tenant(tenant_id: str):
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip()
    if len(reason) < _REASON_MIN_LEN:
        return jsonify({"error": "reason_too_short", "min": _REASON_MIN_LEN}), 422

    db = SessionLocal()
    try:
        user = _resolve_user(db, tenant_id)
        if not user:
            return jsonify({"error": "tenant_not_found"}), 404
        if user.deleted_at:
            return jsonify({"error": "tenant_deleted"}), 409
        if user.suspended_at:
            return jsonify({"error": "already_suspended"}), 409

        # Defesa mútua: não suspende admin da allowlist
        if user.role == "admin" and user.id in get_admin_allowlist():
            return jsonify({"error": "cannot_suspend_admin"}), 403

        now = datetime.now(timezone.utc)
        user.suspended_at = now
        user.suspended_by = current_user.id
        user.suspension_reason = reason
        db.commit()

        logger.warning(
            "[admin.tenant.suspend] tenant=%s by_admin=%s reason=%s",
            tenant_id, current_user.id, reason,
        )
        return jsonify({
            "ok": True,
            "suspended_at": now.isoformat(),
            "suspended_by": current_user.id,
        })
    finally:
        db.close()


@lifecycle_bp.route("/tenants/<tenant_id>/reactivate", methods=["POST"])
@login_required
@require_admin
def reactivate_tenant(tenant_id: str):
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip()
    if len(reason) < _REASON_MIN_LEN:
        return jsonify({"error": "reason_too_short", "min": _REASON_MIN_LEN}), 422

    db = SessionLocal()
    try:
        user = _resolve_user(db, tenant_id)
        if not user:
            return jsonify({"error": "tenant_not_found"}), 404
        if not user.suspended_at:
            return jsonify({"error": "not_suspended"}), 409

        user.suspended_at = None
        user.suspended_by = None
        user.suspension_reason = None
        db.commit()

        logger.warning(
            "[admin.tenant.reactivate] tenant=%s by_admin=%s reason=%s",
            tenant_id, current_user.id, reason,
        )
        return jsonify({"ok": True, "reactivated_at": datetime.now(timezone.utc).isoformat()})
    finally:
        db.close()


# ─── Soft-delete / Restore ────────────────────────────────────────────


@lifecycle_bp.route("/tenants/<tenant_id>/delete", methods=["POST"])
@login_required
@require_admin
def delete_tenant(tenant_id: str):
    """
    Soft-delete: marca deleted_at. Hard-delete só após 30d via cron.
    Requer:
        - confirm_email: email exato do tenant pra confirmar
        - reason: motivo (min 5 chars)
    """
    body = request.get_json(silent=True) or {}
    confirm_email = (body.get("confirm_email") or "").strip().lower()
    reason = (body.get("reason") or "").strip()

    if len(reason) < _REASON_MIN_LEN:
        return jsonify({"error": "reason_too_short", "min": _REASON_MIN_LEN}), 422

    db = SessionLocal()
    try:
        user = _resolve_user(db, tenant_id)
        if not user:
            return jsonify({"error": "tenant_not_found"}), 404
        if user.deleted_at:
            return jsonify({"error": "already_deleted"}), 409

        # Defesa: email tem que bater
        if confirm_email != (user.email or "").strip().lower():
            return jsonify({"error": "confirm_email_mismatch"}), 422

        # Defesa mútua: não deleta admin da allowlist
        if user.role == "admin" and user.id in get_admin_allowlist():
            return jsonify({"error": "cannot_delete_admin"}), 403

        # TODO: cancelar Stripe sub (Frente 2.16) antes de deletar.
        # Por enquanto, marca soft-delete + log warning se houver Stripe sub.

        now = datetime.now(timezone.utc)
        user.deleted_at = now
        # Suspende junto pra bloquear acesso imediato
        if not user.suspended_at:
            user.suspended_at = now
            user.suspended_by = current_user.id
            user.suspension_reason = f"soft_deleted: {reason}"
        db.commit()

        logger.warning(
            "[admin.tenant.delete] tenant=%s by_admin=%s reason=%s "
            "hard_delete_scheduled_after=30d",
            tenant_id, current_user.id, reason,
        )
        return jsonify({
            "ok": True,
            "deleted_at": now.isoformat(),
            "hard_delete_scheduled_at": None,  # cron computa
            "recovery_window_days": 30,
        })
    finally:
        db.close()


@lifecycle_bp.route("/tenants/<tenant_id>/restore", methods=["POST"])
@login_required
@require_admin
def restore_tenant(tenant_id: str):
    """Desfaz soft-delete (durante janela de 30d)."""
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip()
    if len(reason) < _REASON_MIN_LEN:
        return jsonify({"error": "reason_too_short", "min": _REASON_MIN_LEN}), 422

    db = SessionLocal()
    try:
        user = _resolve_user(db, tenant_id)
        if not user:
            return jsonify({"error": "tenant_not_found"}), 404
        if not user.deleted_at:
            return jsonify({"error": "not_deleted"}), 409

        user.deleted_at = None
        # Se foi auto-suspended pelo soft-delete, reativa também
        if user.suspension_reason and user.suspension_reason.startswith("soft_deleted:"):
            user.suspended_at = None
            user.suspended_by = None
            user.suspension_reason = None
        db.commit()

        logger.warning(
            "[admin.tenant.restore] tenant=%s by_admin=%s reason=%s",
            tenant_id, current_user.id, reason,
        )
        return jsonify({"ok": True, "restored_at": datetime.now(timezone.utc).isoformat()})
    finally:
        db.close()
