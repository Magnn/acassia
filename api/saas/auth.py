"""
Auth do SaaS — signup / login / logout via flask-login.

Wiring no app.py (1 linha)::

    from api.saas.auth import auth_bp, login_manager
    login_manager.init_app(app)
    app.register_blueprint(auth_bp)

Tem que existir ``app.config['SECRET_KEY']`` setado antes do init.

Funções puras (``hash_password``, ``signup_user``, ``authenticate_user``) são
testáveis sem Flask. Endpoints são finos — apenas marshalling HTTP.
"""

from __future__ import annotations

import functools
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Iterable, Optional

import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)


def require_role(*allowed_roles: str):
    """
    Decorator de autorização — exige que ``current_user.role`` esteja em
    ``allowed_roles``. Combine com ``@login_required`` (ou já presume sessão
    válida via flask-login).

    Negação:
      - Request JSON / Accept JSON → 403 com {"error": "forbidden", ...}
      - Caso contrário → 403 + flash + redirect para o login.

    Uso::

        @app.route("/api/flows/...", methods=["POST"])
        @login_required
        @require_role("admin")
        def my_admin_route():
            ...
    """
    allowed = tuple(r for r in allowed_roles if r)

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "is_authenticated", False):
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({"error": "unauthorized"}), 401
                return redirect(url_for("saas_auth.login"))
            user_role = (getattr(current_user, "role", "") or "").strip().lower()
            if user_role not in allowed:
                if request.is_json or request.accept_mimetypes.accept_json:
                    return jsonify({
                        "error": "forbidden",
                        "user_role": user_role,
                        "required": list(allowed),
                    }), 403
                flash("Acesso restrito — sua conta não tem permissão.", "error")
                return redirect(url_for("saas_auth.login"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _is_admin(roles: Iterable[str]) -> bool:
    return any((r or "").strip().lower() == "admin" for r in roles)

from db import models
from db.database import SessionLocal
from extensions import limiter
from analytics_telemetry import track as _track_event

logger = logging.getLogger(__name__)

# Cost do bcrypt. Em prod 12 (~250ms); em testes 4 (~ms) via env.
_BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))
_MIN_PASSWORD_LEN = 8

auth_bp = Blueprint("saas_auth", __name__, url_prefix="/saas")
login_manager = LoginManager()
login_manager.login_view = "saas_auth.login"


