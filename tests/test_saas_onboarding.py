"""Testes do wizard de onboarding."""

from pathlib import Path

import pytest
from flask import Flask

from api.saas.auth import auth_bp, login_manager, signup_user
from api.saas.onboarding import (
    ALLOWED_RESTRICTIONS,
    STEP_DONE,
    STEP_OFERTA,
    STEP_PERSONA,
    STEP_TEMPLATE,
    STEP_WHATSAPP,
    detect_current_step,
    onboarding_bp,
    save_oferta,
    save_persona,
    save_template,
    save_whatsapp,
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
    db.query(models.StudioAgent).delete()
    db.query(models.StudioAgentVersion).delete()
    db.query(models.FlowBlueprint).delete()
    db.query(models.TenantFlowVariable).delete()
    db.query(models.TenantFlowSecret).delete()
    db.commit()
    db.close()
    yield


@pytest.fixture
def app() -> Flask:
    flask_app = Flask("test_app", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="test-secret", TESTING=True)
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(onboarding_bp)
    return flask_app


@pytest.fixture
def client(app: Flask):
    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """Client autenticado com user signup novo."""
    user = signup_user("tarologa@x.com", "senha-1234", "Maria")
    client.post("/saas/login", data={"email": "tarologa@x.com", "password": "senha-1234"})
    return client, user


# ─── detect_current_step ─────────────────────────────────────────────────────

def test_detect_step_inicial_eh_persona():
    assert detect_current_step("tenant_zero") == STEP_PERSONA


def test_detect_step_apos_persona_eh_oferta():
    save_persona("t1", "Esmeralda", "acolhedor", "Cigana ancestral com dom genuíno", [])
    assert detect_current_step("t1") == STEP_OFERTA


def test_detect_step_apos_oferta_eh_template():
    save_persona("t2", "X", "direto", "Mais de 20 caracteres aqui sim", [])
    save_oferta("t2", "Tiragem", "19,90", "", "stripe")
    assert detect_current_step("t2") == STEP_TEMPLATE


def test_detect_step_apos_template_eh_whatsapp():
    save_persona("t3", "X", "direto", "Mais de 20 caracteres aqui sim", [])
    save_oferta("t3", "Tiragem", "19,90", "", "stripe")
    save_template("t3", "tarot_express")
    assert detect_current_step("t3") == STEP_WHATSAPP


def test_detect_step_apos_whatsapp_eh_done():
    save_persona("t4", "X", "direto", "Mais de 20 caracteres aqui sim", [])
    save_oferta("t4", "Tiragem", "19,90", "", "stripe")
    save_template("t4", "tarot_express")
    save_whatsapp("t4", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxxx")
    assert detect_current_step("t4") == STEP_DONE


# ─── save_persona ────────────────────────────────────────────────────────────

def test_save_persona_cria_agent_e_versao():
    agent = save_persona("t1", "Esmeralda", "mistico", "História mística da cigana ancestral", ["nao_promete_cura"])
    assert agent.tenant_id == "t1"
    assert agent.name == "Esmeralda"

    db = SessionLocal()
    try:
        ver = db.query(models.StudioAgentVersion).filter_by(agent_id=agent.id).first()
        assert ver is not None
        assert ver.version_number == 1
        assert ver.body_json["tone"] == "mistico"
        assert "nao_promete_cura" in ver.body_json["restrictions"]
    finally:
        db.close()


def test_save_persona_nome_vazio_levanta():
    with pytest.raises(ValueError, match="nome"):
        save_persona("t1", "", "acolhedor", "História suficientemente longa aqui", [])


def test_save_persona_tom_invalido_levanta():
    with pytest.raises(ValueError, match="tom"):
        save_persona("t1", "X", "alienigena", "História suficientemente longa aqui", [])


def test_save_persona_backstory_curta_levanta():
    with pytest.raises(ValueError, match="história"):
        save_persona("t1", "X", "acolhedor", "curto", [])


def test_save_persona_restrictions_invalidas_filtradas():
    """Restrições não-conhecidas são silenciosamente ignoradas."""
    agent = save_persona(
        "t1", "X", "acolhedor", "História suficientemente longa aqui",
        ["nao_promete_cura", "marciano_invalido"],
    )
    db = SessionLocal()
    try:
        ver = db.query(models.StudioAgentVersion).filter_by(agent_id=agent.id).first()
        assert "nao_promete_cura" in ver.body_json["restrictions"]
        assert "marciano_invalido" not in ver.body_json["restrictions"]
    finally:
        db.close()


# ─── save_oferta ─────────────────────────────────────────────────────────────

def test_save_oferta_grava_4_variaveis():
    save_oferta("t1", "Tiragem Express", "19,90", "Descrição", "stripe")
    db = SessionLocal()
    try:
        vars_ = {v.key: v.value_json for v in db.query(models.TenantFlowVariable).filter_by(tenant_id="t1").all()}
        assert vars_["oferta.nome"] == "Tiragem Express"
        assert vars_["oferta.preco"] == 19.90
        assert vars_["oferta.descricao"] == "Descrição"
        assert vars_["oferta.gateway_padrao"] == "stripe"
    finally:
        db.close()


def test_save_oferta_aceita_preco_com_ponto_ou_virgula():
    save_oferta("ta", "T", "19.90", "", "stripe")
    save_oferta("tb", "T", "19,90", "", "stripe")
    db = SessionLocal()
    try:
        a = db.query(models.TenantFlowVariable).filter_by(tenant_id="ta", key="oferta.preco").first()
        b = db.query(models.TenantFlowVariable).filter_by(tenant_id="tb", key="oferta.preco").first()
        assert a.value_json == 19.90
        assert b.value_json == 19.90
    finally:
        db.close()


def test_save_oferta_preco_invalido_levanta():
    with pytest.raises(ValueError, match="preço"):
        save_oferta("t1", "T", "abc", "", "stripe")


def test_save_oferta_preco_negativo_levanta():
    with pytest.raises(ValueError, match="positivo"):
        save_oferta("t1", "T", "-5", "", "stripe")


def test_save_oferta_gateway_invalido_levanta():
    with pytest.raises(ValueError, match="gateway"):
        save_oferta("t1", "T", "19,90", "", "paypal")


# ─── save_template ───────────────────────────────────────────────────────────

def test_save_template_express_clona_seed():
    bp_id = save_template("t1", "tarot_express")
    db = SessionLocal()
    try:
        bp = db.query(models.FlowBlueprint).filter_by(id=bp_id).first()
        assert bp is not None
        assert bp.slug == "post_payment"
        assert bp.body_json["format"] == "acassia-flow"
        # Seed Express tem motor_ref pra envio de cartas
        types = [n.get("type") for n in bp.body_json["graph"]["nodes"]]
        assert "motor_ref" in types
    finally:
        db.close()


def test_save_template_premium_clona_seed():
    bp_id = save_template("t1", "quiromancia_premium")
    db = SessionLocal()
    try:
        bp = db.query(models.FlowBlueprint).filter_by(id=bp_id).first()
        assert bp is not None
        # Premium tem delay em dias
        delays = [n.get("config", {}) for n in bp.body_json["graph"]["nodes"] if n.get("type") == "delay"]
        assert any(d.get("delay_unit") in ("dia", "dias") for d in delays)
    finally:
        db.close()


def test_save_template_em_branco_cria_blueprint_vazio():
    bp_id = save_template("t1", "em_branco")
    db = SessionLocal()
    try:
        bp = db.query(models.FlowBlueprint).filter_by(id=bp_id).first()
        assert bp.body_json["graph"]["nodes"] == []
    finally:
        db.close()


def test_save_template_invalido_levanta():
    with pytest.raises(ValueError, match="template"):
        save_template("t1", "nao_existe")


def test_save_template_idempotente_atualiza():
    """Se chamado 2x, atualiza o mesmo blueprint (não duplica)."""
    save_template("t1", "tarot_express")
    save_template("t1", "quiromancia_premium")  # troca
    db = SessionLocal()
    try:
        bps = db.query(models.FlowBlueprint).filter_by(tenant_id="t1", slug="post_payment").all()
        assert len(bps) == 1
        assert "Premium" in bps[0].title or "Quiromancia" in bps[0].title
    finally:
        db.close()


# ─── save_whatsapp ───────────────────────────────────────────────────────────

def test_save_whatsapp_grava_vars_e_secret():
    save_whatsapp("t1", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxx")
    db = SessionLocal()
    try:
        phone = db.query(models.TenantFlowVariable).filter_by(tenant_id="t1", key="whatsapp.phone_number_id").first()
        waba = db.query(models.TenantFlowVariable).filter_by(tenant_id="t1", key="whatsapp.waba_id").first()
        token = db.query(models.TenantFlowSecret).filter_by(tenant_id="t1", key="whatsapp.access_token").first()
        assert phone.value_json == "12345"
        assert waba.value_json == "67890"
        assert token.value_cipher == "EAAxxxxxxxxxxxxxxxxxx"
    finally:
        db.close()


def test_save_whatsapp_phone_nao_numerico_levanta():
    with pytest.raises(ValueError, match="phone_number_id"):
        save_whatsapp("t1", "abc", "12345", "EAAxxxxxxxxxxxxxxxxxx")


def test_save_whatsapp_token_curto_levanta():
    with pytest.raises(ValueError, match="access_token"):
        save_whatsapp("t1", "12345", "67890", "curto")


# ─── Endpoints ───────────────────────────────────────────────────────────────

def test_index_sem_login_redireciona():
    flask_app = Flask("t", template_folder=_TEMPLATE_DIR)
    flask_app.config.update(SECRET_KEY="x", TESTING=True)
    login_manager.init_app(flask_app)
    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(onboarding_bp)
    client = flask_app.test_client()

    res = client.get("/saas/onboarding/", follow_redirects=False)
    assert res.status_code == 302
    assert "/saas/login" in res.headers.get("Location", "")


def test_index_logado_renderiza_step_persona(logged_in_client):
    client, user = logged_in_client
    res = client.get("/saas/onboarding/")
    assert res.status_code == 200
    assert b"Persona da cigana" in res.data


def test_post_persona_avanca_pra_oferta(logged_in_client):
    client, user = logged_in_client
    res = client.post("/saas/onboarding/persona", data={
        "name": "Esmeralda",
        "tone": "mistico",
        "backstory": "História mística suficientemente longa aqui",
        "restrictions": ["nao_promete_cura"],
    }, follow_redirects=False)
    assert res.status_code == 302

    # próximo GET deve renderizar step oferta
    res2 = client.get("/saas/onboarding/")
    assert b"Oferta principal" in res2.data


def test_post_persona_invalida_retorna_400(logged_in_client):
    client, user = logged_in_client
    res = client.post("/saas/onboarding/persona", data={
        "name": "",
        "tone": "mistico",
        "backstory": "ok longo o bastante aqui",
    })
    assert res.status_code == 400


def test_fluxo_completo_termina_em_signup_done(logged_in_client):
    client, user = logged_in_client
    client.post("/saas/onboarding/persona", data={
        "name": "X", "tone": "direto",
        "backstory": "História suficientemente longa aqui sim",
    })
    client.post("/saas/onboarding/oferta", data={
        "nome": "Tiragem", "preco": "19,90", "gateway": "stripe",
    })
    client.post("/saas/onboarding/template", data={"template": "tarot_express"})
    res = client.post("/saas/onboarding/whatsapp", data={
        "phone_number_id": "12345",
        "waba_id": "67890",
        "access_token": "EAAxxxxxxxxxxxxxxxxxx",
    }, follow_redirects=False)
    assert res.status_code == 302
    assert "/saas/signup/done" in res.headers.get("Location", "")


def test_fluxo_completo_resulta_em_step_done(logged_in_client):
    client, user = logged_in_client
    client.post("/saas/onboarding/persona", data={
        "name": "X", "tone": "direto",
        "backstory": "História suficientemente longa aqui sim",
    })
    client.post("/saas/onboarding/oferta", data={
        "nome": "Tiragem", "preco": "19,90", "gateway": "stripe",
    })
    client.post("/saas/onboarding/template", data={"template": "tarot_express"})
    client.post("/saas/onboarding/whatsapp", data={
        "phone_number_id": "12345",
        "waba_id": "67890",
        "access_token": "EAAxxxxxxxxxxxxxxxxxx",
    })

    assert detect_current_step(user.tenant_id) == STEP_DONE
