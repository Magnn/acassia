from datetime import datetime, timezone

from flow_builder_runtime import validate_flow_document
from published_flow_runtime import execute_published_flow_turn


def _doc(nodes, edges):
    return {
        "format": "meumisterio-flow",
        "version": 1,
        "title": "Publicado",
        "graph": {"nodes": nodes, "edges": edges},
    }


def _turn(doc, message, state=None, **kwargs):
    return execute_published_flow_turn(
        doc,
        blueprint_id=11,
        tenant_id="tenant-test",
        lead_id=22,
        message=message,
        existing_state=state,
        context=kwargs.pop("context", {}),
        **kwargs,
    )


def test_question_pauses_and_only_resumes_response_branch():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {"event": "keyword", "keyword": "oi"}},
            {
                "id": "q",
                "type": "pergunta",
                "config": {"question": "Qual seu nome?", "save_to_flow_field": "nome"},
            },
            {"id": "yes", "type": "conteudo", "config": {"body": "Prazer, {{nome}}"}},
            {"id": "late", "type": "conteudo", "config": {"body": "Expirou"}},
            {"id": "end", "type": "end", "config": {}},
        ],
        [
            {"from": "t", "to": "q"},
            {"from": "q", "to": "yes", "sourceHandle": "resposta"},
            {"from": "q", "to": "late", "sourceHandle": "timeout"},
            {"from": "yes", "to": "end"},
            {"from": "late", "to": "end"},
        ],
    )
    first = _turn(doc, "oi")
    assert first.state["status"] == "waiting"
    assert [action.conteudo for action in first.actions] == ["Qual seu nome?"]

    second = _turn(doc, "Ana", first.state)
    assert second.state["status"] == "completed"
    assert second.state["vars"]["nome"] == "Ana"
    assert [action.conteudo for action in second.actions] == ["Prazer, Ana"]


def test_question_timeout_does_not_run_response_branch():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {"id": "q", "type": "pergunta", "config": {"question": "Responda", "question_timeout_seconds": 1}},
            {"id": "yes", "type": "conteudo", "config": {"body": "RESPOSTA"}},
            {"id": "late", "type": "conteudo", "config": {"body": "TIMEOUT"}},
        ],
        [
            {"from": "t", "to": "q"},
            {"from": "q", "to": "yes", "sourceHandle": "resposta"},
            {"from": "q", "to": "late", "sourceHandle": "timeout"},
        ],
    )
    first = _turn(doc, "início", now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    second = _turn(doc, "atrasada", first.state, now=datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc))
    assert [action.conteudo for action in second.actions] == ["TIMEOUT"]


def test_menu_accepts_number_and_routes_by_source_handle():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {
                "id": "m",
                "type": "menu",
                "config": {"message": "Escolha:", "options": ["Vendas", "Suporte"], "save_to_flow_field": "setor"},
            },
            {"id": "sales", "type": "conteudo", "config": {"body": "VENDAS"}},
            {"id": "support", "type": "conteudo", "config": {"body": "SUPORTE {{setor}}"}},
        ],
        [
            {"from": "t", "to": "m"},
            {"from": "m", "to": "sales", "sourceHandle": "opt_0"},
            {"from": "m", "to": "support", "sourceHandle": "opt_1"},
        ],
    )
    first = _turn(doc, "qualquer")
    assert first.state["status"] == "waiting"
    assert first.actions[0].conteudo == "Escolha:\n1. Vendas\n2. Suporte"

    invalid = _turn(doc, "9", first.state)
    assert invalid.state["status"] == "waiting"
    assert invalid.trace[-1]["event"] == "menu_invalid_option"

    selected = _turn(doc, "2", invalid.state)
    assert selected.state["vars"]["setor"] == "Suporte"
    assert [action.conteudo for action in selected.actions] == ["SUPORTE Suporte"]


def test_frontend_condition_contract_uses_equals_value_and_handles():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {
                "id": "c",
                "type": "condicao",
                "config": {"rules": [{"var": "chat.message", "op": "equals", "value": "sim"}], "logic": "AND"},
            },
            {"id": "yes", "type": "conteudo", "config": {"body": "SIM"}},
            {"id": "no", "type": "conteudo", "config": {"body": "NAO"}},
        ],
        [
            {"from": "t", "to": "c"},
            {"from": "c", "to": "yes", "sourceHandle": "true"},
            {"from": "c", "to": "no", "sourceHandle": "false"},
        ],
    )
    assert [action.conteudo for action in _turn(doc, "SIM").actions] == ["SIM"]
    assert [action.conteudo for action in _turn(doc, "não").actions] == ["NAO"]


