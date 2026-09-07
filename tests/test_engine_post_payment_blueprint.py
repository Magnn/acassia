"""Testes do hook post_payment em Motor.iniciar_fluxo_post_venda (ADR_006).

Foca em `Motor._compile_post_payment_blueprint` isoladamente. Não exercita
o fluxo completo de iniciar_fluxo_post_venda (que tem muitas dependências
do estado real do motor — mocking total seria frágil).
"""

import pytest

from db import models
from db.database import Base, SessionLocal, engine as db_engine
from schema import Acao, ContextoConversa


@pytest.fixture(autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=db_engine)
    db = SessionLocal()
    db.query(models.FlowBlueprint).delete()
    db.query(models.Lead).delete()
    db.commit()
    db.close()
    yield


def _make_motor(tenant_id: str = "default"):
    """Constrói Motor sem rodar __init__ pesado — só precisa de tenant_id."""
    from engine import Engine
    motor = Engine.__new__(Engine)
    motor.tenant_id = tenant_id
    return motor


def _seed_lead(tenant_id: str = "default", telefone: str = "5511999999999") -> int:
    db = SessionLocal()
    try:
        lead = models.Lead(tenant_id=tenant_id, telefone=telefone, node_atual="14_confirmacao_entrega")
        db.add(lead)
        db.commit()
        return lead.id
    finally:
        db.close()


def _seed_post_payment_blueprint(tenant_id: str = "default", body: dict | None = None) -> int:
    db = SessionLocal()
    try:
        bp = models.FlowBlueprint(
            tenant_id=tenant_id,
            slug="post_payment",
            title="Test Post Payment",
            body_json=body or {"format": "meumisterio-flow", "version": 1, "title": "T", "graph": {"nodes": [], "edges": []}},
        )
        db.add(bp)
        db.commit()
        return bp.id
    finally:
        db.close()


def _make_ctx(node_atual: str = "14_confirmacao_entrega") -> ContextoConversa:
    return ContextoConversa(
        lead_id=1,
        telefone="5511999999999",
        node_atual=node_atual,
        texto_recebido="SISTEMA_WEBHOOK",
        tipo_mensagem="system",
    )


# ─── Caminho de fallback (sem blueprint) ─────────────────────────────────────

def test_retorna_none_quando_tenant_nao_tem_blueprint():
    lead_id = _seed_lead()
    motor = _make_motor()
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        result = motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert result is None
    finally:
        db.close()


def test_retorna_none_quando_blueprint_eh_de_outro_tenant():
    """Isolamento estrito: blueprint do tenant_a não deve aparecer no tenant_b."""
    lead_id = _seed_lead(tenant_id="default")
    _seed_post_payment_blueprint(tenant_id="tenant_a")
    motor = _make_motor(tenant_id="default")
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        result = motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert result is None
    finally:
        db.close()


def test_retorna_none_quando_blueprint_de_outro_slug():
    """Só blueprint slug='post_payment' interessa — outros são ignorados."""
    lead_id = _seed_lead()
    db = SessionLocal()
    try:
        bp = models.FlowBlueprint(
            tenant_id="default", slug="some_other", title="T", body_json={}
        )
        db.add(bp)
        db.commit()
    finally:
        db.close()
    motor = _make_motor()
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        result = motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert result is None
    finally:
        db.close()


# ─── Caminho feliz ───────────────────────────────────────────────────────────

def test_retorna_acoes_quando_blueprint_existe(monkeypatch):
    lead_id = _seed_lead()
    _seed_post_payment_blueprint()
    fake_acoes = [Acao(tipo="text", conteudo="primeira"), Acao(tipo="text", conteudo="segunda")]
    monkeypatch.setattr("flow_executor.document_to_acoes", lambda *a, **k: fake_acoes)
    motor = _make_motor()
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        result = motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert result == fake_acoes
    finally:
        db.close()


def test_passa_tenant_id_e_blueprint_id_pro_compile(monkeypatch):
    lead_id = _seed_lead()
    bp_id = _seed_post_payment_blueprint(tenant_id="tenant_x")
    seen_kwargs: dict = {}

    def capture(*a, **k):
        seen_kwargs.update(k)
        return []

    monkeypatch.setattr("flow_executor.document_to_acoes", capture)
    motor = _make_motor(tenant_id="tenant_x")
    db = SessionLocal()
    try:
        # Re-seed lead pro tenant_x
        db.query(models.Lead).filter_by(id=lead_id).delete()
        db.commit()
        lead = models.Lead(tenant_id="tenant_x", telefone="5511888888888", node_atual="x")
        db.add(lead)
        db.commit()

        motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert seen_kwargs.get("tenant_id") == "tenant_x"
        assert seen_kwargs.get("blueprint_id") == bp_id
    finally:
        db.close()


def test_context_passa_lead_data_e_metadata(monkeypatch):
    lead_id = _seed_lead()
    _seed_post_payment_blueprint()
    seen_ctx: dict = {}

    def capture(_doc, **k):
        seen_ctx.update(k.get("context") or {})
        return []

    monkeypatch.setattr("flow_executor.document_to_acoes", capture)
    motor = _make_motor()
    ctx = _make_ctx(node_atual="14_confirmacao_entrega")
    ctx.metadata["__config__"] = {"some": "config"}
    ctx.metadata["custom_key"] = "valor"
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        motor._compile_post_payment_blueprint(db, ctx, lead)
    finally:
        db.close()

    assert seen_ctx["lead_id"] == lead_id
    assert seen_ctx["telefone"] == "5511999999999"
    assert seen_ctx["node_atual"] == "14_confirmacao_entrega"
    assert seen_ctx["custom_key"] == "valor"
    assert seen_ctx["__config__"] == {"some": "config"}


# ─── Resiliência ─────────────────────────────────────────────────────────────

def test_excecao_no_compile_retorna_none(monkeypatch):
    """Blueprint corrompido → log + None (não propaga, garante fallback)."""
    lead_id = _seed_lead()
    _seed_post_payment_blueprint()

    def raise_err(*a, **k):
        raise RuntimeError("blueprint corrompido")

    monkeypatch.setattr("flow_executor.document_to_acoes", raise_err)
    motor = _make_motor()
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        result = motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert result is None
    finally:
        db.close()


def test_blueprint_com_body_json_none_retorna_lista_vazia_sem_crash(monkeypatch):
    """Tenant pode ter blueprint vazio; compile devolve []."""
    lead_id = _seed_lead()
    db = SessionLocal()
    try:
        bp = models.FlowBlueprint(
            tenant_id="default", slug="post_payment", title="T", body_json=None
        )
        db.add(bp)
        db.commit()
    finally:
        db.close()

    monkeypatch.setattr("flow_executor.document_to_acoes", lambda *a, **k: [])
    motor = _make_motor()
    db = SessionLocal()
    try:
        lead = db.query(models.Lead).filter_by(id=lead_id).first()
        result = motor._compile_post_payment_blueprint(db, _make_ctx(), lead)
        assert result == []  # blueprint vazio: lista vazia (não None — não há fallback aqui)
    finally:
        db.close()
