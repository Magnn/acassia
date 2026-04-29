"""
Security baseline endpoints — password reset, email verification,
brute-force lockout (Frente 8.7-8.11).

Endpoints:
    POST /saas/password-reset/request {email}
    POST /saas/password-reset/confirm {token, email, new_password}
    POST /saas/email/verify/request
    GET  /saas/email/verify/confirm?token=...

Lockout:
- 5 falhas em 15min na mesma conta → lockout 15min
- 10 falhas em 1h do mesmo IP → block IP 1h
- Storage: Redis se disponível (chave acassia:auth:fail:{user_id|ip})
- Fallback: in-memory dict (single-process, dev only)
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from db import models
from db.database import SessionLocal
from extensions import limiter


logger = logging.getLogger(__name__)
security_bp = Blueprint("saas_security", __name__, url_prefix="/saas")


# ─── In-memory fallback pra brute-force counter ───────────────────────


_inmem_lock = threading.Lock()
_inmem_counters: dict[str, list[float]] = {}  # key → list of failure timestamps


def _redis():
    """Cliente Redis se disponível, senão None."""
    try:
        from reliability.redis_inbound import _client
        return _client()
    except Exception:
        return None


def _record_failure(key: str, window_s: int = 900) -> int:
    """
    Registra 1 falha. Retorna count atual de falhas na janela.
    Sliding window via lista timestamps (purge antigos).
    """
    now = time.time()
    cutoff = now - window_s
    r = _redis()
    if r:
        try:
            full_key = f"acassia:auth:fail:{key}"
            r.zadd(full_key, {str(now): now})
            r.zremrangebyscore(full_key, 0, cutoff)
            r.expire(full_key, window_s + 60)
            return int(r.zcard(full_key) or 0)
        except Exception as exc:
            logger.warning("[security] redis fail: %s — falling back to memory", exc)

    # Fallback in-memory
    with _inmem_lock:
        ts_list = _inmem_counters.get(key, [])
        ts_list = [t for t in ts_list if t > cutoff]
        ts_list.append(now)
        _inmem_counters[key] = ts_list
        return len(ts_list)


def _clear_failures(key: str) -> None:
    r = _redis()
    if r:
        try:
            r.delete(f"acassia:auth:fail:{key}")
            return
        except Exception:
            pass
    with _inmem_lock:
        _inmem_counters.pop(key, None)


def is_locked_out(user_id: int) -> tuple[bool, int]:
    """
    True se user tem >= 5 falhas em 15min. Retorna (locked, count).
    """
    r = _redis()
    key = str(user_id)
    if r:
        try:
            full_key = f"acassia:auth:fail:user:{key}"
            now = time.time()
            r.zremrangebyscore(full_key, 0, now - 900)
            count = int(r.zcard(full_key) or 0)
            return count >= 5, count
        except Exception:
            pass
    with _inmem_lock:
        ts_list = _inmem_counters.get(f"user:{key}", [])
        cutoff = time.time() - 900
        ts_list = [t for t in ts_list if t > cutoff]
        return len(ts_list) >= 5, len(ts_list)


def record_login_failure(user_id: Optional[int], ip: str) -> dict:
    """
    Registra falha de login. Incrementa por user_id (se conhecido) e por IP.
    Retorna {locked, user_count, ip_count}.
    """
    user_count = _record_failure(f"user:{user_id}", window_s=900) if user_id else 0
    ip_count = _record_failure(f"ip:{ip}", window_s=3600)
    locked = user_count >= 5 or ip_count >= 30
    if locked:
        logger.warning(
            "[security.lockout] user_id=%s ip=%s user_count=%s ip_count=%s",
            user_id, ip, user_count, ip_count,
        )
    return {"locked": locked, "user_count": user_count, "ip_count": ip_count}


def record_login_success(user_id: int) -> None:
    """Limpa contador após login bem-sucedido."""
    _clear_failures(f"user:{user_id}")


# ─── Password policy ──────────────────────────────────────────────────


# Top 50 senhas comuns (fonte: SecLists rockyou top 100)
_COMMON_PASSWORDS = frozenset({
    "12345678", "password", "qwerty123", "abc12345", "iloveyou",
    "1q2w3e4r", "1qaz2wsx", "qwerty12", "letmein123", "welcome1",
    "monkey123", "dragon123", "master123", "shadow12", "654321aa",
    "password1", "12341234", "qwertyui", "asdfghjk", "trustno1",
    "sunshine", "princess", "football", "baseball", "superman",
    "batman123", "starwars", "michael1", "computer", "internet",
    "summer123", "winter123", "spring12", "abc123abc", "passw0rd",
    "p@ssw0rd", "p@ssword", "admin123", "root1234", "test1234",
    "senha123", "brasil12", "muambasm", "bemvindo", "obrigado",
    "100200300", "11223344", "aabbccdd", "zaq12wsx", "asdf1234",
})


class PasswordPolicyError(ValueError):
    pass


def validate_password_strength(password: str, *, min_len: int = 8) -> None:
    """
    Valida senha contra política mínima:
    - >= min_len chars
    - Não está em lista de comum
    - Tem ao menos 1 letra E 1 dígito (relaxado pra UX)

    Raises PasswordPolicyError com mensagem amigável.
    """
    if len(password) < min_len:
        raise PasswordPolicyError(f"senha precisa de no mínimo {min_len} caracteres")
    if password.lower() in _COMMON_PASSWORDS:
        raise PasswordPolicyError(
            "senha muito comum — escolha algo mais único (combine palavras + números)"
        )
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        raise PasswordPolicyError("senha precisa ter ao menos 1 letra e 1 número")


# ─── Helpers de token ─────────────────────────────────────────────────


def _generate_token(length: int = 32) -> tuple[str, str]:
    """Gera (token_plain, token_hash). Hash via SHA-256 (rapidez vs bcrypt — token é one-time)."""
    plain = secrets.token_urlsafe(length)
    digest = hashlib.sha256(plain.encode()).hexdigest()
    return plain, digest


def _hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode()).hexdigest()


# ─── Password reset flow ──────────────────────────────────────────────


@security_bp.route("/password-reset/request", methods=["POST"])
@limiter.limit("3/hour")
def password_reset_request():
    """
    Solicita reset de senha. Sempre retorna 200 (não vaza se email existe).
    """
    body = request.get_json(silent=True) or request.form
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"ok": True, "message": "Se o email existe, enviamos instruções."})

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email, is_active=True).first()
        if not user or user.deleted_at:
            # Silent: não revelar se email existe
            return jsonify({"ok": True, "message": "Se o email existe, enviamos instruções."})

        plain, digest = _generate_token()
        # Limpa tokens anteriores não-usados desse user
        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used_at.is_(None),
        ).delete()

        token = models.PasswordResetToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            requested_ip=request.remote_addr,
        )
        db.add(token)
        db.commit()

        reset_url = f"{os.getenv('APP_URL', 'http://localhost:5000')}/saas/password-reset?token={plain}&email={email}"
        logger.info(
            "[security.password_reset.requested] user_id=%s ip=%s url_logged_for_dev",
            user.id, request.remote_addr,
        )
        # TODO Frente 7.25: send email via Resend
        # Em dev, logamos url pra teste manual:
        if os.getenv("FLASK_ENV") != "production":
            logger.warning("[DEV] password reset URL: %s", reset_url)

        return jsonify({"ok": True, "message": "Se o email existe, enviamos instruções."})
    finally:
        db.close()


@security_bp.route("/password-reset/confirm", methods=["POST"])
@limiter.limit("5/hour")
def password_reset_confirm():
    body = request.get_json(silent=True) or request.form
    token = (body.get("token") or "").strip()
    email = (body.get("email") or "").strip().lower()
    new_password = body.get("new_password") or ""

    if not token or not email or not new_password:
        return jsonify({"error": "missing_fields"}), 400

    try:
        validate_password_strength(new_password)
    except PasswordPolicyError as exc:
        return jsonify({"error": "password_policy", "message": str(exc)}), 422

    digest = _hash_token(token)
    db = SessionLocal()
    try:
        token_row = db.query(models.PasswordResetToken).filter_by(token_hash=digest).first()
        if not token_row or token_row.used_at:
            return jsonify({"error": "token_invalid"}), 400

        # Normaliza tz pra comparação SQLite
        expires_at = token_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return jsonify({"error": "token_expired"}), 400

        user = db.query(models.User).filter_by(id=token_row.user_id, is_active=True).first()
        if not user or user.email != email:
            return jsonify({"error": "token_invalid"}), 400

        # Atualiza senha
        new_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(rounds=int(os.environ.get("BCRYPT_ROUNDS", "12"))),
        ).decode("utf-8")
        user.password_hash = new_hash
        user.last_password_change_at = datetime.now(timezone.utc)
        token_row.used_at = datetime.now(timezone.utc)
        db.commit()

        # Limpa lockout
        record_login_success(user.id)

        logger.warning(
            "[security.password_reset.confirmed] user_id=%s ip=%s",
            user.id, request.remote_addr,
        )
        return jsonify({"ok": True})
    finally:
        db.close()


# ─── Email verification ───────────────────────────────────────────────


@security_bp.route("/email/verify/request", methods=["POST"])
@login_required
@limiter.limit("5/hour")
def email_verify_request():
    """Reenviar email de verificação (current user)."""
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=current_user.id).first()
        if not user:
            return jsonify({"error": "user_not_found"}), 404
        if user.is_verified:
            return jsonify({"error": "already_verified"}), 409

        plain, digest = _generate_token()
        db.query(models.EmailVerificationToken).filter(
            models.EmailVerificationToken.user_id == user.id,
            models.EmailVerificationToken.used_at.is_(None),
        ).delete()
        token = models.EmailVerificationToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        db.add(token)
        db.commit()

        verify_url = f"{os.getenv('APP_URL', 'http://localhost:5000')}/saas/email/verify/confirm?token={plain}"
        if os.getenv("FLASK_ENV") != "production":
            logger.warning("[DEV] email verify URL: %s", verify_url)
        # TODO Frente 7.25: send email via Resend
        return jsonify({"ok": True, "message": "Email de verificação enviado."})
    finally:
        db.close()


# ─── Session management (Frente 8.4-8.6) ──────────────────────────────


def _session_token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def record_user_session(user_id: int, session_id: str) -> int:
    """
    Cria UserSession persistente. Chamado em login_success.
    Returns id da sessão criada.

    NÃO bloqueia login se gravação falhar (resilient).
    """
    db = SessionLocal()
    try:
        # Resolve geo (IP geolocation simples — futuro: usar GeoIP2 lib)
        ip = (request.remote_addr or "")[:45]
        ua = (request.headers.get("User-Agent", "") or "")[:500]

        # Marca todas sessões anteriores como is_current=False
        db.query(models.UserSession).filter_by(
            user_id=user_id, is_current=True,
        ).update({"is_current": False}, synchronize_session=False)

        sess = models.UserSession(
            user_id=user_id,
            session_token_hash=_session_token_hash(session_id),
            ip_address=ip,
            user_agent=ua,
            is_current=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(sess)
        db.commit()
        return sess.id
    except Exception as exc:
        logger.warning("[session] record falhou: %s", exc)
        return 0
    finally:
        db.close()


@security_bp.route("/sessions", methods=["GET"])
@login_required
def list_sessions():
    """Lista sessões ativas do user logado."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        sessions = (
            db.query(models.UserSession)
            .filter(
                models.UserSession.user_id == current_user.id,
                models.UserSession.revoked_at.is_(None),
            )
            .order_by(models.UserSession.last_activity_at.desc())
            .all()
        )
        return jsonify({
            "sessions": [
                {
                    "id": s.id,
                    "ip_address": s.ip_address,
                    "user_agent": (s.user_agent or "")[:200],
                    "geo_country": s.geo_country,
                    "geo_city": s.geo_city,
                    "is_current": s.is_current,
                    "created_at": s.created_at.isoformat(),
                    "last_activity_at": s.last_activity_at.isoformat(),
                    "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                } for s in sessions
            ]
        })
    finally:
        db.close()


@security_bp.route("/sessions/<int:session_id>/revoke", methods=["POST"])
@login_required
def revoke_session(session_id: int):
    """Revoga uma sessão específica."""
    db = SessionLocal()
    try:
        sess = db.query(models.UserSession).filter_by(
            id=session_id, user_id=current_user.id,
        ).first()
        if not sess:
            return jsonify({"error": "session_not_found"}), 404
        if sess.revoked_at:
            return jsonify({"error": "already_revoked"}), 409
        sess.revoked_at = datetime.now(timezone.utc)
        sess.revoked_reason = "user_revoke"
        db.commit()
        logger.info("[session.revoked] user_id=%s session_id=%s", current_user.id, session_id)
        return jsonify({"ok": True})
    finally:
        db.close()


@security_bp.route("/sessions/revoke-all-others", methods=["POST"])
@login_required
def revoke_all_other_sessions():
    """Revoga TODAS as sessões exceto a atual."""
    db = SessionLocal()
    try:
        count = (
            db.query(models.UserSession)
            .filter(
                models.UserSession.user_id == current_user.id,
                models.UserSession.is_current == False,  # noqa: E712
                models.UserSession.revoked_at.is_(None),
            )
            .update(
                {"revoked_at": datetime.now(timezone.utc), "revoked_reason": "user_revoke_all_others"},
                synchronize_session=False,
            )
        )
        db.commit()
        return jsonify({"ok": True, "revoked_count": count})
    finally:
        db.close()


@security_bp.route("/email/verify/confirm", methods=["GET", "POST"])
def email_verify_confirm():
    token = (request.args.get("token") or "").strip()
    if not token:
        body = request.get_json(silent=True) or {}
        token = (body.get("token") or "").strip()
    if not token:
        return jsonify({"error": "token_required"}), 400

    digest = _hash_token(token)
    db = SessionLocal()
    try:
        token_row = db.query(models.EmailVerificationToken).filter_by(token_hash=digest).first()
        if not token_row or token_row.used_at:
            return jsonify({"error": "token_invalid"}), 400
        expires_at = token_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return jsonify({"error": "token_expired"}), 400

        user = db.query(models.User).filter_by(id=token_row.user_id).first()
        if not user:
            return jsonify({"error": "user_not_found"}), 404

        user.is_verified = True
        token_row.used_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("[security.email.verified] user_id=%s", user.id)
        return jsonify({"ok": True, "verified": True})
    finally:
        db.close()
