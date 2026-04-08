"""Testes do runtime do Flow Builder."""
from flow_builder_runtime import compile_flow_plan, validate_flow_document


def test_validate_simple_chain():
    doc = {
        "format": "acassia-flow",
        "version": 1,
        "title": "Teste",
        "graph": {
            "nodes": [
                {"id": "a", "type": "trigger", "label": "G", "x": 0, "y": 0, "config": {}},
                {"id": "b", "type": "conteudo", "label": "C", "x": 100, "y": 0, "config": {"body": "oi"}},
            ],
            "edges": [{"from": "a", "to": "b"}],
        },
    }
    r = validate_flow_document(doc)
    assert r["ok"] is True
    assert len(r["compile_hint"]["steps"]) == 2


def test_cycle_detected():
    doc = {
        "format": "acassia-flow",
        "version": 1,
        "title": "Ciclo",
        "graph": {
            "nodes": [
                {"id": "a", "type": "trigger", "label": "", "config": {}},
                {"id": "b", "type": "conteudo", "label": "", "config": {}},
            ],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
        },
    }
    r = validate_flow_document(doc)
    assert r["ok"] is False


def test_compile_empty_edges_fallback():
    doc = {
        "format": "acassia-flow",
        "version": 1,
        "title": "Só nós",
        "graph": {
            "nodes": [
                {"id": "x", "type": "webhook", "label": "", "x": 10, "y": 0, "config": {}},
                {"id": "y", "type": "end", "label": "", "x": 200, "y": 0, "config": {}},
            ],
            "edges": [],
        },
    }
    p = compile_flow_plan(doc)
    assert p["ok"] is True
    assert len(p["steps"]) == 2
