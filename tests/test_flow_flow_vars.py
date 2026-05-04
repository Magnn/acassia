"""B3: variáveis de fluxo (HTTP → {{chave}} no passo seguinte)."""

import pytest

from flow_executor import apply_flow_template, document_to_acoes, steps_to_acoes


def test_apply_flow_template_simple():
    assert apply_flow_template("Olá {{nome}}", {"nome": "Ana"}) == "Olá Ana"
    assert apply_flow_template("{{flow_http__h}}", {"flow_http__h": {"status": 200, "body": "ok"}}) == "ok"


@pytest.fixture
def allow_http(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_HTTP", True)


def test_steps_http_then_message_save_as(allow_http, monkeypatch):
    class Resp:
        status_code = 200
        text = "preco_fixo"

    monkeypatch.setattr("flow_executor.requests.request", lambda **kw: Resp())

    doc = {
        "format": "meumisterio-flow",
        "version": 1,
        "title": "HTTP var",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {
                    "id": "h1",
                    "type": "api",
                    "config": {"url": "https://example.com/x", "method": "GET", "save_as": "preco"},
                },
                {"id": "m1", "type": "conteudo", "config": {"body": "Valor: {{preco}}"}},
            ],
            "edges": [
                {"from": "t", "to": "h1"},
                {"from": "h1", "to": "m1"},
            ],
        },
    }
    out = {}
    acoes = document_to_acoes(doc, context={}, flow_vars_metadata_out=out)
    texts = [a.conteudo for a in acoes if a.tipo == "text"]
    assert any("Valor: preco_fixo" in (t or "") for t in texts)
    assert "preco" in out
    assert out["preco"] == "preco_fixo"


def test_document_to_acoes_flow_http_key_in_template(allow_http, monkeypatch):
    class Resp:
        status_code = 200
        text = "body_text"

    monkeypatch.setattr("flow_executor.requests.request", lambda **kw: Resp())

    doc = {
        "format": "meumisterio-flow",
        "version": 1,
        "title": "HTTP key",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {"id": "hx", "type": "api", "config": {"url": "https://example.com/y", "method": "GET"}},
                {"id": "m1", "type": "conteudo", "config": {"body": "R: {{flow_http__hx}}"}},
            ],
            "edges": [
                {"from": "t", "to": "hx"},
                {"from": "hx", "to": "m1"},
            ],
        },
    }
    acoes = document_to_acoes(doc, context={})
    texts = [a.conteudo for a in acoes if a.tipo == "text"]
    assert any("R: body_text" in (t or "") for t in texts)


def test_steps_to_acoes_metadata_out_only_http_keys(allow_http, monkeypatch):
    class Resp:
        status_code = 201
        text = "x"

    monkeypatch.setattr("flow_executor.requests.request", lambda **kw: Resp())

    steps = [
        {
            "order": 1,
            "node_id": "n1",
            "type": "api",
            "config": {"url": "https://example.com/z", "method": "GET"},
        },
    ]
    meta = {}
    flow_vars = {}
    steps_to_acoes(steps, flow_vars=flow_vars, flow_vars_metadata_out=meta)
    assert "flow_http__n1" in meta
    assert meta["flow_http__n1"]["status"] == 201
