"""
Admin impersonate (Frente 1.2).

Endpoints:
    POST /api/admin/impersonate         — inicia sessão (requer reason+totp+duration)
    POST /api/admin/impersonate/stop    — encerra sessão atual
    GET  /api/admin/impersonate/active  — retorna sessão ativa do admin atual
    GET  /api/admin/impersonations      — histórico (read-only)

Defesas:
    - Não pode impersonar outro admin
    - Não pode impersonar a si mesmo (CHECK constraint no schema)
    - Não pode impersonar tenant suspenso/deletado sem ativar primeiro
    - Reason obrigatório, min 10 chars
    - TOTP revalidado (segunda camada além do cookie 2FA)
    - Sessão expira em 1h max (configurável via duration)
    - Cookie distinto do session normal pra não vazar sessões em outras tabs
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

import pyotp
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from itsdangerous import BadSignature, URLSafeTimedSerializer

from api.admin.guard import require_admin
from db import models
from db.database import SessionLocal
from extensions import limiter


logger = logging.getLogger(__name__)
impersonate_bp = Blueprint("admin_impersonate", __name__, url_prefix="/api/admin")


_IMP_COOKIE = "acassia_imp_session"
_IMP_SALT = "impersonate-cookie-v1"
_REASON_MIN_LEN = 10
_DURATION_MIN_DEFAULT = 60
_DURATION_MIN_MAX = 240  # 4h


def _imp_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_IMP_SALT)


def get_active_impersonation_session_id() -> int | None:
    """
    Retorna ID da sessão de impersonate ativa via cookie, ou None.
    Usado pelo `current_user` resolver (próximo passo).
    """
    raw = request.cookies.get(_IMP_COOKIE)
    if not raw:
        return None
    try:
        # max_age 4h pra cobrir _DURATION_MIN_MAX
        data = _imp_serializer().loads(raw, max_age=_DURATION_MIN_MAX * 60 + 60)
    except BadSignature:
        return None
    return data.get("session_id")


# ─── Endpoints ────────────────────────────────────────────────────────


@impersonate_bp.route("/impersonate", methods=["POST"])
@login_required
@require_admin
@limiter.limit("10/minute")
def start_impersonate():
    body = request.get_json(silent=True) or {}
    target_user_id = body.get("target_user_id")
    reason = (body.get("reason") or "").strip()
    duration_min = int(body.get("duration_min") or _DURATION_MIN_DEFAULT)
    totp_code = (body.get("totp") or "").strip()

    # Validações
    if not target_user_id or not isinstance(target_user_id, int):
        return jsonify({"error": "target_user_id_required"}), 422
    if len(reason) < _REASON_MIN_LEN:
        return jsonify({
            "error": "reason_too_short",
            "min": _REASON_MIN_LEN,
        }), 422
    if duration_min < 5 or duration_min > _DURATION_MIN_MAX:
        return jsonify({
            "error": "duration_invalid",
            "min": 5, "max": _DURATION_MIN_MAX,
        }), 422
    if not totp_code:
        return jsonify({"error": "totp_required"}), 401
    if target_user_id == current_user.id:
        return jsonify({"error": "cannot_self_impersonate"}), 403

    db = SessionLocal()
    try:
        # Re-valida TOTP (defesa extra mesmo com cookie 2FA)
        admin_user = db.query(models.User).filter_by(id=current_user.id).first()
        if not admin_user or not admin_user.totp_secret:
            return jsonify({"error": "admin_2fa_not_enabled"}), 401
        if not pyotp.TOTP(admin_user.totp_secret).verify(totp_code, valid_window=1):
            logger.warning(
                "[admin.impersonate.totp_fail] admin_id=%s target=%s",
                current_user.id, target_user_id,
            )
            return jsonify({"error": "totp_invalid"}), 401

        # Resolve target
        target = db.query(models.User).filter_by(id=target_user_id).first()
        if not target:
            return jsonify({"error": "target_not_found"}), 404
        if target.role == "admin":
            return jsonify({"error": "cannot_impersonate_admin"}), 403
        if target.deleted_at is not None:
            return jsonify({"error": "target_deleted"}), 403
        if target.suspended_at is not None:
            return jsonify({"error": "target_suspended"}), 403
        if not target.is_active:
            return jsonify({"error": "target_inactive"}), 403

        # Encerra sessões anteriores não-fechadas do mesmo admin
        prev = db.query(models.ImpersonationSession).filter(
            models.ImpersonationSession.admin_user_id == current_user.id,
            models.ImpersonationSession.ended_at.is_(None),
        ).all()
        for p in prev:
            p.ended_at = datetime.now(timezone.utc)
            p.end_reason = "superseded"

        # Cria sessão
        now = datetime.now(timezone.utc)
        sess = models.ImpersonationSession(
            admin_user_id=current_user.id,
            target_user_id=target.id,
            target_tenant_id=target.tenant_id,
            reason=reason,
            started_at=now,
            expires_at=now + timedelta(minutes=duration_min),
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:500],
            actions_count=0,
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        sess_id = sess.id
    finally:
        db.close()

    logger.warning(
        "[admin.impersonate.start] admin_id=%s target_user_id=%s tenant=%s session_id=%s "
        "duration_min=%s reason=%s",
        current_user.id, target_user_id, target.tenant_id, sess_id, duration_min, reason,
    )

    # Emite cookie de impersonate (httpOnly)
    resp = jsonify({
        "ok": True,
        "session_id": sess_id,
        "target": {
            "user_id": target.id,
            "email": target.email,
            "name": target.name,
            "tenant_id": target.tenant_id,
        },
        "expires_at": (now + timedelta(minutes=duration_min)).isoformat(),
        "duration_min": duration_min,
        "redirect_to": "/dashboard",
    })
    is_secure = request.is_secure or False
    token = _imp_serializer().dumps({"session_id": sess_id})
    resp.set_cookie(
        _IMP_COOKIE,
        token,
        max_age=duration_min * 60,
        httponly=True,
        secure=is_secure,
        samesite="Lax",  # Lax pra navegação cross-page funcionar
        path="/",
    )
    return resp


@impersonate_bp.route("/impersonate/stop", methods=["POST"])
@login_required
def stop_impersonate():
    """
    Encerra a sessão de impersonate ativa. NOTA: NÃO usa @require_admin
    porque pode ser chamado durante uma sessão impersonate (current_user
    seria o target, não o admin).
    """
    sess_id = get_active_impersonation_session_id()
    if not sess_id:
        # Idempotente — não tinha sessão, ok
        resp = jsonify({"ok": True, "redirect_to": "/admin/tenants"})
        resp.delete_cookie(_IMP_COOKIE, path="/")
        return resp

    db = SessionLocal()
    try:
        sess = db.query(models.ImpersonationSession).filter_by(id=sess_id).first()
        if sess and sess.ended_at is None:
            sess.ended_at = datetime.now(timezone.utc)
            sess.end_reason = "manual"
            db.commit()
            logger.warning(
                "[admin.impersonate.stop] session_id=%s admin_id=%s actions=%s",
                sess_id, sess.admin_user_id, sess.actions_count,
            )
    finally:
        db.close()

    resp = jsonify({"ok": True, "redirect_to": "/admin/tenants"})
    resp.delete_cookie(_IMP_COOKIE, path="/")
    return resp


@impersonate_bp.route("/impersonate/active", methods=["GET"])
@login_required
def active_impersonation():
    """
    Retorna info da sessão de impersonate ativa (se houver).
    Frontend usa pra renderizar o banner persistente.
    """
    sess_id = get_active_impersonation_session_id()
    if not sess_id:
        return jsonify({"active": False})

    db = SessionLocal()
    try:
        sess = db.query(models.ImpersonationSession).filter_by(id=sess_id).first()
        if not sess or sess.ended_at is not None:
            return jsonify({"active": False})

        target = db.query(models.User).filter_by(id=sess.target_user_id).first()
        admin = db.query(models.User).filter_by(id=sess.admin_user_id).first()

        # Auto-expire check (normaliza tz porque SQLite armazena naive)
        now = datetime.now(timezone.utc)
        sess_expires = sess.expires_at
        if sess_expires.tzinfo is None:
            sess_expires = sess_expires.replace(tzinfo=timezone.utc)
        if sess_expires < now:
            sess.ended_at = now
            sess.end_reason = "expired"
            db.commit()
            return jsonify({"active": False, "reason": "expired"})

        return jsonify({
            "active": True,
            "session_id": sess.id,
            "started_at": sess.started_at.isoformat(),
            "expires_at": sess_expires.isoformat(),
            "expires_in_s": int((sess_expires - now).total_seconds()),
            "reason": sess.reason,
            "target": {
                "user_id": target.id if target else None,
                "email": target.email if target else "deleted",
                "name": target.name if target else None,
                "tenant_id": sess.target_tenant_id,
            },
            "admin": {
                "user_id": admin.id if admin else None,
                "email": admin.email if admin else "deleted",
            },
        })
    finally:
        db.close()


@impersonate_bp.route("/impersonations", methods=["GET"])
@login_required
@require_admin
def list_impersonations():
    """Histórico de sessões impersonate (filtros opcionais)."""
    args = request.args
    admin_id = args.get("admin_id")
    tenant_id = args.get("tenant_id")
    limit = min(int(args.get("limit") or 50), 200)
    cursor = int(args.get("cursor") or 0)

    db = SessionLocal()
    try:
        q = db.query(models.ImpersonationSession)
        if admin_id and admin_id.isdigit():
            q = q.filter(models.ImpersonationSession.admin_user_id == int(admin_id))
        if tenant_id:
            q = q.filter(models.ImpersonationSession.target_tenant_id == tenant_id)
        q = q.order_by(models.ImpersonationSession.started_at.desc())
        total = q.count()
        sessions = q.offset(cursor).limit(limit).all()
        return jsonify({
            "sessions": [
                {
                    "id": s.id,
                    "admin_user_id": s.admin_user_id,
                    "target_user_id": s.target_user_id,
                    "target_tenant_id": s.target_tenant_id,
                    "reason": s.reason,
                    "started_at": s.started_at.isoformat(),
                    "expires_at": s.expires_at.isoformat(),
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                    "end_reason": s.end_reason,
                    "ip_address": s.ip_address,
                    "actions_count": s.actions_count,
                } for s in sessions
            ],
            "total": total,
            "cursor_next": cursor + limit if (cursor + limit) < total else None,
        })
    finally:
        db.close()
