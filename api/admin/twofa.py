"""
2FA TOTP — setup, challenge, recovery codes (Frente 1.1, 8.1).

Endpoints:
    POST /admin/2fa/setup       → gera secret + QR code (não persiste até confirm)
    POST /admin/2fa/setup/confirm → confirma TOTP + persiste secret + recovery codes
    POST /admin/2fa/challenge   → valida TOTP, seta cookie admin
    POST /admin/2fa/recover     → valida recovery code, seta cookie admin
    POST /admin/2fa/disable     → desabilita 2FA (requer TOTP atual)
    GET  /admin/2fa/status      → estado do 2FA do user logado

Recovery codes: 10 códigos one-time hash-stored. User vê apenas 1x.
"""

from __future__ import annotations

import base64
import hashlib
import io
import logging
import secrets
from datetime import datetime, timezone

import bcrypt
import pyotp
import qrcode
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required

from api.admin.guard import (
    _ADMIN_2FA_COOKIE,
    issue_admin_2fa_cookie,
    revoke_admin_2fa_cookie,
)
from db import models
from db.database import SessionLocal
from extensions import limiter


logger = logging.getLogger(__name__)
twofa_bp = Blueprint("admin_twofa", __name__, url_prefix="/admin/2fa")


_TOTP_ISSUER = "Meu Mistério"
_RECOVERY_CODES_COUNT = 10


# ─── Helpers ─────────────────────────────────────────────────────────


def _generate_recovery_codes() -> list[str]:
    """10 códigos formato XXXX-XXXX (8 chars hex)."""
    out = []
    for _ in range(_RECOVERY_CODES_COUNT):
        raw = secrets.token_hex(4).upper()  # 8 chars
        out.append(f"{raw[:4]}-{raw[4:]}")
    return out


def _hash_recovery(code: str) -> str:
    """bcrypt do código (case-insensitive, sem hífen)."""
    normalized = code.replace("-", "").upper().encode()
    return bcrypt.hashpw(normalized, bcrypt.gensalt(rounds=10)).decode()


def _verify_recovery(code: str, hashed: str) -> bool:
    normalized = code.replace("-", "").upper().encode()
    try:
        return bcrypt.checkpw(normalized, hashed.encode())
    except (ValueError, TypeError):
        return False


def _qr_code_data_url(uri: str) -> str:
    """Gera PNG do QR code → data URL base64 inline."""
    img = qrcode.make(uri, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ─── Endpoints ────────────────────────────────────────────────────────


@twofa_bp.route("/status", methods=["GET"])
@login_required
def status():
    """Retorna se 2FA está ativo + última verificação cookie."""
    enabled = bool(getattr(current_user, "totp_enabled_at", None))
    has_recovery_codes = False
    if enabled:
        db = SessionLocal()
        try:
            u = db.query(models.User).filter_by(id=current_user.id).first()
            if u and u.totp_recovery_codes:
                has_recovery_codes = (
                    isinstance(u.totp_recovery_codes, list)
                    and len(u.totp_recovery_codes) > 0
                )
        finally:
            db.close()
    cookie_set = bool(request.cookies.get(_ADMIN_2FA_COOKIE))
    return jsonify({
        "enabled": enabled,
        "has_recovery_codes": has_recovery_codes,
        "cookie_present": cookie_set,
    })


@twofa_bp.route("/setup", methods=["POST"])
@login_required
@limiter.limit("5/minute")
def setup_init():
    """
    Inicia setup: gera secret novo + URI TOTP + QR code data URL.
    NÃO persiste — usuário precisa confirmar com TOTP em /confirm.
    Secret vai num token assinado de curta duração.
    """
    if getattr(current_user, "totp_enabled_at", None):
        return jsonify({"error": "already_enabled"}), 400

    secret = pyotp.random_base32()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=_TOTP_ISSUER,
    )

    # Token assinado contendo o secret (frontend envia de volta no confirm)
    from itsdangerous import URLSafeTimedSerializer
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="2fa-setup-v1")
    setup_token = s.dumps({"secret": secret, "uid": current_user.id})

    return jsonify({
        "qr_data_url": _qr_code_data_url(uri),
        "secret": secret,  # mostra pra user salvar manual também
        "uri": uri,
        "setup_token": setup_token,
    })


