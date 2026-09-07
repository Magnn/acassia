"""Execução conversacional, com estado, de um blueprint publicado.

O executor legado transforma um DAG inteiro em uma lista de ações. Este módulo
executa somente o caminho escolhido e pausa em blocos que dependem da próxima
mensagem do contato (pergunta e menu).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flow_executor import apply_flow_template, steps_to_acoes
from flow_graph_walk import evaluate_condicao_rules, stable_weighted_index
from schema import Acao


RUNTIME_STATE_KEY = "flow_builder_runtime"
_MAX_TURN_STEPS = 200


@dataclass
class PublishedFlowTurn:
    handled: bool
    actions: List[Acao] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    side_effects: List[Dict[str, Any]] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _parse_datetime(raw: Any) -> Optional[datetime]:
    try:
        value = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _graph(doc: Mapping[str, Any]) -> tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    graph = doc.get("graph") if isinstance(doc.get("graph"), dict) else {}
    nodes_raw = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    edges_raw = graph.get("edges") if isinstance(graph.get("edges"), list) else []

    nodes: Dict[str, Dict[str, Any]] = {}
    for raw in nodes_raw:
        if not isinstance(raw, dict):
            continue
        node_id = str(raw.get("id") or "").strip()
        if not node_id:
            continue
        nodes[node_id] = {
            "id": node_id,
            "type": str(raw.get("type") or "generic").strip().lower(),
            "label": str(raw.get("label") or ""),
            "config": dict(raw.get("config") or {}) if isinstance(raw.get("config"), dict) else {},
        }

    outgoing: Dict[str, List[Dict[str, Any]]] = {node_id: [] for node_id in nodes}
    for raw in edges_raw:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("from") or "").strip()
        target = str(raw.get("to") or "").strip()
        if source not in nodes or target not in nodes:
            continue
        outgoing[source].append(
            {
                "from": source,
                "to": target,
                "sourceHandle": str(raw.get("sourceHandle") or "").strip(),
                "targetHandle": str(raw.get("targetHandle") or "").strip(),
                "label": str(raw.get("label") or "").strip(),
            }
        )
    return nodes, outgoing


def _edge_target(
    edges: List[Dict[str, Any]],
    *handles: str,
    fallback_index: int = 0,
) -> Optional[str]:
    wanted = {_norm(handle) for handle in handles if handle}
    if wanted:
        for edge in edges:
            if _norm(edge.get("sourceHandle")) in wanted or _norm(edge.get("label")) in wanted:
                return str(edge.get("to") or "").strip() or None
    if not edges:
        return None
    index = min(max(0, fallback_index), len(edges) - 1)
    return str(edges[index].get("to") or "").strip() or None


def _trigger_matches(
    node: Mapping[str, Any],
    message: str,
    *,
    event_type: str,
    context: Mapping[str, Any],
) -> bool:
    cfg = node.get("config") if isinstance(node.get("config"), dict) else {}
    integration = _norm(cfg.get("integration") or "whatsapp")
    event = _norm(cfg.get("event") or "keyword").replace("-", "_").replace(" ", "_")
    incoming_event = _norm(event_type or "message").replace("-", "_").replace(" ", "_")
    event_aliases = {
        "purchase": {"purchase", "purchase_approved", "paid", "approved", "completed"},
        "purchase_approved": {"purchase", "purchase_approved", "paid", "approved", "completed"},
        "abandon": {"abandon", "abandoned", "cart_abandoned", "checkout_abandoned"},
        "cart_abandoned": {"abandon", "abandoned", "cart_abandoned", "checkout_abandoned"},
    }
    if incoming_event not in ("message", "message_received", "mensagem"):
        accepted = event_aliases.get(event, {event})
        if incoming_event not in accepted:
            return False
        event_platform = _norm(context.get("event.platform") or context.get("platform"))
        return integration in ("", "whatsapp") or not event_platform or integration == event_platform
    if integration not in ("", "whatsapp", "whatsapp oficial", "whatsapp_official", "business"):
        return False
    if event in ("message", "message_received", "mensagem", "mensagem_recebida", "any_message"):
        return True
    if event in ("inicio_conversa", "conversation_started"):
        return not bool(context.get("flow.has_previous_state"))
    if event in ("keyword", "palavra_chave"):
        keyword = _norm(cfg.get("keyword"))
        return not keyword or _norm(message) == keyword
    return False


def _select_menu_option(cfg: Mapping[str, Any], message: str, reply_id: Optional[str]) -> Optional[int]:
    options = cfg.get("options") if isinstance(cfg.get("options"), list) else []
    rid = str(reply_id or "").strip().lower()
    match = re.fullmatch(r"opt[_:-]?(\d+)", rid)
    if match:
        index = int(match.group(1))
        return index if 0 <= index < len(options) else None
    text = _norm(message)
    if text.isdigit():
        index = int(text) - 1
        return index if 0 <= index < len(options) else None
    for index, option in enumerate(options):
        if text and text == _norm(option):
            return index
    return None


def _question_action(node: Mapping[str, Any], variables: Mapping[str, Any]) -> List[Acao]:
    cfg = node.get("config") if isinstance(node.get("config"), dict) else {}
    body = apply_flow_template(
        str(cfg.get("question") or cfg.get("body") or cfg.get("question_text") or ""),
        variables,
    )
    if not body.strip():
        return []
    metadata: Dict[str, Any] = {
        "source": "flow_builder",
        "node_type": "pergunta",
        "node_id": node.get("id"),
    }
    replies = cfg.get("quick_replies")
    if isinstance(replies, list) and replies:
        metadata["quick_replies"] = [str(item) for item in replies if str(item).strip()]
    return [Acao(tipo="text", conteudo=body[:4000], metadata=metadata)]


def _menu_action(node: Mapping[str, Any], variables: Mapping[str, Any]) -> List[Acao]:
    cfg = node.get("config") if isinstance(node.get("config"), dict) else {}
    options = [str(item).strip() for item in (cfg.get("options") or []) if str(item).strip()]
    body = apply_flow_template(str(cfg.get("message") or cfg.get("body") or "Selecione uma opção:"), variables)
    numbered = "\n".join(f"{index + 1}. {option}" for index, option in enumerate(options))
    content = f"{body.rstrip()}\n{numbered}" if numbered else body
    if not content.strip():
        return []
    return [
        Acao(
            tipo="text",
            conteudo=content[:4000],
            metadata={
                "source": "flow_builder",
                "node_type": "menu",
                "node_id": node.get("id"),
                "quick_replies": options,
            },
        )
    ]


def _is_in_business_hours(cfg: Mapping[str, Any], now: datetime) -> bool:
    timezone_name = str(cfg.get("timezone") or "America/Sao_Paulo").strip()
    try:
        local = now.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        local = now.astimezone(timezone.utc)
    days = cfg.get("days") if isinstance(cfg.get("days"), list) else []
    if len(days) != 7:
        return False
    day_index = (local.weekday() + 1) % 7  # UI: domingo=0; Python: segunda=0
    day = days[day_index] if isinstance(days[day_index], dict) else {}
    if not day.get("active"):
        return False
    current_minutes = local.hour * 60 + local.minute
    intervals = day.get("intervals") if isinstance(day.get("intervals"), list) else []
    for interval in intervals:
        if not isinstance(interval, dict):
            continue
        try:
            start_h, start_m = [int(part) for part in str(interval.get("start") or "00:00").split(":", 1)]
            end_h, end_m = [int(part) for part in str(interval.get("end") or "23:59").split(":", 1)]
        except (TypeError, ValueError):
            continue
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if (start <= end and start <= current_minutes <= end) or (
            start > end and (current_minutes >= start or current_minutes <= end)
        ):
            return True
    return False


def _split_choice(
    node_id: str,
    cfg: Mapping[str, Any],
    edges: List[Dict[str, Any]],
    *,
    tenant_id: str,
    lead_id: int,
    blueprint_id: int,
) -> tuple[Optional[str], str, List[float]]:
    raw_weights = cfg.get("weights")
    if isinstance(raw_weights, list):
        weights = []
        for raw in raw_weights[: len(edges)]:
            try:
                weights.append(max(0.0, float(raw)))
            except (TypeError, ValueError):
                weights.append(0.0)
    else:
        try:
            weight_a = max(0.0, min(100.0, float(cfg.get("weight_a") or 50)))
        except (TypeError, ValueError):
            weight_a = 50.0
        weights = [weight_a, 100.0 - weight_a]
    if len(weights) < len(edges):
        weights.extend([1.0] * (len(edges) - len(weights)))
    weights = weights[: len(edges)] or [1.0]
    index = stable_weighted_index(
        weights,
        (tenant_id, str(lead_id), node_id, str(blueprint_id)),
    )
    variant = chr(ord("A") + index)
    target = _edge_target(edges, variant, variant.lower(), f"t{index + 1}", fallback_index=index)
    return target, variant, weights


def _node_failed(node_type: str, node_id: str, actions: List[Acao], variables: Mapping[str, Any]) -> bool:
    for action in actions:
        metadata = getattr(action, "metadata", None) or {}
        if metadata.get("error") or metadata.get("llm_error") or str(metadata.get("runtime") or "").endswith("_error"):
            return True
    if node_type in ("api", "integration"):
        safe_node_id = re.sub(r"[^\w\-.]+", "_", node_id)
        result = variables.get(f"flow_http__{safe_node_id}")
        if not isinstance(result, dict):
            return True
        try:
            return int(result.get("status") or 0) >= 400
        except (TypeError, ValueError):
            return True
    if node_type in ("gpt", "agente_ia"):
        safe_node_id = re.sub(r"[^\w\-.]+", "_", node_id)
        result = variables.get(f"flow_llm__{safe_node_id}")
        if isinstance(result, dict):
            try:
                return int(result.get("status") or 0) >= 400
            except (TypeError, ValueError):
                return True
        return not actions
    return False


def _action_effects(cfg: Mapping[str, Any], variables: Mapping[str, Any]) -> List[Dict[str, Any]]:
    raw_actions = cfg.get("actions")
    if not isinstance(raw_actions, list):
        raw_actions = cfg.get("acao_stack")
    if not isinstance(raw_actions, list):
        raw_actions = [cfg] if cfg.get("action_kind") else []
    effects: List[Dict[str, Any]] = []
    for raw in raw_actions:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("action_kind") or "").strip()
        if not kind:
            continue
        raw_payload = str(raw.get("payload") or "")
        source_type = str(raw.get("source_type") or "").strip().lower()
        if source_type == "webhook" and "{{" not in raw_payload:
            resolved = variables.get(raw_payload)
            if resolved is None and raw_payload.startswith("event."):
                event_payload = variables.get("event")
                if isinstance(event_payload, Mapping):
                    resolved = event_payload.get(raw_payload.removeprefix("event."))
            payload = "" if resolved is None else str(resolved)
        else:
            payload = apply_flow_template(raw_payload, variables)
        effect = {"kind": kind, "payload": payload}
        for key in ("target_field", "source_type"):
            if raw.get(key) is not None:
                effect[key] = str(raw.get(key) or "")
        effects.append(effect)
    return effects


def execute_published_flow_turn(
    doc: Mapping[str, Any],
    *,
    blueprint_id: int,
    tenant_id: str,
    lead_id: int,
    message: str,
    interactive_reply_id: Optional[str] = None,
    event_type: str = "message",
    existing_state: Optional[Mapping[str, Any]] = None,
    context: Optional[Mapping[str, Any]] = None,
    now: Optional[datetime] = None,
) -> PublishedFlowTurn:
    """Executa um turno. ``handled=False`` libera o motor legado."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    current_time = current_time.astimezone(timezone.utc)
    nodes, outgoing = _graph(doc)
    if not nodes:
        return PublishedFlowTurn(handled=False)

    old = dict(existing_state or {})
    is_message_event = _norm(event_type) in ("", "message", "message_received", "mensagem")
    active = is_message_event and (
        int(old.get("blueprint_id") or 0) == int(blueprint_id)
        and str(old.get("status") or "") in ("running", "waiting")
    )
    persisted_vars = dict(old.get("vars") or {}) if active and isinstance(old.get("vars"), dict) else {}
    variables: Dict[str, Any] = dict(context or {})
    variables.update(persisted_vars)
    variables["chat.message"] = message
    variables["texto_recebido"] = message
    variables["lead_id"] = str(lead_id)
    variables["tenant_id"] = tenant_id
    variables["blueprint_id"] = blueprint_id
    variables["flow.has_previous_state"] = bool(existing_state)
    weekday_names = (
        "Segunda-Feira",
        "Terça-Feira",
        "Quarta-Feira",
        "Quinta-Feira",
        "Sexta-Feira",
        "Sábado",
        "Domingo",
    )
    try:
        condition_time = current_time.astimezone(
            ZoneInfo(str(variables.get("timezone") or "America/Sao_Paulo"))
        )
    except ZoneInfoNotFoundError:
        condition_time = current_time
    variables["dia_semana"] = weekday_names[condition_time.weekday()]
    variables["horario"] = condition_time.strftime("%H:%M")

    state: Dict[str, Any] = {
        "version": 1,
        "blueprint_id": int(blueprint_id),
        "status": "running",
        "current_node_id": None,
        "waiting": None,
        "vars": persisted_vars,
        "updated_at": _iso(current_time),
    }

    if active and isinstance(old.get("waiting"), dict):
        waiting = dict(old["waiting"])
        node_id = str(waiting.get("node_id") or "")
        node = nodes.get(node_id)
        if node and node["type"] == "pergunta":
            expired_at = _parse_datetime(waiting.get("expires_at"))
            timed_out = bool(expired_at and current_time >= expired_at)
            if not timed_out:
                save_as = str(node["config"].get("save_to_flow_field") or node["config"].get("output_var") or "").strip()
                if save_as:
                    persisted_vars[save_as] = message
                    variables[save_as] = message
            current_node = _edge_target(
                outgoing.get(node_id, []),
                "timeout" if timed_out else "resposta",
                "error" if timed_out else "response",
                fallback_index=1 if timed_out else 0,
            )
        elif node and node["type"] == "menu":
            choice = _select_menu_option(node["config"], message, interactive_reply_id)
            if choice is None:
                state.update(old)
                state["updated_at"] = _iso(current_time)
                state["vars"] = persisted_vars
                return PublishedFlowTurn(
                    handled=True,
                    actions=_menu_action(node, variables),
                    state=state,
                    trace=[{"node_id": node_id, "event": "menu_invalid_option"}],
                )
            options = node["config"].get("options") or []
            selected = str(options[choice])
            save_as = str(node["config"].get("save_to_flow_field") or node["config"].get("output_var") or "").strip()
            if save_as:
                persisted_vars[save_as] = selected
                variables[save_as] = selected
            current_node = _edge_target(outgoing.get(node_id, []), f"opt_{choice}", fallback_index=choice)
        elif node and node["type"] == "agente_ia":
            current_node = node_id
        else:
            current_node = None
    elif active:
        current_node = str(old.get("current_node_id") or "").strip() or None
    else:
        trigger = next(
            (
                node
                for node in nodes.values()
                if node["type"] in ("trigger", "webhook")
                and _trigger_matches(node, message, event_type=event_type, context=variables)
            ),
            None,
        )
        if trigger is None:
            return PublishedFlowTurn(handled=False)
        current_node = trigger["id"]

    actions: List[Acao] = []
    side_effects: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []
    force_complete = False

    for _ in range(_MAX_TURN_STEPS):
        if not current_node or current_node not in nodes:
            state["status"] = "completed"
            state["current_node_id"] = None
            break
        node = nodes[current_node]
        node_id = node["id"]
        node_type = node["type"]
        cfg = node["config"]
        edges = outgoing.get(node_id, [])
        state["current_node_id"] = node_id
        trace.append({"node_id": node_id, "type": node_type})

        if node_type == "end":
            state["status"] = "completed"
            state["current_node_id"] = node_id
            break
        if node_type in ("trigger", "webhook", "generic"):
            current_node = _edge_target(edges)
            continue
        if node_type == "condicao":
            passed, _, _ = evaluate_condicao_rules(cfg, variables)
            current_node = _edge_target(
                edges,
                "true" if passed else "false",
                "sim" if passed else "nao",
                fallback_index=0 if passed else 1,
            )
            trace[-1]["branch"] = passed
            continue
        if node_type in ("ab_split", "divisao"):
            current_node, variant, split_weights = _split_choice(
                node_id,
                cfg,
                edges,
                tenant_id=tenant_id,
                lead_id=lead_id,
                blueprint_id=blueprint_id,
            )
            persisted_vars["ab_variant"] = variant
            persisted_vars[f"ab_{node_id}_variant"] = variant
            variables.update(persisted_vars)
            total_weight = sum(split_weights) or 1.0
            side_effects.append(
                {
                    "kind": "ab_exposure",
                    "blueprint_id": blueprint_id,
                    "node_id": node_id,
                    "variant": variant,
                    "weight_a": round((split_weights[0] if split_weights else 0.0) * 100 / total_weight),
                    "weight_b": round((split_weights[1] if len(split_weights) > 1 else 0.0) * 100 / total_weight),
                }
            )
            trace[-1]["variant"] = variant
            continue
        if node_type == "expediente":
            in_hours = _is_in_business_hours(cfg, current_time)
            current_node = _edge_target(
                edges,
                "sucesso" if in_hours else "erro",
                "success" if in_hours else "error",
                fallback_index=0 if in_hours else 1,
            )
            trace[-1]["in_business_hours"] = in_hours
            continue
        if node_type == "pergunta":
            actions.extend(_question_action(node, variables))
            try:
                timeout_seconds = max(1, min(2_592_000, int(cfg.get("question_timeout_seconds") or 3600)))
            except (TypeError, ValueError):
                timeout_seconds = 3600
            state["status"] = "waiting"
            state["waiting"] = {
                "node_id": node_id,
                "type": "pergunta",
                "expires_at": _iso(current_time + timedelta(seconds=timeout_seconds)),
            }
            break
        if node_type == "menu":
            actions.extend(_menu_action(node, variables))
            state["status"] = "waiting"
            state["waiting"] = {"node_id": node_id, "type": "menu", "expires_at": None}
            break
        if node_type == "acao":
            effects = _action_effects(cfg, variables)
            side_effects.extend(effects)
            force_complete = any(effect.get("kind") == "end_flow" for effect in effects)
            if force_complete:
                state["status"] = "completed"
                break
            current_node = _edge_target(edges)
            continue
        if node_type in ("notificar", "notificar_atendente"):
            side_effects.append(
                {
                    "kind": "notify_attendant",
                    "payload": apply_flow_template(str(cfg.get("message") or "Contato solicitou atendimento."), variables),
                    "attendant_id": str(cfg.get("atendente_id") or ""),
                }
            )
            current_node = _edge_target(edges)
            continue

        before = len(actions)
        produced = steps_to_acoes(
            [{"node_id": node_id, "type": node_type, "config": cfg}],
            flow_vars=variables,
            flow_vars_metadata_out=persisted_vars,
            blueprint_id=blueprint_id,
            tenant_id=tenant_id,
        )
        actions.extend(produced)
        variables.update(persisted_vars)
        failed = _node_failed(node_type, node_id, actions[before:], variables)
        if (
            node_type == "agente_ia"
            and not failed
            and str(cfg.get("control_mode") or "until_converted") == "until_converted"
            and str(variables.get("convertido") or "").strip().lower() not in ("1", "true", "yes", "sim")
        ):
            state["status"] = "waiting"
            state["waiting"] = {"node_id": node_id, "type": "agente_ia", "expires_at": None}
            trace[-1]["control"] = "until_converted"
            break
        current_node = _edge_target(
            edges,
            "erro" if failed else "sucesso",
            "error" if failed else "success",
            "avancar" if not failed else "",
            fallback_index=1 if failed else 0,
        )
        trace[-1]["failed"] = failed
    else:
        state["status"] = "failed"
        state["error"] = "limite de passos por turno excedido"

    if force_complete:
        state["waiting"] = None
    state["vars"] = persisted_vars
    state["updated_at"] = _iso(current_time)
    return PublishedFlowTurn(
        handled=True,
        actions=actions,
        state=state,
        side_effects=side_effects,
        trace=trace,
    )
