"""Testes do validador de blueprints post_payment."""

from typing import Any

from flows.post_payment.validator import (
    CONFIRMATION_MAX_DELAY_SECONDS,
    POST_PAYMENT_TRIGGER_EVENT,
    _delay_node_seconds,
    _has_acao_node,
    _shortest_delay_to_message,
    validate_post_payment_blueprint,
)


def _doc(graph_nodes: list, graph_edges: list, title: str = "PostPayment Test") -> dict:
    """Helper: monta um documento meumisterio-flow v1 mínimo."""
    return {
        "format": "meumisterio-flow",
        "version": 1,
        "title": title,
        "graph": {"nodes": graph_nodes, "edges": graph_edges},
    }


def _trigger(node_id: str = "t1", event: str = POST_PAYMENT_TRIGGER_EVENT) -> dict:
    return {"id": node_id, "type": "trigger", "config": {"event": event}}


def _mensagem(node_id: str, texto: str = "olá!") -> dict:
    return {"id": node_id, "type": "conteudo", "config": {"content_text": texto}}


def _delay(node_id: str, seconds: float = 0, **extra) -> dict:
    cfg: dict[str, Any] = {"seconds": seconds, **extra}
    return {"id": node_id, "type": "delay", "config": cfg}


def _acao(node_id: str, action_kind: str = "add_tag") -> dict:
    return {"id": node_id, "type": "acao", "config": {"action_kind": action_kind, "payload": "convertido"}}


def _edge(src: str, dst: str) -> dict:
    return {"id": f"{src}-{dst}", "from": src, "to": dst}


# ─── Caminho feliz ───────────────────────────────────────────────────────────

def test_valid_post_payment_minimo():
    doc = _doc(
        graph_nodes=[_trigger(), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "m1"), _edge("m1", "a1")],
    )
    res = validate_post_payment_blueprint(doc)
    assert res["ok"] is True
    assert res["errors"] == []
    assert res["post_payment_issues"] == []


def test_valid_post_payment_com_delay_curto():
    """Mensagem 30s depois do trigger — dentro do limite."""
    doc = _doc(
        graph_nodes=[_trigger(), _delay("d1", seconds=30), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "d1"), _edge("d1", "m1"), _edge("m1", "a1")],
    )
    res = validate_post_payment_blueprint(doc)
    assert res["ok"] is True


# ─── Regra 1: trigger event ─────────────────────────────────────────────────

def test_invalid_trigger_event_outro_valor():
    doc = _doc(
        graph_nodes=[_trigger(event="webhook.message.received"), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "m1")],
    )
    res = validate_post_payment_blueprint(doc)
    assert res["ok"] is False
    codes = [e["code"] for e in res["errors"]]
    assert "pp_invalid_trigger_event" in codes


def test_invalid_trigger_event_vazio():
    doc = _doc(
        graph_nodes=[_trigger(event=""), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "m1")],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_invalid_trigger_event" in codes