@twofa_bp.route("/setup/confirm", methods=["POST"])
@login_required
@limiter.limit("10/minute")
def setup_confirm():
    """
    Confirma setup: valida TOTP contra secret do setup_token, persiste,
    gera recovery codes (mostrados 1x), e emite cookie admin 2FA.
    """
    body = request.get_json(silent=True) or {}
    totp_code = (body.get("totp") or "").strip()
    setup_token = body.get("setup_token") or ""

    if not totp_code or not setup_token:
        return jsonify({"error": "totp_and_setup_token_required"}), 400

    from itsdangerous import URLSafeTimedSerializer, BadSignature
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="2fa-setup-v1")
    try:
        data = s.loads(setup_token, max_age=600)  # 10min pra confirmar
    except BadSignature:
        return jsonify({"error": "setup_token_invalid_or_expired"}), 400

    if data.get("uid") != current_user.id:
        return jsonify({"error": "setup_token_user_mismatch"}), 400

    secret = data.get("secret")
    if not pyotp.TOTP(secret).verify(totp_code, valid_window=1):
        return jsonify({"error": "totp_invalid"}), 401

    # Gera recovery codes
    recovery_plain = _generate_recovery_codes()
    recovery_hashed = [_hash_recovery(c) for c in recovery_plain]

    # Persiste
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        if not user:
            return jsonify({"error": "user_not_found"}), 404
        user.totp_secret = secret
        user.totp_enabled_at = datetime.now(timezone.utc)
        user.totp_recovery_codes = recovery_hashed
        db.commit()
    finally:
        db.close()

    logger.info("[admin.2fa.enabled] user_id=%s", current_user.id)

    # Emite cookie 2FA imediatamente (user já validou TOTP)
    resp = jsonify({
        "ok": True,
        "recovery_codes": recovery_plain,
        "warning": "Salve esses códigos em local seguro — você verá apenas uma vez.",
    })
    issue_admin_2fa_cookie(resp, current_user.id)
    return resp


@twofa_bp.route("/challenge", methods=["POST"])
@login_required
@limiter.limit("10/minute")
def challenge():
    """
    Valida TOTP atual e emite cookie admin 2FA (TTL 15min).
    Usado pra entrar em /admin após login normal.
    """
    body = request.get_json(silent=True) or {}
    totp_code = (body.get("totp") or "").strip()
    if not totp_code:
        return jsonify({"error": "totp_required"}), 400

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        if not user or not user.totp_secret:
            return jsonify({"error": "2fa_not_enabled"}), 400

        if not pyotp.TOTP(user.totp_secret).verify(totp_code, valid_window=1):
            logger.warning("[admin.2fa.fail] user_id=%s ip=%s",
                          current_user.id, request.remote_addr)
            return jsonify({"error": "totp_invalid"}), 401
    finally:
        db.close()

    logger.info("[admin.2fa.success] user_id=%s ip=%s",
               current_user.id, request.remote_addr)
    resp = jsonify({"ok": True, "expires_in_s": 15 * 60})
    issue_admin_2fa_cookie(resp, current_user.id)
    return resp


@twofa_bp.route("/recover", methods=["POST"])
@login_required
@limiter.limit("3/minute")
def recover():
    """
    Valida recovery code (one-time) e emite cookie admin 2FA.
    Code é consumido (removido da lista) após uso.
    """
    body = request.get_json(silent=True) or {}
    code = (body.get("code") or "").strip()
    if not code:
        return jsonify({"error": "code_required"}), 400

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        if not user or not user.totp_recovery_codes:
            return jsonify({"error": "2fa_not_enabled"}), 400

        codes = list(user.totp_recovery_codes)
        matched_idx = None
        for i, hashed in enumerate(codes):
            if _verify_recovery(code, hashed):
                matched_idx = i
                break

        if matched_idx is None:
            logger.warning("[admin.2fa.recover.fail] user_id=%s", current_user.id)
            return jsonify({"error": "code_invalid"}), 401

        # Consome (remove) o code
        codes.pop(matched_idx)
        user.totp_recovery_codes = codes
        db.commit()
        remaining = len(codes)
    finally:
        db.close()

    logger.warning(
        "[admin.2fa.recover.success] user_id=%s remaining_codes=%d",
        current_user.id, remaining,
    )
    resp = jsonify({"ok": True, "remaining_recovery_codes": remaining})
    issue_admin_2fa_cookie(resp, current_user.id)
    return resp


@twofa_bp.route("/disable", methods=["POST"])
@login_required
@limiter.limit("3/minute")
def disable():
    """
    Desabilita 2FA. Requer TOTP atual (proteção contra session hijack).
    """
    body = request.get_json(silent=True) or {}
    totp_code = (body.get("totp") or "").strip()
    if not totp_code:
        return jsonify({"error": "totp_required"}), 400

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        if not user or not user.totp_secret:
            return jsonify({"error": "2fa_not_enabled"}), 400
        if not pyotp.TOTP(user.totp_secret).verify(totp_code, valid_window=1):
            return jsonify({"error": "totp_invalid"}), 401

        user.totp_secret = None
        user.totp_enabled_at = None
        user.totp_recovery_codes = None
        db.commit()
    finally:
        db.close()

    logger.warning("[admin.2fa.disabled] user_id=%s", current_user.id)
    resp = jsonify({"ok": True})
    revoke_admin_2fa_cookie(resp)
    return resp


@twofa_bp.route("/logout", methods=["POST"])
@login_required
def logout_admin():
    """Limpa cookie 2FA (sai do modo admin sem fazer logout completo)."""
    resp = jsonify({"ok": True})
    revoke_admin_2fa_cookie(resp)
    return resp
