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
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from urllib.parse import urlsplit

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


def _safe_next_url(value: Optional[str], default: str = "/builder/workspaces") -> str:
    """Aceita somente caminhos locais, evitando redirects externos após login."""
    candidate = (value or "").strip()
    if not candidate:
        return default
    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return default
    return candidate


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
                        admin_subrole=getattr(admin_user, 'admin_subrole', None),
                    )

        return AuthenticatedUser(
            user_id=admin_user.id,
            email=admin_user.email,
            tenant_id=admin_user.tenant_id,
            role=admin_user.role,
            admin_subrole=getattr(admin_user, 'admin_subrole', None),
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

        # Attach referral se cookie meumisterio_ref está presente (Frente 7.15)
        try:
            from api.saas.affiliate import attach_referral_to_signup
            attach_referral_to_signup(user.id, email)
        except Exception as exc:
            logger.debug("[signup.referral] attach falhou: %s", exc)

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
    """Redireciona direto pro dashboard após signup (conforme regra de negócio)."""
    return redirect("/builder/dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5/minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_safe_next_url(request.args.get("next"), "/builder/dashboard"))

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
            from api.saas.security import record_login_success, record_user_session
            record_login_success(user.id)
        except Exception:
            pass

        _touch_last_login(user.id)
        login_user(AuthenticatedUser(user.id, user.email, user.tenant_id, user.role))

        # Grava sessão persistida pra session mgmt (Frente 8.4)
        try:
            from flask import session as flask_session
            sess_id = flask_session.get("_id") or flask_session.sid if hasattr(flask_session, 'sid') else "unknown"
            record_user_session(user.id, str(sess_id))
        except Exception:
            pass

        next_url = _safe_next_url(request.args.get("next"))
        return redirect(next_url)

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("saas_auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5/minute")
def forgot_password():
    """
    Solicitação de recuperação de senha.
    Em requisições GET, redireciona para o login abrindo o modal de recuperação.
    Em requisições POST, gera o token seguro de uso único e grava no banco.
    """
    if request.method == "GET":
        return redirect(url_for("saas_auth.login", forgot="1"))

    data = request.get_json(silent=True) or request.form
    email = (data.get("email") or "").strip().lower()

    if not email or "@" not in email:
        msg = "Se o e-mail informado estiver cadastrado, você receberá as instruções em instantes."
        if request.is_json:
            return jsonify({"ok": True, "message": msg})
        flash(msg, "info")
        return redirect(url_for("saas_auth.login"))

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email, is_active=True).first()
        if not user or getattr(user, "deleted_at", None):
            msg = "Se o e-mail informado estiver cadastrado, você receberá as instruções em instantes."
            if request.is_json:
                return jsonify({"ok": True, "message": msg})
            flash(msg, "info")
            return redirect(url_for("saas_auth.login"))

        plain = secrets.token_urlsafe(32)
        digest = hashlib.sha256(plain.encode("utf-8")).hexdigest()

        # Invalida tokens anteriores não-usados deste usuário
        db.query(models.PasswordResetToken).filter(
            models.PasswordResetToken.user_id == user.id,
            models.PasswordResetToken.used_at.is_(None),
        ).delete()

        token_obj = models.PasswordResetToken(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            requested_ip=request.remote_addr,
        )
        db.add(token_obj)
        db.commit()

        reset_url = url_for("saas_auth.reset_password", token=plain, _external=True)
        logger.info(
            "[saas_auth.password_reset] user_id=%s ip=%s email=%s reset_url=%s",
            user.id, request.remote_addr, email, reset_url,
        )

        # Tenta envio por e-mail (Resend ou SMTP se configurados)
        from api.utils.email_sender import send_password_reset_email, is_email_service_configured

        email_sent = False
        if is_email_service_configured():
            try:
                email_sent = send_password_reset_email(user.email, reset_url)
            except Exception as exc:
                logger.warning("[saas_auth] Falha ao despachar e-mail de reset: %s", exc)

        resp_payload = {
            "ok": True,
            "email_sent": email_sent,
        }

        if email_sent:
            resp_payload["message"] = (
                "Enviamos um link de recuperação para seu e-mail. Verifique a caixa de entrada e também a pasta de spam."
            )
        else:
            # Se o servidor não possui envio de e-mail ativo (SMTP/Resend não configurados)
            # OU se estiver em dev/teste, fornece o link seguro diretamente para não travar o usuário
            resp_payload["message"] = (
                "Como o envio automático de e-mails ainda não possui credenciais SMTP/Resend configuradas no servidor, "
                "utilize o link de recuperação direto abaixo para redefinir sua senha agora mesmo:"
            )
            resp_payload["reset_url"] = reset_url

        if request.is_json:
            return jsonify(resp_payload)

        flash(resp_payload["message"], "success" if email_sent else "info")
        return redirect(url_for("saas_auth.login"))
    finally:
        db.close()


@auth_bp.route("/email-status", methods=["GET"])
def email_status():
    """Retorna diagnóstico de provedores de e-mail detectados no ambiente."""
    from api.utils.email_sender import get_email_diagnostic_info
    return jsonify(get_email_diagnostic_info())


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@auth_bp.route("/password-reset", methods=["GET", "POST"])
@limiter.limit("10/minute")
def reset_password(token: Optional[str] = None):
    """
    Visualização e submissão do formulário de redefinição de senha com token de 1h.
    """
    if not token:
        token = request.args.get("token") or request.form.get("token") or ""
    token = token.strip()

    if not token:
        flash("Token de recuperação ausente ou inválido.", "error")
        return redirect(url_for("saas_auth.login"))

    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    db = SessionLocal()
    try:
        token_row = db.query(models.PasswordResetToken).filter_by(token_hash=digest).first()
        if not token_row or token_row.used_at:
            flash("Link de recuperação inválido ou já utilizado. Por favor, solicite um novo.", "error")
            return redirect(url_for("saas_auth.login"))

        expires_at = token_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            flash("Este link de recuperação expirou (validade de 1 hora). Solicite um novo.", "error")
            return redirect(url_for("saas_auth.login"))

        user = db.query(models.User).filter_by(id=token_row.user_id, is_active=True).first()
        if not user:
            flash("Usuário não encontrado.", "error")
            return redirect(url_for("saas_auth.login"))

        if request.method == "POST":
            new_password = (request.form.get("password") or "").strip()
            confirm_password = (request.form.get("confirm_password") or "").strip()

            if not new_password:
                flash("Por favor, informe a nova senha.", "error")
                return render_template("auth/reset_password.html", token=token), 400

            if new_password != confirm_password:
                flash("As senhas informadas não coincidem.", "error")
                return render_template("auth/reset_password.html", token=token), 400

            if len(new_password) < _MIN_PASSWORD_LEN:
                flash(f"A senha deve ter no mínimo {_MIN_PASSWORD_LEN} caracteres.", "error")
                return render_template("auth/reset_password.html", token=token), 400

            try:
                from api.saas.security import validate_password_strength, PasswordPolicyError
                validate_password_strength(new_password, min_len=_MIN_PASSWORD_LEN)
            except PasswordPolicyError as exc:
                flash(str(exc), "error")
                return render_template("auth/reset_password.html", token=token), 422
            except Exception:
                pass

            user.password_hash = hash_password(new_password)
            user.last_password_change_at = datetime.now(timezone.utc)
            token_row.used_at = datetime.now(timezone.utc)
            db.commit()

            try:
                from api.saas.security import record_login_success
                record_login_success(user.id)
            except Exception:
                pass

            logger.info("[saas_auth.password_reset_success] user_id=%s email=%s", user.id, user.email)
            flash("Senha redefinida com sucesso! Você já pode entrar com sua nova senha.", "success")
            return redirect(url_for("saas_auth.login"))

        return render_template("auth/reset_password.html", token=token)
    finally:
        db.close()


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

    # Uma única sessão para todas as queries (evita pool contention)
    db = SessionLocal()
    try:
        if getattr(current_user, "is_impersonating", False):
            admin = db.query(models.User).filter_by(
                id=current_user.impersonator_id,
            ).first()
            payload["impersonating"] = True
            payload["impersonator"] = {
                "id": current_user.impersonator_id,
                "email": admin.email if admin else "deleted",
                "name": admin.name if admin else None,
            }

        # Buscar nome do user real (campo `name` não está no AuthenticatedUser)
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


@auth_bp.route("/me/onboarding", methods=["GET"])
@login_required
def me_onboarding():
    """
    Progresso de onboarding gamificado (Frente 5.1).
    Auto-detecta milestones antes de retornar pra evitar UI stale.
    """
    import onboarding_progress
    try:
        onboarding_progress.auto_detect_for_tenant(current_user.tenant_id)
    except Exception:
        pass
    return jsonify(onboarding_progress.progress(current_user.id))


@auth_bp.route("/me/onboarding/<milestone_key>/complete", methods=["POST"])
@login_required
def me_complete_milestone(milestone_key):
    """Force-complete um milestone (admin/dev override)."""
    import onboarding_progress
    is_new = onboarding_progress.mark_milestone(current_user.id, milestone_key)
    return jsonify({"ok": True, "is_new": is_new})

# ─── WORKSPACES MANAGEMENT (FRENTE 11.0) ───────────────────────────────────

from db.models import Workspace, WorkspaceMember

@auth_bp.route("/workspaces", methods=["GET"])
@login_required
def list_workspaces():
    """Lista todos os workspaces a que o usuário pertence."""
    db = SessionLocal()
    try:
        memberships = db.query(WorkspaceMember).filter_by(user_id=current_user.id).all()
        workspace_ids = [m.workspace_id for m in memberships]
        workspaces = db.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()

        result = []
        for w in workspaces:
            role = next((m.role for m in memberships if m.workspace_id == w.id), "user")
            result.append({
                "id": w.id,
                "name": w.name,
                "role": role,
                "is_current": w.id == current_user.tenant_id
            })

        return jsonify({"workspaces": result})
    finally:
        db.close()

@auth_bp.route("/workspaces/switch", methods=["POST"])
@login_required
def switch_workspace():
    """Altera o tenant_id atual do usuário para trocar de contexto."""
    data = request.json or {}
    target_id = data.get("workspace_id", "").strip()

    db = SessionLocal()
    try:
        # Verifica se ele é membro do workspace alvo
        membership = db.query(WorkspaceMember).filter_by(user_id=current_user.id, workspace_id=target_id).first()
        if not membership:
            return jsonify({"error": "Sem permissão ou workspace não encontrado"}), 403

        u = db.query(models.User).filter_by(id=current_user.id).first()
        u.tenant_id = target_id
        db.commit()

        # Update session
        login_user(AuthenticatedUser(u.id, u.email, target_id, u.role))
        return jsonify({"message": "Contexto alterado com sucesso", "current_workspace": target_id})
    finally:
        db.close()

@auth_bp.route("/workspaces", methods=["POST"])
@login_required
def create_workspace():
    """Cria um novo workspace e vincula o criador como admin."""
    import uuid
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Nome obrigatório"}), 400

    new_tenant_id = "wk_" + uuid.uuid4().hex[:12]
    db = SessionLocal()
    try:
        new_ws = Workspace(
            id=new_tenant_id,
            name=name,
            owner_id=current_user.id
        )
        db.add(new_ws)
        db.flush()

        new_member = WorkspaceMember(
            workspace_id=new_tenant_id,
            user_id=current_user.id,
            role="admin"
        )
        db.add(new_member)
        db.commit()

        return jsonify({"message": "Workspace criado", "id": new_tenant_id})
    finally:
        db.close()
