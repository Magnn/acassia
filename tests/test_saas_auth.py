"""Testes do auth do SaaS — funções puras + endpoints com test_client."""

from pathlib import Path

import pytest
from flask import Flask

from api.saas.auth import (
    AuthenticatedUser,
    auth_bp,
    authenticate_user,
    hash_password,
    login_manager,
    signup_user,
    verify_password,
)
from db import models
from db.database import Base, SessionLocal, engine as db_engine

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TEMPLATE_DIR = str(_PROJECT_ROOT / "templates")


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.User).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def app() -> Flask:
    flask_app = Flask("test_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(
        SECRET_KEY="test-secret",
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    return flask_app


@pytest.fixture
def client(app: Flask):
    return app.test_client()


# ─── hash / verify ───────────────────────────────────────────────────────────

def test_hash_e_verify_funcionam():
    h = hash_password("senha-forte-123")
    assert verify_password("senha-forte-123", h) is True
    assert verify_password("outra-senha", h) is False


def test_hash_diferente_a_cada_chamada():
    a = hash_password("xyz12345")
    b = hash_password("xyz12345")
    assert a != b
    assert verify_password("xyz12345", a)
    assert verify_password("xyz12345", b)


def test_verify_com_hash_invalido_retorna_false():
    assert verify_password("senha-1234", "not_a_hash") is False
    assert verify_password("senha-1234", "") is False


# ─── signup_user (função pura) ───────────────────────────────────────────────

def test_signup_user_cria_user_com_tenant_id():
    user = signup_user("foo@bar.com", "senha-1234", "Foo")
    assert user.id is not None
    assert user.email == "foo@bar.com"
    assert user.tenant_id.startswith("tenant_")
    assert user.password_hash and user.password_hash != "senha-1234"


def test_signup_email_lowercase():
    user = signup_user("FOO@BAR.com", "senha-1234")
    assert user.email == "foo@bar.com"


def test_signup_email_trimmed():
    user = signup_user("  foo@bar.com  ", "senha-1234")
    assert user.email == "foo@bar.com"


def test_signup_email_invalido_levanta():
    with pytest.raises(ValueError, match="email"):
        signup_user("nao_eh_email", "senha-1234")


def test_signup_senha_curta_levanta():
    with pytest.raises(ValueError, match="senha"):
        signup_user("foo@bar.com", "abc")


def test_signup_email_duplicado_levanta():
    signup_user("foo@bar.com", "senha-1234")
    with pytest.raises(ValueError, match="já registrado"):
        signup_user("foo@bar.com", "outra-1234")


def test_signup_tenant_ids_unicos_entre_users():
    a = signup_user("a@x.com", "senha-1234")
    b = signup_user("b@x.com", "senha-5678")
    assert a.tenant_id != b.tenant_id


def test_signup_name_truncado_a_200():
    long_name = "a" * 500
    user = signup_user("a@x.com", "senha-1234", name=long_name)
    assert len(user.name) == 200


def test_signup_name_vazio_vira_none():
    user = signup_user("a@x.com", "senha-1234", name="   ")
    assert user.name is None


# ─── authenticate_user ───────────────────────────────────────────────────────

def test_authenticate_credenciais_corretas():
    signup_user("foo@bar.com", "senha-1234")
    user = authenticate_user("foo@bar.com", "senha-1234")
    assert user is not None
    assert user.email == "foo@bar.com"


def test_authenticate_senha_errada_retorna_none():
    signup_user("foo@bar.com", "senha-1234")
    assert authenticate_user("foo@bar.com", "errada-1234") is None


def test_authenticate_email_inexistente_retorna_none():
    assert authenticate_user("ninguem@nada.com", "senha-1234") is None


def test_authenticate_email_case_insensitive():
    signup_user("foo@bar.com", "senha-1234")
    assert authenticate_user("FOO@BAR.COM", "senha-1234") is not None


def test_authenticate_user_inativo_retorna_none():
    signup_user("foo@bar.com", "senha-1234")
    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(email="foo@bar.com").first()
        u.is_active = False
        db.commit()
    finally:
        db.close()
    assert authenticate_user("foo@bar.com", "senha-1234") is None


def test_authenticate_args_vazios_retornam_none():
    assert authenticate_user("", "senha") is None
    assert authenticate_user("foo@bar.com", "") is None


# ─── Endpoints HTTP (integration via test_client) ────────────────────────────

def test_signup_endpoint_GET_renderiza(client):
    res = client.get("/saas/signup")
    assert res.status_code == 200
    assert b"Criar Conta" in res.data or b"Criar conta" in res.data


def test_signup_endpoint_POST_cria_user_e_redireciona(client):
    res = client.post(
        "/saas/signup",
        data={"email": "novo@user.com", "password": "senha-1234", "name": "Maria"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "/saas/signup/done" in res.headers.get("Location", "")

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email="novo@user.com").first()
        assert user is not None
        assert user.name == "Maria"
    finally:
        db.close()


def test_signup_endpoint_email_invalido_retorna_400(client):
    res = client.post(
        "/saas/signup",
        data={"email": "no_email", "password": "senha-1234"},
    )
    assert res.status_code == 400


def test_signup_endpoint_email_duplicado_retorna_400(client):
    signup_user("dup@x.com", "senha-1234")
    res = client.post(
        "/saas/signup",
        data={"email": "dup@x.com", "password": "outra-1234"},
    )
    assert res.status_code == 400


def test_login_endpoint_GET_renderiza(client):
    res = client.get("/saas/login")
    assert res.status_code == 200
    assert b"Entrar" in res.data


def test_login_endpoint_POST_credenciais_corretas(client):
    signup_user("alguem@x.com", "senha-1234")
    res = client.post(
        "/saas/login",
        data={"email": "alguem@x.com", "password": "senha-1234"},
        follow_redirects=False,
    )
    assert res.status_code == 302


def test_login_endpoint_credenciais_erradas_retorna_401(client):
    signup_user("alguem@x.com", "senha-1234")
    res = client.post(
        "/saas/login",
        data={"email": "alguem@x.com", "password": "errada-1234"},
    )
    assert res.status_code == 401


def test_login_endpoint_atualiza_last_login_at(client):
    signup_user("dt@x.com", "senha-1234")
    client.post("/saas/login", data={"email": "dt@x.com", "password": "senha-1234"})

    db = SessionLocal()
    try:
        u = db.query(models.User).filter_by(email="dt@x.com").first()
        assert u.last_login_at is not None
    finally:
        db.close()


def test_login_redirect_respeita_next_param(client):
    signup_user("alguem@x.com", "senha-1234")
    res = client.post(
        "/saas/login?next=/custom/path",
        data={"email": "alguem@x.com", "password": "senha-1234"},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert "/custom/path" in res.headers.get("Location", "")


def test_logout_redireciona_pra_login(client):
    signup_user("alguem@x.com", "senha-1234")
    client.post("/saas/login", data={"email": "alguem@x.com", "password": "senha-1234"})
    res = client.post("/saas/logout", follow_redirects=False)
    assert res.status_code == 302
    assert "/saas/login" in res.headers.get("Location", "")


def test_logout_sem_login_redireciona_pra_login(client):
    """Sem session, /logout dispara login_required → redirect pro login."""
    res = client.post("/saas/logout", follow_redirects=False)
    assert res.status_code == 302
    # Pode ser /saas/login direto ou /saas/login?next=...
    assert "/saas/login" in res.headers.get("Location", "")


def test_signup_done_requer_autenticacao(client):
    res = client.get("/saas/signup/done", follow_redirects=False)
    assert res.status_code == 302
    assert "/saas/login" in res.headers.get("Location", "")


def test_signup_loga_user_automaticamente(client):
    """Após signup, user já tem session — pode acessar /signup/done."""
    client.post(
        "/saas/signup",
        data={"email": "auto@x.com", "password": "senha-1234"},
    )
    res = client.get("/saas/signup/done", follow_redirects=False)
    assert res.status_code == 302
    assert "/builder/dashboard" in res.headers.get("Location", "")


# ─── AuthenticatedUser wrapper ───────────────────────────────────────────────

def test_authenticated_user_get_id_eh_str():
    u = AuthenticatedUser(user_id=42, email="x@x.com", tenant_id="tenant_xyz", role="operator")
    assert u.get_id() == "42"
    assert u.is_authenticated is True
