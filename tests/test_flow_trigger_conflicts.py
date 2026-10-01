from flow_trigger_conflicts import find_conflicting_trigger


def _doc(event, keyword="", integration="WhatsApp"):
    return {
        "graph": {
            "nodes": [
                {
                    "id": "trigger",
                    "type": "trigger",
                    "config": {"event": event, "keyword": keyword, "integration": integration},
                }
            ]
        }
    }


def test_same_keyword_conflicts_after_case_and_whitespace_normalization():
    conflict = find_conflicting_trigger(
        _doc("keyword", "  QUERO   COMPRAR "),
        [(7, "Compra", _doc("palavra_chave", "quero comprar"))],
    )
    assert conflict == (7, "Compra")


def test_different_keywords_can_be_published_for_one_number():
    conflict = find_conflicting_trigger(
        _doc("keyword", "quero comprar"),
        [(7, "Suporte", _doc("keyword", "preciso de ajuda"))],
    )
    assert conflict is None


def test_catch_all_message_trigger_conflicts_with_keyword_trigger():
    conflict = find_conflicting_trigger(
        _doc("message_received"),
        [(7, "Boas-vindas", _doc("keyword", "oi"))],
    )
    assert conflict == (7, "Boas-vindas")


def test_runtime_message_event_aliases_conflict_with_keyword_trigger():
    for event in ("message", "mensagem"):
        conflict = find_conflicting_trigger(
            _doc(event),
            [(7, "Boas-vindas", _doc("keyword", "oi"))],
        )
        assert conflict == (7, "Boas-vindas")


def test_purchase_event_aliases_conflict_for_the_same_integration():
    conflict = find_conflicting_trigger(
        _doc("purchase_approved", integration="Hotmart"),
        [(7, "Pós-venda", _doc("purchase", integration="Hotmart"))],
    )
    assert conflict == (7, "Pós-venda")


def test_same_event_on_different_integrations_does_not_conflict():
    conflict = find_conflicting_trigger(
        _doc("purchase", integration="Hotmart"),
        [(7, "Kiwify", _doc("purchase", integration="Kiwify"))],
    )
    assert conflict is None


def test_whatsapp_business_and_whatsapp_channel_share_the_same_inbound_scope():
    conflict = find_conflicting_trigger(
        _doc("keyword", "oi", integration="Business"),
        [(7, "Boas-vindas", _doc("keyword", "OI", integration="WhatsApp Oficial"))],
    )
    assert conflict == (7, "Boas-vindas")


def test_generic_whatsapp_purchase_trigger_conflicts_with_platform_purchase_trigger():
    conflict = find_conflicting_trigger(
        _doc("purchase", integration="WhatsApp"),
        [(7, "Hotmart", _doc("purchase_approved", integration="Hotmart"))],
    )
    assert conflict == (7, "Hotmart")