@login_manager.unauthorized_handler
def _on_unauthorized():
    """
    Override default (redirect /saas/auth/login) — quando a request é JSON ou
    aceita JSON, retorna 401 com payload em vez de redirect 302. Mantém
    redirect tradicional pra requests HTML (login form).
    """
    if request.is_json or (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        return jsonify({"error": "unauthorized"}), 401
    return redirect(url_for("saas_auth.login", next=request.path))


# ─── Wrapper pra session de flask-login ──────────────────────────────────────


class AuthenticatedUser(UserMixin):
    def __init__(self, user_id: int, email: str, tenant_id: str, role: str,
                 impersonator_id: Optional[int] = None,
                 impersonation_session_id: Optional[int] = None,
                 admin_subrole: Optional[str] = None):
        self.id = user_id
        self.email = email
        self.tenant_id = tenant_id
        self.role = role
        # Quando setado, indica que o admin (impersonator_id) está vendo a app
        # como esse user. Frontend renderiza banner persistente.
        self.impersonator_id = impersonator_id
        self.impersonation_session_id = impersonation_session_id
        self.admin_subrole = admin_subrole

    @property
    def is_impersonating(self) -> bool:
        return self.impersonator_id is not None

    def get_id(self) -> str:
        return str(self.id)


@login_manager.user_loader
def _load_user(user_id_str: str) -> Optional[AuthenticatedUser]:
    try:
        admin_user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None

    db = SessionLocal()
    try:
        # Carrega o user "real" do session cookie do flask-login
        admin_user = db.query(models.User).filter_by(id=admin_user_id, is_active=True).first()
        if not admin_user:
            return None

        # Verifica cookie de impersonate. Se válido E user real é admin,
        # retorna AuthenticatedUser com identidade do TARGET + flags impersonator.
        try:
            from api.admin.impersonate import get_active_impersonation_session_id
            sess_id = get_active_impersonation_session_id()
        except Exception:
            sess_id = None

        if sess_id and admin_user.role == "admin":
            from datetime import datetime, timezone
            sess = db.query(models.ImpersonationSession).filter_by(id=sess_id).first()
            # SQLite armazena DateTime sem tzinfo mesmo com timezone=True;
            # normaliza pra comparação confiável.
            now_utc = datetime.now(timezone.utc)
            sess_expires = sess.expires_at if sess else None
            if sess_expires is not None and sess_expires.tzinfo is None:
                sess_expires = sess_expires.replace(tzinfo=timezone.utc)
            if (sess and sess.ended_at is None
                    and sess_expires is not None and sess_expires > now_utc
                    and sess.admin_user_id == admin_user.id):
                target = db.query(models.User).filter_by(id=sess.target_user_id).first()
                if target and target.is_active and target.deleted_at is None:
                    return AuthenticatedUser(
                        user_id=target.id,
                        email=target.email,
                        tenant_id=target.tenant_id,
                        role=target.role,
                        impersonator_id=admin_user.id,
                        impersonation_session_id=sess.id,
                        admin_subrole=admin_user.admin_subrole,
                    )

        return AuthenticatedUser(
            user_id=admin_user.id,
            email=admin_user.email,
            tenant_id=admin_user.tenant_id,
            role=admin_user.role,
            admin_subrole=admin_user.admin_subrole,
        )
    finally:
        db.close()


# ─── Funções puras (testáveis sem Flask) ─────────────────────────────────────


def hash_password(password: str) -> str:
    """bcrypt; cost configurável via env BCRYPT_ROUNDS (default 12)."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=_BCRYPT_ROUNDS),
    ).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time via bcrypt.checkpw. False em qualquer formato inválido."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def signup_user(email: str, password: str, name: Optional[str] = None) -> models.User:
    """
    Cria User com tenant_id único + 14d trial Pro automático (Frente 2.19).

    Raises:
        ValueError: email inválido, senha < 8 chars, ou email já registrado.
    """
    email = (email or "").strip().lower()
    password = password or ""
    if "@" not in email or len(email) < 5:
        raise ValueError("email inválido")

    # Password policy (Frente 8.10)
    try:
        from api.saas.security import validate_password_strength, PasswordPolicyError
        validate_password_strength(password, min_len=_MIN_PASSWORD_LEN)
    except PasswordPolicyError as exc:
        raise ValueError(str(exc))
    except Exception:
        # Fallback se import circular: check mínimo
        if len(password) < _MIN_PASSWORD_LEN:
            raise ValueError(f"senha precisa de no mínimo {_MIN_PASSWORD_LEN} caracteres")

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter_by(email=email).first()
        if existing:
            raise ValueError("email já registrado")

        # Trial farming guard: same email já bloqueado acima.
        # TODO Frente 2.19: bloquear same phone, same Stripe card.

        from datetime import timedelta

        tenant_id = f"tenant_{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc)
        user = models.User(
            tenant_id=tenant_id,
            email=email,
            password_hash=hash_password(password),
            name=(name or "").strip()[:200] or None,
            is_active=True,
            # Trial 14d Pro automático
            trial_started_at=now,
            trial_ends_at=now + timedelta(days=14),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(
            "[saas_auth] signup ok email=%s tenant=%s trial_ends=%s",
            email, tenant_id, user.trial_ends_at.isoformat() if user.trial_ends_at else None,
        )
        return user
    finally:
        db.close()


def authenticate_user(email: str, password: str) -> Optional[models.User]:
    """Returns User se credenciais válidas + ativo. None caso contrário."""
    email = (email or "").strip().lower()
    if not email or not password:
        return None
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email, is_active=True).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user
    finally:
        db.close()


def _touch_last_login(user_id: int) -> None:
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(id=user_id).first()
        if u:
            u.last_login_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


# ─── Endpoints HTTP ──────────────────────────────────────────────────────────


@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("3/minute", methods=["POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("saas_auth.signup_done"))

    if request.method == "POST":
        try:
            user = signup_user(
                email=request.form.get("email", ""),
                password=request.form.get("password", ""),
                name=request.form.get("name", ""),
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("auth/signup.html"), 400

        login_user(AuthenticatedUser(user.id, user.email, user.tenant_id, user.role))
        _track_event(
            "signup_completed",
            tenant_id=user.tenant_id,
            user_id=user.id,
            email=user.email,
        )
        return redirect(url_for("saas_auth.signup_done"))

    return render_template("auth/signup.html")


@auth_bp.route("/signup/done")
@login_required
def signup_done():
    """Placeholder — vira o passo 1 do wizard de onboarding numa próxima task."""
    return render_template("auth/signup_done.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5/minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("saas_auth.signup_done"))

    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        ip = request.remote_addr or "unknown"

        # Resolve user_id ANTES de validar senha (pra checar lockout)
        candidate_id = None
        db = SessionLocal()
        try:
            u = db.query(models.User).filter_by(email=email.strip().lower()).first()
            if u:
                candidate_id = u.id
        finally:
            db.close()

        # Lockout check (Frente 8.7-8.8)
        if candidate_id is not None:
            try:
                from api.saas.security import is_locked_out
                locked, count = is_locked_out(candidate_id)
                if locked:
                    logger.warning(
                        "[saas_auth.lockout] user_id=%s ip=%s count=%d",
                        candidate_id, ip, count,
                    )
                    flash("Conta temporariamente bloqueada — aguarde 15 minutos.", "error")
                    return render_template("auth/login.html"), 423  # Locked
            except Exception:
                pass  # fail open

        user = authenticate_user(email=email, password=password)
        if not user:
            # Registra falha pra brute-force tracking
            try:
                from api.saas.security import record_login_failure
                record_login_failure(candidate_id, ip)
            except Exception:
                pass
            flash("Email ou senha inválidos", "error")
            return render_template("auth/login.html"), 401

        # Sucesso: limpa contador
        try:
            from api.saas.security import record_login_success
            record_login_success(user.id)
        except Exception:
            pass

        _touch_last_login(user.id)
        login_user(AuthenticatedUser(user.id, user.email, user.tenant_id, user.role))
        next_url = request.args.get("next") or url_for("saas_auth.signup_done")
        return redirect(next_url)

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("saas_auth.login"))


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """
    Retorna info do usuário logado para o front-end React.
    Se em sessão impersonate, inclui flag e dados do admin original.
    """
    payload = {
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role,
    }

    if getattr(current_user, "is_impersonating", False):
        # Carrega info do admin pra mostrar no banner
        db = SessionLocal()
        try:
            admin = db.query(models.User).filter_by(
                id=current_user.impersonator_id,
            ).first()
            payload["impersonating"] = True
            payload["impersonator"] = {
                "id": current_user.impersonator_id,
                "email": admin.email if admin else "deleted",
                "name": admin.name if admin else None,
            }
        finally:
            db.close()

    # Buscar nome do user real (campo `name` não está no AuthenticatedUser)
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(id=current_user.id).first()
        if u:
            payload["name"] = u.name
            payload["is_verified"] = u.is_verified
            payload["totp_enabled"] = bool(u.totp_enabled_at)
    finally:
        db.close()

    return jsonify(payload)


@auth_bp.route("/me/plan", methods=["GET"])
@login_required
def me_plan():
    """
    Plano efetivo do user logado + limits + features (Frente 2.1).
    Frontend usa via useMyPlan() hook + <FeatureGate>.
    """
    import plans as plans_module

    plan_key, source = plans_module.effective_plan(current_user.tenant_id)
    cfg = plans_module.get_plan_config(plan_key)
    return jsonify({
        "plan": plan_key,
        "label": cfg["label"],
        "source": source,
        "price_brl": cfg["price_brl"],
        "limits": cfg["limits"],
        "features": cfg["features"],
    })


@auth_bp.route("/me/usage", methods=["GET"])
@login_required
def me_usage():
    """
    Uso atual + limites pra todos os kinds (Frente 2.27).
    Frontend usa via useMyUsage() hook + <QuotaGate>.
    """
    import quota
    usage = quota.get_usage(current_user.tenant_id)
    return jsonify({"usage": usage, "tenant_id": current_user.tenant_id})
