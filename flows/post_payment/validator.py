"""
Validador específico de blueprints do tipo ``post_payment`` (ADR_006).

Estende :func:`flow_builder_runtime.validate_flow_document` adicionando
regras pra proteger o cliente de publicar um pós-pagamento quebrado:

* **Erro:** trigger precisa ter ``config.event = 'webhook.payment.approved'``
* **Erro:** precisa existir um nó de mensagem alcançável a partir do trigger
  com delay acumulado ≤ 60s (lead pagou e precisa de confirmação rápida)
* **Warning:** recomendado ter pelo menos 1 nó ``acao`` (pra audit/tag de
  conversão); ausência sugere que analytics vai perder atribuição

Uso típico::

    from flows.post_payment.validator import validate_post_payment_blueprint

    res = validate_post_payment_blueprint(blueprint_doc)
    if not res["ok"]:
        # rejeitar publish, devolver res["errors"] pro frontend

A função preserva o formato de retorno de ``validate_flow_document`` —
mesmas chaves ``ok``/``errors``/``warnings``/``normalized``. Erros e
warnings específicos de post_payment ficam acumulados nas listas existentes
e também isolados em ``post_payment_issues``.
"""

from __future__ import annotations

from heapq import heappop, heappush
from typing import Any, Dict, List, Mapping, Optional

from flow_builder_runtime import ValidationIssue, validate_flow_document

POST_PAYMENT_TRIGGER_EVENT = "webhook.payment.approved"
CONFIRMATION_MAX_DELAY_SECONDS = 60.0

# Conversor de unidades aceitas no campo `delay_unit` do nó delay.
_DELAY_UNIT_TO_SECONDS: Dict[str, float] = {
    "s": 1, "seg": 1, "segundos": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "minuto": 60, "minutos": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hora": 3600, "horas": 3600, "hour": 3600, "hours": 3600,
    "d": 86400, "dia": 86400, "dias": 86400, "day": 86400, "days": 86400,
}


