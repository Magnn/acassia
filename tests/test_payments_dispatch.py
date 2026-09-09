"""Testes do dispatch de pós-pagamento → blueprint."""

from unittest.mock import patch

import pytest

from api.payments.dispatch import (
    POST_PAYMENT_SLUG,
    _run_post_payment,
    dispatch_post_payment_blueprint,
)
from db import models
from db.database import Base, SessionLocal, engine


@pytest.fixture(autouse=True)
def _setup_db():
    """Tabelas criadas + Lead/FlowBlueprint limpos por teste."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(models.FlowBlueprint).delete()
    db.query(models.Lead).delete()
    db.commit()
    db.close()
    yield


def _seed_lead(tenant_id: str = "default", telefone: str = "5511999999999") -> int:
    db = SessionLocal()
    try:
        lead = models.Lead(tenant_id=tenant_id, telefone=telefone, node_atual="9_entrega")
        db.add(lead)
        db.commit()
        return lead.id
    finally:
        db.close()


def _seed_blueprint(
    tenant_id: str = "default",
    slug: str = POST_PAYMENT_SLUG,
    body: dict | None = None,
) -> int:
    db = SessionLocal()
    try:
        bp = models.FlowBlueprint(
            tenant_id=tenant_id,
            slug=slug,
            title="Post payment test",
            body_json=body or {"trigger": "webhook.payment.approved", "nodes": []},
        )
        db.add(bp)
        db.commit()
        return bp.id
    finally:
        db.close()


# ─── Early returns / validações ──────────────────────────────────────────────

def test_dispatch_retorna_false_sem_blueprint():
    lead_id = _seed_lead()
    assert dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=lead_id,
        provider="stripe",
        event_id="evt_1",
    ) is False


def test_dispatch_retorna_false_sem_lead():
    _seed_blueprint()
    assert dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=99999,
        provider="stripe",
        event_id="evt_1",
    ) is False


def test_dispatch_retorna_false_se_lead_de_outro_tenant():
    """Isolamento estrito multi-tenant: lookup de lead exige tenant_id correto."""
    lead_id = _seed_lead(tenant_id="tenant_a")
    _seed_blueprint(tenant_id="tenant_b")
    assert dispatch_post_payment_blueprint(
        tenant_id="tenant_b",
        lead_id=lead_id,
        provider="stripe",
        event_id="evt_1",
    ) is False


def test_dispatch_blueprint_de_outro_slug_nao_serve():
    lead_id = _seed_lead()
    _seed_blueprint(slug="some_other_purpose")
    assert dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=lead_id,
        provider="stripe",
        event_id="evt_1",
    ) is False


def test_dispatch_blueprint_de_outro_tenant_nao_serve():
    lead_id = _seed_lead(tenant_id="default")
    _seed_blueprint(tenant_id="outro_tenant")
    assert dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=lead_id,
        provider="stripe",
        event_id="evt_1",
    ) is False


# ─── Caminho feliz ───────────────────────────────────────────────────────────

@patch("api.utils.task_queue.enqueue_post_payment", return_value=True)
def test_dispatch_enfileira_job_duravel_quando_tudo_certo(mock_enqueue):
    lead_id = _seed_lead()
    _seed_blueprint()

    ok = dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=lead_id,
        provider="stripe",
        event_id="evt_xyz",
        payment_metadata={"amount": 1990, "currency": "BRL"},
    )

    assert ok is True
    mock_enqueue.assert_called_once()


@patch("api.utils.task_queue.enqueue_post_payment", return_value=True)
def test_dispatch_passa_payload_correto_pra_fila(mock_enqueue):
    lead_id = _seed_lead()
    _seed_blueprint()

    dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=lead_id,
        provider="cakto",
        event_id="evt_args",
        payment_metadata={"product": "tiragem"},
    )

    args = mock_enqueue.call_args.kwargs
    assert args["tenant_id"] == "default"
    assert isinstance(args["blueprint_id"], int)
    assert args["lead_id"] == lead_id
    assert args["provider"] == "cakto"
    assert args["event_id"] == "evt_args"
    assert args["payment_metadata"] == {"product": "tiragem"}


@patch("api.utils.task_queue.enqueue_post_payment", return_value=True)
def test_dispatch_payment_metadata_default_eh_dict_vazio(mock_enqueue):
    lead_id = _seed_lead()
    _seed_blueprint()

    dispatch_post_payment_blueprint(
        tenant_id="default",
        lead_id=lead_id,
        provider="stripe",
        event_id="evt_empty",
        # sem payment_metadata
    )
    assert mock_enqueue.call_args.kwargs["payment_metadata"] == {}


# ─── _run_post_payment isolado ───────────────────────────────────────────────

def test_run_post_payment_compila_blueprint_e_injeta_payment_no_context():
    lead_id = _seed_lead()
    bp_id = _seed_blueprint()

    fake_acoes = ["acao1", "acao2", "acao3"]
    fake_engine = type("Runtime", (), {
        "personalizer": None,
        "_buscar_historico": lambda self, db, lead_id, limit: [],
        "_processar_fila": lambda self, lead_id, ctx, acoes: None,
    })()
    with patch("flow_executor.document_to_acoes", return_value=fake_acoes) as m_compile:
        with patch("flow_executor.flow_context_from_lead", return_value={"nome": "Maria"}) as m_ctx:
            _run_post_payment(
                tenant_id="default",
                blueprint_id=bp_id,
                lead_id=lead_id,
                provider="stripe",
                event_id="evt_y",
                payment_metadata={"amount": 1990, "product": "tiragem"}, engine=fake_engine,
            )

    m_ctx.assert_called_once()
    m_compile.assert_called_once()
    # Context recebeu chave 'payment' com metadata expandida
    ctx_passed = m_compile.call_args.kwargs["context"]
    assert ctx_passed["nome"] == "Maria"
    assert ctx_passed["payment"]["provider"] == "stripe"
    assert ctx_passed["payment"]["event_id"] == "evt_y"
    assert ctx_passed["payment"]["amount"] == 1990
    assert ctx_passed["payment"]["product"] == "tiragem"


def test_run_post_payment_passa_tenant_e_blueprint_id_pra_compile():
    lead_id = _seed_lead(tenant_id="tenant_x")
    bp_id = _seed_blueprint(tenant_id="tenant_x")

    with patch("flow_executor.document_to_acoes", return_value=[]) as m_compile:
        with patch("flow_executor.flow_context_from_lead", return_value={}):
            with pytest.raises(ValueError, match="without_actions"):
                _run_post_payment(
                    tenant_id="tenant_x", blueprint_id=bp_id, lead_id=lead_id,
                    provider="stripe", event_id="evt_z", payment_metadata={},
                )

    kwargs = m_compile.call_args.kwargs
    assert kwargs["tenant_id"] == "tenant_x"
    assert kwargs["blueprint_id"] == bp_id


def test_run_post_payment_propaga_excecao_para_retry_da_fila():
    lead_id = _seed_lead()
    bp_id = _seed_blueprint()

    with patch("flow_executor.document_to_acoes", side_effect=RuntimeError("blueprint quebrou")):
        with patch("flow_executor.flow_context_from_lead", return_value={}):
            with pytest.raises(RuntimeError, match="blueprint quebrou"):
                _run_post_payment(
                    tenant_id="default", blueprint_id=bp_id, lead_id=lead_id,
                    provider="cakto", event_id="evt_crash", payment_metadata={},
                )


def test_run_post_payment_aborta_se_blueprint_sumir_entre_dispatch_e_execucao():
    """Race: blueprint deletado entre dispatch e thread executar."""
    lead_id = _seed_lead()

    with patch("flow_executor.document_to_acoes") as m_compile:
        with patch("flow_executor.flow_context_from_lead") as m_ctx:
            _run_post_payment(
                tenant_id="default",
                blueprint_id=99999,  # não existe
                lead_id=lead_id,
                provider="stripe",
                event_id="evt_abort",
                payment_metadata={},
            )

    m_compile.assert_not_called()
    m_ctx.assert_not_called()