def test_ab_split_is_deterministic_and_follows_canvas_handles():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {"id": "ab", "type": "ab_split", "config": {"weights": [50, 50]}},
            {"id": "a", "type": "conteudo", "config": {"body": "A"}},
            {"id": "b", "type": "conteudo", "config": {"body": "B"}},
        ],
        [
            {"from": "t", "to": "ab"},
            {"from": "ab", "to": "a", "sourceHandle": "a"},
            {"from": "ab", "to": "b", "sourceHandle": "b"},
        ],
    )
    first = _turn(doc, "oi")
    second = _turn(doc, "oi")
    assert first.state["vars"]["ab_variant"] == second.state["vars"]["ab_variant"]
    assert [action.conteudo for action in first.actions] == [action.conteudo for action in second.actions]
    assert first.side_effects == [
        {
            "kind": "ab_exposure",
            "blueprint_id": 11,
            "node_id": "ab",
            "variant": first.state["vars"]["ab_variant"],
            "weight_a": 50,
            "weight_b": 50,
        }
    ]


def test_action_and_notification_return_real_side_effects():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {
                "id": "a",
                "type": "acao",
                "config": {
                    "actions": [
                        {"action_kind": "tag_add", "payload": "Interessado"},
                        {"action_kind": "update_contact", "target_field": "name", "payload": "{{novo_nome}}"},
                        {
                            "action_kind": "update_contact",
                            "target_field": "email",
                            "source_type": "webhook",
                            "payload": "event.email",
                        },
                    ]
                },
            },
            {"id": "n", "type": "notificar_atendente", "config": {"message": "Ajude {{novo_nome}}", "atendente_id": "7"}},
            {"id": "e", "type": "end", "config": {}},
        ],
        [{"from": "t", "to": "a"}, {"from": "a", "to": "n"}, {"from": "n", "to": "e"}],
    )
    result = _turn(doc, "oi", context={"novo_nome": "Bia", "event": {"email": "bia@example.com"}})
    assert result.side_effects == [
        {"kind": "tag_add", "payload": "Interessado"},
        {"kind": "update_contact", "payload": "Bia", "target_field": "name"},
        {
            "kind": "update_contact",
            "payload": "bia@example.com",
            "target_field": "email",
            "source_type": "webhook",
        },
        {"kind": "notify_attendant", "payload": "Ajude Bia", "attendant_id": "7"},
    ]


def test_strict_validation_preserves_handles_and_rejects_disconnected_block():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {"id": "c", "type": "condicao", "config": {"rules": [{"var": "x", "op": "equals", "value": "1"}]}},
            {"id": "yes", "type": "end", "config": {}},
            {"id": "no", "type": "end", "config": {}},
            {"id": "loose", "type": "conteudo", "config": {"body": "solto"}},
        ],
        [
            {"from": "t", "to": "c"},
            {"from": "c", "to": "yes", "sourceHandle": "true"},
            {"from": "c", "to": "no", "sourceHandle": "false"},
        ],
    )
    result = validate_flow_document(doc, strict=True)
    assert result["ok"] is False
    assert result["normalized"]["graph"]["edges"][1]["sourceHandle"] == "true"
    assert "nodes_disconnected_from_trigger" in {issue["code"] for issue in result["errors"]}


def test_purchase_event_starts_matching_checkout_trigger_only():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {"integration": "hotmart", "event": "purchase"}},
            {"id": "m", "type": "conteudo", "config": {"body": "Compra {{event.product}} aprovada"}},
        ],
        [{"from": "t", "to": "m"}],
    )
    matched = execute_published_flow_turn(
        doc,
        blueprint_id=11,
        tenant_id="tenant-test",
        lead_id=22,
        message="",
        event_type="purchase_approved",
        context={"event.platform": "hotmart", "event.product": "Oráculo"},
    )
    assert matched.handled is True
    assert [action.conteudo for action in matched.actions] == ["Compra Oráculo aprovada"]

    ignored = execute_published_flow_turn(
        doc,
        blueprint_id=11,
        tenant_id="tenant-test",
        lead_id=22,
        message="",
        event_type="cart_abandoned",
        context={"event.platform": "hotmart"},
    )
    assert ignored.handled is False