def test_no_trigger_node():
    doc = _doc(
        graph_nodes=[_mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("m1", "a1")],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_no_trigger" in codes


# ─── Regra 2: mensagem em ≤ 60s ─────────────────────────────────────────────

def test_no_message_reachable():
    doc = _doc(
        graph_nodes=[_trigger(), _delay("d1"), _acao("a1")],
        graph_edges=[_edge("t1", "d1"), _edge("d1", "a1")],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_no_confirmation_message" in codes


def test_late_confirmation_61s_falha():
    doc = _doc(
        graph_nodes=[_trigger(), _delay("d1", seconds=61), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "d1"), _edge("d1", "m1")],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_late_confirmation" in codes


def test_late_confirmation_aceita_no_limite():
    """Exatamente 60s é OK (limite inclusivo)."""
    doc = _doc(
        graph_nodes=[_trigger(), _delay("d1", seconds=60), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "d1"), _edge("d1", "m1")],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_late_confirmation" not in codes


def test_caminho_mais_curto_eh_escolhido():
    """
    Há dois caminhos do trigger: um curto (30s) e um longo (120s).
    Validação deve usar o curto e aceitar.
    """
    doc = _doc(
        graph_nodes=[
            _trigger(),
            _delay("d_curto", seconds=30),
            _delay("d_longo", seconds=120),
            _mensagem("m_curto"),
            _mensagem("m_longo"),
            _acao("a1"),
        ],
        graph_edges=[
            _edge("t1", "d_curto"), _edge("d_curto", "m_curto"),
            _edge("t1", "d_longo"), _edge("d_longo", "m_longo"),
        ],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_late_confirmation" not in codes


def test_pergunta_tambem_conta_como_mensagem():
    doc = _doc(
        graph_nodes=[
            _trigger(),
            {"id": "p1", "type": "pergunta", "config": {"question": "ok?"}},
            _acao("a1"),
        ],
        graph_edges=[_edge("t1", "p1")],
    )
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "pp_no_confirmation_message" not in codes


# ─── Regra 3: warning de tag de conversão ───────────────────────────────────

def test_warning_quando_sem_acao_node():
    doc = _doc(
        graph_nodes=[_trigger(), _mensagem("m1")],
        graph_edges=[_edge("t1", "m1")],
    )
    res = validate_post_payment_blueprint(doc)
    warning_codes = [w["code"] for w in res["warnings"]]
    assert "pp_no_conversion_tag" in warning_codes
    # warnings não bloqueiam publish
    assert res["ok"] is True


def test_sem_warning_quando_acao_presente():
    doc = _doc(
        graph_nodes=[_trigger(), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "m1"), _edge("m1", "a1")],
    )
    res = validate_post_payment_blueprint(doc)
    warning_codes = [w["code"] for w in res["warnings"]]
    assert "pp_no_conversion_tag" not in warning_codes


# ─── Helpers expostos ────────────────────────────────────────────────────────

def test_delay_node_seconds_formato_legado():
    n = {"type": "delay", "config": {"seconds": 45}}
    assert _delay_node_seconds(n) == 45.0


def test_delay_node_seconds_formato_amount_unit_minutos():
    n = {"type": "delay", "config": {"delay_amount": 2, "delay_unit": "min"}}
    assert _delay_node_seconds(n) == 120.0


def test_delay_node_seconds_formato_amount_unit_horas():
    n = {"type": "delay", "config": {"delay_amount": 1, "delay_unit": "h"}}
    assert _delay_node_seconds(n) == 3600.0


def test_delay_node_seconds_formato_amount_unit_dias():
    n = {"type": "delay", "config": {"delay_amount": 1, "delay_unit": "dia"}}
    assert _delay_node_seconds(n) == 86400.0


def test_delay_node_seconds_smart_min():
    n = {"type": "delay", "config": {"delay_smart_min": 10, "delay_smart_max": 30}}
    assert _delay_node_seconds(n) == 10.0


def test_delay_node_seconds_config_invalida_retorna_zero():
    n = {"type": "delay", "config": {"seconds": "abc"}}
    assert _delay_node_seconds(n) == 0.0


def test_has_acao_node_true_e_false():
    assert _has_acao_node([_acao("a")]) is True
    assert _has_acao_node([_trigger()]) is False
    assert _has_acao_node([]) is False


def test_shortest_delay_to_message_simples():
    nodes = [_trigger(), _delay("d1", seconds=15), _mensagem("m1")]
    edges = [_edge("t1", "d1"), _edge("d1", "m1")]
    assert _shortest_delay_to_message("t1", nodes, edges) == 15.0


def test_shortest_delay_to_message_sem_caminho():
    nodes = [_trigger(), _acao("a1")]
    edges = [_edge("t1", "a1")]
    assert _shortest_delay_to_message("t1", nodes, edges) is None


def test_shortest_delay_to_message_start_inexistente():
    nodes = [_mensagem("m1")]
    edges = []
    assert _shortest_delay_to_message("nao_existe", nodes, edges) is None


# ─── Integração com base ─────────────────────────────────────────────────────

def test_erros_da_validacao_base_propagam():
    """Documento sem título deve falhar na validação base."""
    doc = {
        "format": "meumisterio-flow",
        "version": 1,
        # sem title
        "graph": {"nodes": [_trigger(), _mensagem("m1"), _acao("a1")], "edges": [_edge("t1", "m1")]},
    }
    res = validate_post_payment_blueprint(doc)
    codes = [e["code"] for e in res["errors"]]
    assert "missing_title" in codes
    assert res["ok"] is False


def test_resultado_preserva_campos_da_base():
    doc = _doc(
        graph_nodes=[_trigger(), _mensagem("m1"), _acao("a1")],
        graph_edges=[_edge("t1", "m1")],
    )
    res = validate_post_payment_blueprint(doc)
    # campos esperados da base + novo
    for key in ("ok", "errors", "warnings", "normalized", "compile_hint", "post_payment_issues"):
        assert key in res
