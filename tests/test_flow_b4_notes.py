"""B4: anotações do canvas não são enviadas ao WhatsApp."""

from flow_executor import document_to_acoes, steps_to_acoes


def test_anotacao_action_has_note_metadata():
    steps = [
        {
            "order": 1,
            "node_id": "n1",
            "type": "anotacao",
            "config": {"note": "Só para operação"},
        },
    ]
    acoes = steps_to_acoes(steps)
    assert len(acoes) == 1
    a = acoes[0]
    assert a.tipo == "text"
    assert "operação" in (a.conteudo or "")
    m = a.metadata or {}
    assert m.get("kind") == "note"
    assert m.get("runtime") == "note_internal"
    assert m.get("source") == "flow_builder"


def test_document_linear_with_anotacao():
    doc = {
        "format": "meumisterio-flow",
        "version": 1,
        "title": "Notes",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {"id": "x", "type": "anotacao", "config": {"note": "Interno"}},
                {"id": "y", "type": "conteudo", "config": {"body": "Olá lead"}},
            ],
            "edges": [
                {"from": "t", "to": "x"},
                {"from": "x", "to": "y"},
            ],
        },
    }
    acoes = document_to_acoes(doc)
    kinds = [(a.metadata or {}).get("kind") for a in acoes if a.tipo == "text"]
    assert "note" in kinds
    assert any("Olá lead" in (a.conteudo or "") for a in acoes if a.tipo == "text")
