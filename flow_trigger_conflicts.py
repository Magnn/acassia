"""Helpers for preventing published blueprints from sharing a start trigger."""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping, Optional


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _trigger_nodes(document: Mapping[str, Any]) -> list[Dict[str, Any]]:
    graph = document.get("graph") if isinstance(document.get("graph"), dict) else {}
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    return [
        node for node in nodes
        if isinstance(node, dict) and _norm(node.get("type")) in ("trigger", "webhook")
    ]


def _trigger_parts(node: Mapping[str, Any]) -> tuple[str, str, str]:
    config = node.get("config") if isinstance(node.get("config"), dict) else {}
    integration = _norm(config.get("integration") or "whatsapp").replace("_", " ")
    if "whatsapp" in integration or integration == "business":
        integration = "whatsapp"
    event = _norm(config.get("event") or "keyword").replace("-", "_").replace(" ", "_")
    aliases = {
        "message": "message_received",
        "mensagem": "message_received",
        "purchase_approved": "purchase",
        "paid": "purchase",
        "approved": "purchase",
        "completed": "purchase",
        "abandoned": "abandon",
        "cart_abandoned": "abandon",
        "checkout_abandoned": "abandon",
        "mensagem_recebida": "message_received",
        "any_message": "message_received",
        "conversation_started": "inicio_conversa",
    }
    event = aliases.get(event, event)
    keyword = _norm(config.get("keyword"))
    return integration, event, keyword


_WHATSAPP_INBOUND = {"whatsapp"}
_MESSAGE_EVENTS = {"message_received", "inicio_conversa", "keyword", "palavra_chave"}


def _same_trigger(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_integration, left_event, left_keyword = _trigger_parts(left)
    right_integration, right_event, right_keyword = _trigger_parts(right)
    is_whatsapp_message_trigger = (
        (left_integration in _WHATSAPP_INBOUND or right_integration in _WHATSAPP_INBOUND)
        and left_event in _MESSAGE_EVENTS
        and right_event in _MESSAGE_EVENTS
    )
    if is_whatsapp_message_trigger:
        if left_integration != right_integration:
            return False
        left_wildcard = left_event == "message_received" or (
            left_event in ("keyword", "palavra_chave") and not left_keyword
        )
        right_wildcard = right_event == "message_received" or (
            right_event in ("keyword", "palavra_chave") and not right_keyword
        )
        if left_wildcard or right_wildcard:
            return True
        if left_event == "inicio_conversa" or right_event == "inicio_conversa":
            return True
        return left_keyword == right_keyword and bool(left_keyword)

    same_non_keyword_event = (
        left_event == right_event
        and left_event not in ("keyword", "palavra_chave")
        and (
            left_integration == right_integration
            or left_integration in _WHATSAPP_INBOUND
            or right_integration in _WHATSAPP_INBOUND
        )
    )
    same_keyword_event = (
        left_integration == right_integration
        and left_event == right_event
        and left_event in ("keyword", "palavra_chave")
        and left_keyword == right_keyword
    )
    return same_non_keyword_event or same_keyword_event


def find_conflicting_trigger(
    candidate: Mapping[str, Any],
    published: Iterable[tuple[int, str, Mapping[str, Any]]],
) -> Optional[tuple[int, str]]:
    for candidate_node in _trigger_nodes(candidate):
        for blueprint_id, title, document in published:
            for published_node in _trigger_nodes(document):
                if _same_trigger(candidate_node, published_node):
                    return blueprint_id, title
    return None