def validate_post_payment_blueprint(doc: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Valida blueprint do tipo post_payment.

    Roda :func:`validate_flow_document` primeiro (validação base). Depois adiciona:

    1. **Trigger event correto** (erro)
    2. **Mensagem alcançável em ≤60s** (erro)
    3. **Nó de ação pra tag de conversão** (warning)

    Returns:
        Dict com mesma estrutura de ``validate_flow_document``, plus
        ``post_payment_issues`` (lista isolada das regras desta camada).
        ``ok=False`` se qualquer erro (base ou post_payment) está presente.
    """
    base = validate_flow_document(doc)
    pp_issues: List[ValidationIssue] = []

    nodes = (base.get("normalized") or {}).get("graph", {}).get("nodes") or []
    edges = (base.get("normalized") or {}).get("graph", {}).get("edges") or []

    trigger_node = _find_trigger_node(nodes)

    # ── Regra 1: trigger event ──────────────────────────────────────────
    if not trigger_node:
        pp_issues.append(ValidationIssue(
            "error",
            "pp_no_trigger",
            "Blueprint post_payment exige um nó trigger.",
        ))
    else:
        event = (trigger_node.get("config") or {}).get("event") or ""
        if event != POST_PAYMENT_TRIGGER_EVENT:
            pp_issues.append(ValidationIssue(
                "error",
                "pp_invalid_trigger_event",
                f"Trigger.config.event deve ser '{POST_PAYMENT_TRIGGER_EVENT}'; "
                f"encontrado: '{event or '(vazio)'}'.",
            ))

    # ── Regra 2: mensagem ≤ 60s do trigger ──────────────────────────────
    if trigger_node:
        delay_to_msg = _shortest_delay_to_message(trigger_node["id"], nodes, edges)
        if delay_to_msg is None:
            pp_issues.append(ValidationIssue(
                "error",
                "pp_no_confirmation_message",
                "Não há nó de mensagem (conteudo/pergunta) alcançável a partir "
                "do trigger; lead pagou mas não vai receber confirmação.",
            ))
        elif delay_to_msg > CONFIRMATION_MAX_DELAY_SECONDS:
            pp_issues.append(ValidationIssue(
                "error",
                "pp_late_confirmation",
                f"Primeira mensagem está a {int(delay_to_msg)}s do trigger; "
                f"máximo permitido é {int(CONFIRMATION_MAX_DELAY_SECONDS)}s "
                "(cliente paga e fica ansioso esperando confirmação).",
            ))

    # ── Regra 3: tag de conversão (warning) ─────────────────────────────
    if not _has_acao_node(nodes):
        pp_issues.append(ValidationIssue(
            "warning",
            "pp_no_conversion_tag",
            "Recomendado: adicione um nó 'ação' que marque tag de conversão "
            "(ex: 'convertido_express') pra preservar audit e analytics.",
        ))

    # ── Combina com base ────────────────────────────────────────────────
    pp_errors = [i for i in pp_issues if i.level == "error"]
    pp_warnings = [i for i in pp_issues if i.level == "warning"]

    base_errors = list(base.get("errors") or [])
    base_warnings = list(base.get("warnings") or [])

    return {
        **base,
        "ok": base.get("ok", False) and len(pp_errors) == 0,
        "errors": base_errors + [i.to_dict() for i in pp_errors],
        "warnings": base_warnings + [i.to_dict() for i in pp_warnings],
        "post_payment_issues": [i.to_dict() for i in pp_issues],
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _find_trigger_node(nodes: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Retorna o primeiro nó de tipo trigger/webhook, ou None."""
    for n in nodes:
        if (n.get("type") or "").lower() in ("trigger", "webhook"):
            return n
    return None


def _has_acao_node(nodes: List[Dict[str, Any]]) -> bool:
    """True se há ao menos 1 nó de tipo 'acao' (pra tag/audit de conversão)."""
    return any((n.get("type") or "").lower() == "acao" for n in nodes)


def _delay_node_seconds(node: Dict[str, Any]) -> float:
    """
    Converte config de nó delay em segundos. Aceita 3 formatos:

    * ``seconds`` (legado): valor em segundos direto
    * ``delay_amount`` + ``delay_unit``: amount × unidade (s/m/h/d)
    * ``delay_smart_min``: usado como lower bound conservador
    """
    cfg = node.get("config") or {}

    if "delay_amount" in cfg or "delay_unit" in cfg:
        try:
            amount = float(cfg.get("delay_amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        unit = str(cfg.get("delay_unit") or "s").lower().strip()
        return amount * _DELAY_UNIT_TO_SECONDS.get(unit, 1)

    if "delay_smart_min" in cfg:
        try:
            return float(cfg.get("delay_smart_min") or 0)
        except (TypeError, ValueError):
            return 0.0

    try:
        return float(cfg.get("seconds") or 0)
    except (TypeError, ValueError):
        return 0.0


def _shortest_delay_to_message(
    start_id: str,
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Optional[float]:
    """
    Caminho mais curto (em segundos de delay acumulado) do trigger até a
    primeira mensagem (nó tipo conteudo/pergunta).

    Returns:
        float com segundos acumulados até a primeira mensagem, ou None se
        nenhuma mensagem é alcançável do trigger.

    Algoritmo: Dijkstra em grafo dirigido com peso = segundos de delay nos
    nós (mensagens têm peso 0, delay tem peso configurado).
    """
    if not start_id:
        return None

    nodes_by_id: Dict[str, Dict[str, Any]] = {n["id"]: n for n in nodes if n.get("id")}
    if start_id not in nodes_by_id:
        return None

    adjacency: Dict[str, List[str]] = {}
    for e in edges:
        src = e.get("from")
        dst = e.get("to")
        if src and dst:
            adjacency.setdefault(src, []).append(dst)

    # min-heap de (delay_acumulado_até_node, node_id)
    heap: List[tuple] = [(0.0, start_id)]
    best: Dict[str, float] = {start_id: 0.0}

    while heap:
        delay_acc, node_id = heappop(heap)
        if delay_acc > best.get(node_id, float("inf")):
            continue

        node = nodes_by_id.get(node_id)
        if not node:
            continue

        ntype = (node.get("type") or "").lower()
        if ntype in ("conteudo", "pergunta") and node_id != start_id:
            return delay_acc

        # Custo de "passar por" este nó é o delay dele (apenas delay nodes acumulam)
        passing_cost = _delay_node_seconds(node) if ntype == "delay" else 0.0

        for next_id in adjacency.get(node_id, []):
            new_delay = delay_acc + passing_cost
            if new_delay < best.get(next_id, float("inf")):
                best[next_id] = new_delay
                heappush(heap, (new_delay, next_id))

    return None
