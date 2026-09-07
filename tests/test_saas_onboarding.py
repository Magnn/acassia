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
def _mock_meta(monkeypatch):
    monkeypatch.setattr("api.saas.integrations_whatsapp._validate_token_and_phone", lambda *args: (True, {}))
    monkeypatch.setattr("meta_graph_admin.subscribe_apps_to_waba", lambda *args: (True, {"success": True}))


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.User).delete()
    db.query(models.StudioAgent).delete()
    db.query(models.StudioAgentVersion).delete()
    db.query(models.FlowBlueprint).delete()
    db.query(models.FlowPublish).delete()
    db.query(models.TenantFlowVariable).delete()
    db.query(models.TenantFlowSecret).delete()
    db.query(models.WaPhoneTenantBinding).delete()
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
    save_persona("t1", "Esmeralda", "acolhedor", "Meu Mistério ancestral com dom genuíno", [])
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
    agent = save_persona("t1", "Esmeralda", "mistico", "História mística da meumisterio ancestral", ["nao_promete_cura"])
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
        assert bp.body_json["format"] == "meumisterio-flow"
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
    with SessionLocal() as db:
        assert not db.query(models.TenantFlowVariable).filter_by(tenant_id="t1", key="template_escolhido").first()


def test_persona_edit_preserves_version_history():
    agent = save_persona("t1", "Ana", "direto", "Atendimento da nossa empresa", [])
    save_persona("t1", "Bia", "acolhedor", "Atendimento atualizado da empresa", [])
    with SessionLocal() as db:
        versions = db.query(models.StudioAgentVersion).filter_by(agent_id=agent.id).order_by(models.StudioAgentVersion.version_number).all()
        assert [v.version_number for v in versions] == [1, 2]
        assert versions[0].body_json["tone"] == "direto"


@pytest.mark.parametrize("price", ["nan", "inf", "-inf"])
def test_nonfinite_price_rejected(price):
    with pytest.raises(ValueError):
        save_oferta("t1", "Produto", price, "", "stripe")


