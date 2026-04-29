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

import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

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

from db import models
from db.database import SessionLocal

logger = logging.getLogger(__name__)

# Cost do bcrypt. Em prod 12 (~250ms); em testes 4 (~ms) via env.
_BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))
_MIN_PASSWORD_LEN = 8

auth_bp = Blueprint("saas_auth", __name__, url_prefix="/saas")
login_manager = LoginManager()
login_manager.login_view = "saas_auth.login"


# ─── Wrapper pra session de flask-login ──────────────────────────────────────


class AuthenticatedUser(UserMixin):
    def __init__(self, user_id: int, email: str, tenant_id: str, role: str):
        self.id = user_id
        self.email = email
        self.tenant_id = tenant_id
        self.role = role

    def get_id(self) -> str:
        return str(self.id)


@login_manager.user_loader
def _load_user(user_id_str: str) -> Optional[AuthenticatedUser]:
    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(id=user_id, is_active=True).first()
        if not user:
            return None
        return AuthenticatedUser(user.id, user.email, user.tenant_id, user.role)
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
    Cria User com tenant_id único.

    Raises:
        ValueError: email inválido, senha < 8 chars, ou email já registrado.
    """
    email = (email or "").strip().lower()
    password = password or ""
    if "@" not in email or len(email) < 5:
        raise ValueError("email inválido")
    if len(password) < _MIN_PASSWORD_LEN:
        raise ValueError(f"senha precisa de no mínimo {_MIN_PASSWORD_LEN} caracteres")

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter_by(email=email).first()
        if existing:
            raise ValueError("email já registrado")

        tenant_id = f"tenant_{secrets.token_hex(8)}"
        user = models.User(
            tenant_id=tenant_id,
            email=email,
            password_hash=hash_password(password),
            name=(name or "").strip()[:200] or None,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("[saas_auth] signup ok email=%s tenant=%s", email, tenant_id)
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
        return redirect(url_for("saas_auth.signup_done"))

    return render_template("auth/signup.html")


@auth_bp.route("/signup/done")
@login_required
def signup_done():
    """Placeholder — vira o passo 1 do wizard de onboarding numa próxima task."""
    return render_template("auth/signup_done.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("saas_auth.signup_done"))

    if request.method == "POST":
        user = authenticate_user(
            email=request.form.get("email", ""),
            password=request.form.get("password", ""),
        )
        if not user:
            flash("Email ou senha inválidos", "error")
            return render_template("auth/login.html"), 401

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
    """Retorna info do usuário logado para o front-end React."""
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "tenant_id": current_user.tenant_id,
        "role": current_user.role
    })
