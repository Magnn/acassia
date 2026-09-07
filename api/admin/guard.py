"""
Admin route guard com defesa em profundidade (Frente 1.1).

Camadas:
    1. Login válido (flask-login)
    2. role == "admin"
    3. user_id ∈ ADMIN_ALLOWLIST_IDS (env var, NÃO no DB — defesa contra DB pwn)
    4. Cookie `admin_2fa_verified` válido (TTL 15min)

Uso::

    from api.admin.guard import require_admin

    @app.route("/api/admin/...")
    @require_admin
    def my_admin_endpoint(): ...
"""

from __future__ import annotations

import functools
import logging
import os
from datetime import datetime, timezone, timedelta

from flask import jsonify, redirect, request, url_for, current_app
from flask_login import current_user
from itsdangerous import BadSignature, URLSafeTimedSerializer


logger = logging.getLogger(__name__)


_ADMIN_2FA_COOKIE = "meumisterio_admin_2fa"
_ADMIN_2FA_TTL_S = 15 * 60  # 15 minutos
_ADMIN_2FA_SALT = "admin-2fa-cookie-v1"


def get_admin_allowlist() -> set[int]:
    """
    IDs autorizados a acessar /admin. Vem da env var ADMIN_ALLOWLIST_IDS
    (vírgula-separada). Default seguro inclui primeiros IDs admin.
    """
    raw = (os.getenv("ADMIN_ALLOWLIST_IDS") or "1,2,3,4,5").strip()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def get_admin_allowed_emails() -> set[str]:
    """
    Emails autorizados a acessar /admin diretamente (ex.: mgnhnrq31@gmail.com).
    """
    raw = os.getenv("ADMIN_ALLOWLIST_EMAILS", "mgnhnrq31@gmail.com,interno@meumisterio.local").strip()
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _serializer():
    """Serializer assinado pra cookie 2FA. Usa SECRET_KEY do app."""
    key = current_app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(key, salt=_ADMIN_2FA_SALT)


def issue_admin_2fa_cookie(response, user_id: int) -> None:
    """
    Marca a response com cookie httpOnly+Secure indicando 2FA OK.
    Chamado após validação TOTP bem-sucedida.
    """
    s = _serializer()
    token = s.dumps({"uid": user_id, "ts": int(datetime.now(timezone.utc).timestamp())})
    is_secure = request.is_secure or os.getenv("FLASK_ENV") == "production"
    response.set_cookie(
        _ADMIN_2FA_COOKIE,
        token,
        max_age=_ADMIN_2FA_TTL_S,
        httponly=True,
        secure=is_secure,
        samesite="Strict",
        path="/",
    )


def revoke_admin_2fa_cookie(response) -> None:
    """Remove cookie 2FA — usado em logout admin."""
    response.delete_cookie(_ADMIN_2FA_COOKIE, path="/")


def _is_2fa_cookie_valid(user_id: int) -> bool:
    """
    Cookie OK se: assinado válido, não expirado, e uid bate com user_id.
    """
    raw = request.cookies.get(_ADMIN_2FA_COOKIE)
    if not raw:
        return False
    s = _serializer()
    try:
        data = s.loads(raw, max_age=_ADMIN_2FA_TTL_S)
    except BadSignature:
        logger.warning("[admin] cookie 2FA com assinatura inválida user_id=%s", user_id)
        return False
    return data.get("uid") == user_id


def _wants_json() -> bool:
    return request.is_json or (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    )


def _deny(reason: str, status: int = 403):
    logger.warning(
        "[admin.access.denied] reason=%s user_id=%s ip=%s path=%s",
        reason,
        getattr(current_user, "id", None),
        request.remote_addr,
        request.path,
    )
    if _wants_json():
        return jsonify({"error": "admin_access_denied", "reason": reason}), status
    # Pra rotas HTML, redireciona pro login normal
    return redirect(url_for("saas_auth.login", next=request.path))


def require_admin(fn):
    """
    Decorator que aplica todas as 4 camadas de defesa.

    Returns:
        - 401 ou redirect → não logado
        - 403 → role != admin OU id ∉ allowlist
        - 403 + reason="2fa_required" → 2FA não validado / expirado
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # Camada 1: autenticado?
        if not getattr(current_user, "is_authenticated", False):
            if _wants_json():
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("saas_auth.login", next=request.path))

        # Camada 2: role admin?
        role = (getattr(current_user, "role", "") or "").strip().lower()
        if role != "admin":
            return _deny("not_admin", 403)

        # Camada 3: na allowlist?
        allowlist = get_admin_allowlist()
        allowed_emails = get_admin_allowed_emails()
        user_email = (getattr(current_user, "email", "") or "").strip().lower()
        if current_user.id not in allowlist and user_email not in allowed_emails:
            logger.error(
                "[SECURITY] Tentativa de acesso admin fora da allowlist user_id=%s email=%s ip=%s",
                current_user.id, user_email, request.remote_addr,
            )
            return _deny("not_in_allowlist", 403)

        # Camada 4: 2FA válido? (obrigatório se o usuário já ativou TOTP)
        totp_enabled = bool(getattr(current_user, "totp_enabled_at", None))
        if totp_enabled and not _is_2fa_cookie_valid(current_user.id):
            return _deny("2fa_required", 403)

        # Tudo OK
        logger.info(
            "[admin.access.granted] user_id=%s ip=%s path=%s",
            current_user.id, request.remote_addr, request.path,
        )
        return fn(*args, **kwargs)

    return wrapper


def admin_subrole_at_least(*allowed_subroles: str):
    """
    Decorator finer-grained pra Frente 1.24 (admin team management).
    Use APÓS @require_admin pra restringir a sub-roles específicas.

    Sub-roles: 'founder' (tudo), 'support' (sem financeiro), 'billing' (sem destrutivo)

    Uso::

        @require_admin
        @admin_subrole_at_least("founder", "billing")
        def refund_endpoint(): ...
    """
    allowed = set(s.strip().lower() for s in allowed_subroles if s)

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            sub = (getattr(current_user, "admin_subrole", "") or "").strip().lower()
            # 'founder' bypass — sempre passa
            if sub == "founder":
                return fn(*args, **kwargs)
            if sub not in allowed:
                return _deny(f"subrole_required:{','.join(allowed)}", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