def test_phone_conflict_does_not_change_tenant_configuration():
    save_whatsapp("owner", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxx")
    with pytest.raises(ValueError, match="outro tenant"):
        save_whatsapp("other", "12345", "99999", "EAAyyyyyyyyyyyyyyyyyy")
    with SessionLocal() as db:
        assert db.query(models.TenantFlowVariable).filter_by(tenant_id="other").count() == 0
        assert db.query(models.TenantFlowSecret).filter_by(tenant_id="other").count() == 0
        assert db.get(models.WaPhoneTenantBinding, "12345").tenant_id == "owner"


def test_validation_outage_does_not_activate_phone(monkeypatch):
    def unavailable(*args):
        raise ConnectionError("offline")
    monkeypatch.setattr("api.saas.integrations_whatsapp._validate_token_and_phone", unavailable)
    with pytest.raises(ValueError, match="validar"):
        save_whatsapp("t1", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxx")
    with SessionLocal() as db:
        assert db.get(models.WaPhoneTenantBinding, "12345") is None
        assert db.query(models.TenantFlowVariable).filter_by(tenant_id="t1").count() == 0


def test_pending_whatsapp_does_not_finish_onboarding():
    save_persona("t1", "Ana", "direto", "Atendimento da nossa empresa", [])
    save_oferta("t1", "Produto", "10", "", "stripe")
    save_template("t1", "em_branco")
    save_whatsapp("t1", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxx", skip_validation=True)
    assert detect_current_step("t1") == STEP_WHATSAPP


def test_readiness_requires_authentication(client):
    assert client.get("/saas/onboarding/readiness").status_code == 302


def test_whatsapp_uses_request_host_and_preserves_webhook_path(logged_in_client, monkeypatch):
    client, user = logged_in_client
    monkeypatch.delenv("PUBLIC_URL", raising=False)
    payload = {"phone_number_id": "123456789", "waba_id": "987654321", "access_token": "EAAxxxxxxxxxxxxxxxxxx"}
    first = client.post("/saas/onboarding/whatsapp", json=payload, base_url="https://localhost")
    assert first.status_code == 200
    url = first.json["binding"]["webhook_url"]
    assert url.startswith("https://localhost/webhook/wh_")
    second = client.post("/saas/onboarding/whatsapp", json=payload, base_url="https://localhost")
    assert second.json["binding"]["webhook_url"] == url


@pytest.mark.parametrize("delivery_status,expected", [(None, False), ("failed", False), ("sent", True), ("delivered", True), ("read", True)])
def test_readiness_requires_successful_outbound_status(delivery_status, expected):
    from launch_readiness import launch_readiness
    with SessionLocal() as db:
        lead = models.Lead(tenant_id="readiness-delivery", telefone="5592999991111")
        db.add(lead)
        db.flush()
        db.add(models.Mensagem(lead_id=lead.id, remetente="bot", texto="Resposta", delivery_status=delivery_status))
        db.commit()
    steps = {s["key"]: s["completed"] for s in launch_readiness("readiness-delivery")["steps"]}
    assert steps["reply"] is expected


def test_readiness_is_scoped_to_logged_in_tenant(logged_in_client):
    client, user = logged_in_client
    save_persona("other", "Ana", "direto", "Atendimento da nossa empresa", [])
    save_oferta("other", "Produto", "10", "", "stripe")
    save_template("other", "tarot_express")
    save_whatsapp("other", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxx")
    response = client.get("/saas/onboarding/readiness?tenant=other")
    assert response.status_code == 200
    assert response.json["completed_count"] == 0
    assert "EAA" not in response.get_data(as_text=True)


def test_readiness_distinguishes_saved_connection_from_received_message():
    from launch_readiness import launch_readiness
    save_whatsapp("t1", "12345", "67890", "EAAxxxxxxxxxxxxxxxxxx")
    steps = {s["key"]: s["completed"] for s in launch_readiness("t1")["steps"]}
    assert steps["whatsapp"] is True
    assert steps["inbound"] is False
    assert steps["published"] is False
    with SessionLocal() as db:
        db.get(models.WaPhoneTenantBinding, "12345").inbound_count = 1
        db.commit()
    steps = {s["key"]: s["completed"] for s in launch_readiness("t1")["steps"]}
    assert steps["inbound"] is True


def test_sales_starter_keeps_post_payment_and_waits_for_each_reply():
    from flow_builder_runtime import validate_flow_document
    from published_flow_runtime import execute_published_flow_turn
    save_oferta("t1", "Consultoria", "100", "Sessão de planejamento", "stripe")
    post_payment_id = save_template("t1", "tarot_express")
    commercial_id = save_template("t1", "atendimento_comercial")
    assert commercial_id != post_payment_id
    with SessionLocal() as db:
        doc = db.get(models.FlowBlueprint, commercial_id).body_json
        assert db.get(models.FlowBlueprint, post_payment_id).slug == "post_payment"
    assert validate_flow_document(doc, strict=True)["ok"]
    args = dict(blueprint_id=commercial_id, tenant_id="t1", lead_id=42)
    first = execute_published_flow_turn(doc, message="Olá", **args)
    assert first.state["status"] == "waiting"
    assert not any("Consultoria" in a.conteudo for a in first.actions)
    second = execute_published_flow_turn(doc, message="Planejar minha empresa", existing_state=first.state, **args)
    assert second.state["vars"]["necessidade"] == "Planejar minha empresa"
    assert any("Consultoria" in a.conteudo for a in second.actions)
    assert second.state["status"] == "waiting"
    third = execute_published_flow_turn(doc, message="Como agendar?", existing_state=second.state, **args)
    assert third.state["vars"]["duvida_comercial"] == "Como agendar?"
    assert third.state["status"] == "completed"
    assert any(effect["kind"] == "notify_attendant" and "Como agendar?" in effect["payload"] for effect in third.side_effects)


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
    assert b"Persona da meumisterio" in res.data


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
