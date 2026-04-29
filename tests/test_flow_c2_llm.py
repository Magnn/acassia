"""C2: blocos GPT/Agente com Gemini em steps_to_acoes quando permitido."""

from flow_executor import document_to_acoes, flow_gemini_generate_text, steps_to_acoes


def test_flow_gemini_generate_text_requires_key():
    text, err = flow_gemini_generate_text("hi", model="gemini-2.5-flash", temperature=0.5, api_key=None)
    assert text == ""
    assert err


def test_steps_llm_placeholder_when_flag_off(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_LLM", False)
    steps = [
        {
            "order": 1,
            "node_id": "g1",
            "type": "gpt",
            "config": {"prompt": "Hello"},
        },
    ]
    acoes = steps_to_acoes(steps)
    assert len(acoes) == 1
    assert (acoes[0].metadata or {}).get("runtime") == "llm"
    assert "Hello" in (acoes[0].conteudo or "")


def test_steps_llm_resolved_via_gemini(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_LLM", True)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class Resp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "Resposta do modelo"}],
                        },
                    },
                ],
            }

    monkeypatch.setattr("flow_executor.requests.post", lambda *a, **kw: Resp())

    steps = [
        {
            "order": 1,
            "node_id": "g1",
            "type": "gpt",
            "config": {"prompt": "Ping", "model": "gemini-2.5-flash"},
        },
    ]
    acoes = steps_to_acoes(steps)
    assert len(acoes) == 1
    m = acoes[0].metadata or {}
    assert m.get("runtime") == "llm_gemini"
    assert "Resposta do modelo" in (acoes[0].conteudo or "")


def test_document_to_acoes_gpt_branch(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_LLM", True)
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    class Resp:
        status_code = 200

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "OK"}]}}]}

    monkeypatch.setattr("flow_executor.requests.post", lambda *a, **kw: Resp())

    doc = {
        "format": "acassia-flow",
        "version": 1,
        "title": "L",
        "graph": {
            "nodes": [
                {"id": "t", "type": "trigger", "config": {}},
                {"id": "g", "type": "gpt", "config": {"prompt": "X"}},
            ],
            "edges": [{"from": "t", "to": "g"}],
        },
    }
    acoes = document_to_acoes(doc, context={})
    assert any((a.metadata or {}).get("runtime") == "llm_gemini" for a in acoes if a.tipo == "text")


def test_llm_api_error_fallback(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_LLM", True)
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    class Resp:
        status_code = 200

        def json(self):
            return {"candidates": []}

    monkeypatch.setattr("flow_executor.requests.post", lambda *a, **kw: Resp())

    steps = [
        {"order": 1, "node_id": "g1", "type": "gpt", "config": {"prompt": "P"}},
    ]
    acoes = steps_to_acoes(steps)
    assert len(acoes) == 1
    assert (acoes[0].metadata or {}).get("runtime") == "llm_gemini"
    assert "Desculpe" in (acoes[0].conteudo or "")
