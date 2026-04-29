"""Percurso com condicao (B1) e divisao A/B (B2) — alinhado a flow_graph_walk."""
from flow_executor import document_to_acoes
from flow_graph_walk import (
    divisao_persist_key,
    evaluate_condicao_rules,
    graph_has_condicao,
    graph_has_divisao,
    graph_walk_steps,
    pick_condicao_next_node,
)


def _doc_branching():
    return {
        "format": "acassia-flow",
        "version": 1,
        "title": "Cond test",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "label": "G", "config": {}},
                {
                    "id": "c",
                    "type": "condicao",
                    "label": "C",
                    "config": {
                        "logic": "AND",
                        "rules": [{"var": "nome", "op": "eq", "val": "Maria"}],
                    },
                },
                {"id": "a", "type": "conteudo", "label": "Sim", "config": {"body": "CAMINHO_SIM"}},
                {"id": "b", "type": "conteudo", "label": "Nao", "config": {"body": "CAMINHO_NAO"}},
            ],
            "edges": [
                {"from": "t", "to": "c"},
                {"from": "c", "to": "a", "label": "sim"},
                {"from": "c", "to": "b", "label": "não"},
            ],
        },
    }


def test_graph_has_condicao():
    assert graph_has_condicao(_doc_branching()) is True
    assert graph_has_condicao({"graph": {"nodes": [{"id": "x", "type": "conteudo", "config": {}}]}}) is False


def test_evaluate_rules_eq():
    cfg = {"logic": "AND", "rules": [{"var": "nome", "op": "eq", "val": "Maria"}]}
    assert evaluate_condicao_rules(cfg, {"nome": "Maria"}) == (True, "AND", True)
    assert evaluate_condicao_rules(cfg, {"nome": "João"}) == (False, "AND", True)


def test_pick_branch_labels():
    outs = [
        {"from": "c", "to": "a", "label": "sim"},
        {"from": "c", "to": "b", "label": "não"},
    ]
    assert pick_condicao_next_node({}, outs, True) == "a"
    assert pick_condicao_next_node({}, outs, False) == "b"


def test_graph_walk_maria_vs_joao():
    doc = _doc_branching()
    steps_m = graph_walk_steps(doc, {"nome": "Maria"})
    assert [s["node_id"] for s in steps_m] == ["a"]
    steps_j = graph_walk_steps(doc, {"nome": "João"})
    assert [s["node_id"] for s in steps_j] == ["b"]


def test_document_to_acoes_branching():
    doc = _doc_branching()
    acoes_m = document_to_acoes(doc, context={"nome": "Maria"})
    texts_m = [a.conteudo for a in acoes_m if a.tipo == "text"]
    assert any("CAMINHO_SIM" in (t or "") for t in texts_m)
    acoes_j = document_to_acoes(doc, context={"nome": "X"})
    texts_j = [a.conteudo for a in acoes_j if a.tipo == "text"]
    assert any("CAMINHO_NAO" in (t or "") for t in texts_j)


def test_linear_without_context_unchanged():
    doc = {
        "format": "acassia-flow",
        "version": 1,
        "title": "Linear",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {"id": "x", "type": "conteudo", "config": {"body": "hi"}},
            ],
            "edges": [{"from": "t", "to": "x"}],
        },
    }
    acoes = document_to_acoes(doc)
    assert any("hi" in (a.conteudo or "") for a in acoes if a.tipo == "text")


def _doc_divisao_ab():
    return {
        "format": "acassia-flow",
        "version": 1,
        "title": "Div A/B",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "label": "G", "config": {}},
                {
                    "id": "d",
                    "type": "divisao",
                    "label": "Split",
                    "config": {"weights": "A:50,B:50"},
                },
                {"id": "a", "type": "conteudo", "label": "A", "config": {"body": "TEXTO_A"}},
                {"id": "b", "type": "conteudo", "label": "B", "config": {"body": "TEXTO_B"}},
            ],
            "edges": [
                {"from": "t", "to": "d"},
                {"from": "d", "to": "a", "label": "A"},
                {"from": "d", "to": "b", "label": "B"},
            ],
        },
    }


def test_graph_has_divisao():
    assert graph_has_divisao(_doc_divisao_ab()) is True
    assert graph_has_divisao(_doc_branching()) is False


def test_graph_walk_divisao_deterministic_same_inputs():
    doc = _doc_divisao_ab()
    ctx = {"lead_id": "1001", "tenant_id": "tenant-x"}
    s1 = graph_walk_steps(doc, ctx, blueprint_id=99, tenant_id="tenant-x")
    s2 = graph_walk_steps(doc, ctx, blueprint_id=99, tenant_id="tenant-x")
    assert [x["node_id"] for x in s1] == [x["node_id"] for x in s2]
    assert len(s1) == 1
    assert s1[0]["node_id"] in ("a", "b")


def test_graph_walk_divisao_respects_stored_metadata():
    doc = _doc_divisao_ab()
    pkey = divisao_persist_key("d")
    ctx = {"lead_id": "1", "tenant_id": "t", pkey: {"to": "b"}}
    steps = graph_walk_steps(doc, ctx, blueprint_id=1, tenant_id="t")
    assert [s["node_id"] for s in steps] == ["b"]


def test_document_to_acoes_divisao_metadata_out():
    doc = _doc_divisao_ab()
    div_out = {}
    acoes = document_to_acoes(
        doc,
        context={"lead_id": "7", "tenant_id": "z"},
        blueprint_id=3,
        tenant_id="z",
        divisao_metadata_out=div_out,
    )
    pkey = divisao_persist_key("d")
    assert pkey in div_out
    assert str(div_out[pkey].get("to") or "") in ("a", "b")
    texts = [a.conteudo for a in acoes if a.tipo == "text"]
    if div_out[pkey]["to"] == "a":
        assert any("TEXTO_A" in (t or "") for t in texts)
    else:
        assert any("TEXTO_B" in (t or "") for t in texts)
