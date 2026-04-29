"""C3: bloco motor_ref com whitelist e hook Python."""

from flow_executor import document_to_acoes, steps_to_acoes
from flow_motor_ref import invoke_flow_motor_ref


def test_invoke_demo_hook():
    acoes, err = invoke_flow_motor_ref(
        "flows.flow_blueprint_motor.demo:demo_greeting",
        {"nome": "Teste"},
        node_id="n1",
        blueprint_id=1,
        tenant_id="t",
    )
    assert err is None
    assert len(acoes) == 1
    assert "Teste" in (acoes[0].conteudo or "")
    assert (acoes[0].metadata or {}).get("runtime") == "motor_ref"


def test_invoke_rejects_non_allowlist():
    acoes, err = invoke_flow_motor_ref(
        "os.path:join",
        {},
        node_id="x",
        blueprint_id=None,
        tenant_id=None,
    )
    assert acoes == []
    assert err


def test_steps_motor_ref_resolved(monkeypatch):
    monkeypatch.setattr("flow_motor_ref._ALLOW_MOTOR_REF", True)
    steps = [
        {
            "order": 1,
            "node_id": "mr",
            "type": "motor_ref",
            "config": {"module_hint": "flows.flow_blueprint_motor.demo:demo_greeting"},
        },
    ]
    acoes = steps_to_acoes(steps, flow_vars={"nome": "Ana"}, blueprint_id=3, tenant_id="z")
    assert len(acoes) == 1
    assert "Ana" in (acoes[0].conteudo or "")


def test_steps_motor_ref_pending_when_disabled(monkeypatch):
    monkeypatch.setattr("flow_motor_ref._ALLOW_MOTOR_REF", False)
    steps = [
        {
            "order": 1,
            "node_id": "mr",
            "type": "motor_ref",
            "config": {"module_hint": "flows.flow_blueprint_motor.demo:demo_greeting"},
        },
    ]
    acoes = steps_to_acoes(steps, flow_vars={})
    assert len(acoes) == 1
    assert (acoes[0].metadata or {}).get("runtime") == "motor_ref_pending"


def test_document_linear_motor_ref(monkeypatch):
    monkeypatch.setattr("flow_motor_ref._ALLOW_MOTOR_REF", True)
    doc = {
        "format": "acassia-flow",
        "version": 1,
        "title": "M",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {
                    "id": "mr",
                    "type": "motor_ref",
                    "config": {"module_hint": "flows.flow_blueprint_motor.demo:demo_greeting"},
                },
            ],
            "edges": [{"from": "t", "to": "mr"}],
        },
    }
    acoes = document_to_acoes(doc, context={"nome": "B"})
    assert any("B" in (a.conteudo or "") for a in acoes if a.tipo == "text")