def test_api_disabled_routes_to_error_without_sending_technical_text(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_HTTP", False)
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {"id": "api", "type": "api", "config": {"url": "https://example.com"}},
            {"id": "ok", "type": "conteudo", "config": {"body": "OK"}},
            {"id": "error", "type": "conteudo", "config": {"body": "ERRO CONTROLADO"}},
        ],
        [
            {"from": "t", "to": "api"},
            {"from": "api", "to": "ok", "sourceHandle": "sucesso"},
            {"from": "api", "to": "error", "sourceHandle": "erro"},
        ],
    )
    result = _turn(doc, "oi")
    assert [action.conteudo for action in result.actions] == ["ERRO CONTROLADO"]
    assert result.state["vars"]["flow_http__api"]["status"] == 503


def test_business_hours_routes_success_and_error():
    days = [
        {"name": "Domingo", "active": False, "intervals": []},
        {"name": "Segunda-feira", "active": True, "intervals": [{"start": "09:00", "end": "18:00"}]},
        {"name": "Terça-feira", "active": False, "intervals": []},
        {"name": "Quarta-feira", "active": False, "intervals": []},
        {"name": "Quinta-feira", "active": False, "intervals": []},
        {"name": "Sexta-feira", "active": False, "intervals": []},
        {"name": "Sábado", "active": False, "intervals": []},
    ]
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {"id": "hours", "type": "expediente", "config": {"timezone": "America/Sao_Paulo", "days": days}},
            {"id": "open", "type": "conteudo", "config": {"body": "ABERTO"}},
            {"id": "closed", "type": "conteudo", "config": {"body": "FECHADO"}},
        ],
        [
            {"from": "t", "to": "hours"},
            {"from": "hours", "to": "open", "sourceHandle": "sucesso"},
            {"from": "hours", "to": "closed", "sourceHandle": "erro"},
        ],
    )
    monday_at_noon_sp = datetime(2026, 8, 17, 15, 0, tzinfo=timezone.utc)
    result = _turn(doc, "oi", now=monday_at_noon_sp)
    assert [action.conteudo for action in result.actions] == ["ABERTO"]


def test_agent_single_response_uses_current_message_and_advances(monkeypatch):
    monkeypatch.setattr("flow_executor._ALLOW_LLM", True)
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    captured = {}

    def fake_generate(prompt, **kwargs):
        captured["prompt"] = prompt
        return "Resposta da IA", None

    monkeypatch.setattr("flow_executor.flow_gemini_generate_text", fake_generate)
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {
                "id": "agent",
                "type": "agente_ia",
                "config": {"context_prompt": "Ajude com clareza", "control_mode": "single_response"},
            },
            {"id": "next", "type": "conteudo", "config": {"body": "AVANÇOU"}},
            {"id": "error", "type": "conteudo", "config": {"body": "ERRO"}},
        ],
        [
            {"from": "t", "to": "agent"},
            {"from": "agent", "to": "next", "sourceHandle": "avancar"},
            {"from": "agent", "to": "error", "sourceHandle": "erro"},
        ],
    )
    result = _turn(doc, "Preciso de ajuda")
    assert "Preciso de ajuda" in captured["prompt"]
    assert [action.conteudo for action in result.actions] == ["Resposta da IA", "AVANÇOU"]


def test_voice_block_carries_frontend_voice_controls_to_engine_action():
    doc = _doc(
        [
            {"id": "t", "type": "trigger", "config": {}},
            {
                "id": "voice",
                "type": "voice_studio",
                "config": {
                    "script": "Olá {{nome}}",
                    "voice_id": "Kore",
                    "style": 0.8,
                    "speed": 1.25,
                    "send_as_voice": "false",
                },
            },
            {"id": "done", "type": "end", "config": {}},
            {"id": "error", "type": "conteudo", "config": {"body": "ERRO"}},
        ],
        [
            {"from": "t", "to": "voice"},
            {"from": "voice", "to": "done", "sourceHandle": "sucesso"},
            {"from": "voice", "to": "error", "sourceHandle": "erro"},
        ],
    )

    result = _turn(doc, "oi", context={"nome": "Bia"})

    assert len(result.actions) == 1
    assert result.actions[0].tipo == "tts"
    assert result.actions[0].tts_template == "Olá Bia"
    assert result.actions[0].metadata["voice_profile"] == "Kore"
    assert result.actions[0].metadata["voice_style"] == 0.8
    assert result.actions[0].metadata["voice_speed"] == 1.25
    assert result.actions[0].metadata["whatsapp_voice"] is False
