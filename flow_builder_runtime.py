"""
Runtime avançado do Flow Builder AcassIA.

- Catálogo de blocos (schema por tipo)
- Validação estrutural + por config
- Compilação para plano linear (ordem de execução)
- Deteção de ciclos e nós inatingíveis
- Simulação dry-run (sem WhatsApp)
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Set, Tuple

# ── Tipos de nó suportados (alinhados ao dashboard) ─────────────────
ALLOWED_NODE_TYPES = frozenset(
    {
        "trigger",
        "webhook",
        "engine",
        "nucleo_ia",
        "motor_ref",
        "conteudo",
        "pergunta",
        "acao",
        "delay",
        "condicao",
        "expediente",
        "notificar",
        "divisao",
        "api",
        "gpt",
        "agente_ia",
        "voice_studio",
        "anotacao",
        "generic",
        "end",
    }
)

# Schema por tipo: campos obrigatórios em node["config"] (se existir config)
# runtime: categoria para simulação / futuro executor
NODE_SPECS: Dict[str, Dict[str, Any]] = {
    "trigger": {
        "label": "Gatilho",
        "runtime": "entry",
        "required_config": [],
        "optional_keys": ("event", "integration", "keyword"),
    },
    "webhook": {
        "label": "Webhook",
        "runtime": "entry",
        "required_config": [],
        "optional_keys": ("path",),
    },
    "engine": {
        "label": "Engine",
        "runtime": "system",
        "required_config": [],
        "optional_keys": (),
    },
    "nucleo_ia": {
        "label": "Núcleo IA",
        "runtime": "system",
        "required_config": [],
        "optional_keys": (),
    },
    "motor_ref": {
        "label": "Referência motor Python",
        "runtime": "system",
        "required_config": [],
        "optional_keys": ("module_hint",),
    },
    "conteudo": {
        "label": "Conteúdo",
        "runtime": "message",
        "required_config": (),
        "optional_keys": ("body", "media_type"),
    },
    "pergunta": {
        "label": "Pergunta",
        "runtime": "message",
        "required_config": (),
        "optional_keys": ("body", "question"),
    },
    "acao": {
        "label": "Ação",
        "runtime": "action",
        "required_config": (),
        "optional_keys": ("action_kind", "payload"),
    },
    "delay": {
        "label": "Delay",
        "runtime": "delay",
        "required_config": (),
        "optional_keys": ("seconds",),
    },
    "condicao": {
        "label": "Condição",
        "runtime": "branch",
        "required_config": (),
        "optional_keys": ("expression", "true_to", "false_to"),
    },
    "expediente": {
        "label": "Expediente",
        "runtime": "schedule",
        "required_config": (),
        "optional_keys": ("timezone", "windows"),
    },
    "notificar": {
        "label": "Notificar",
        "runtime": "notify",
        "required_config": (),
        "optional_keys": ("channel", "message"),
    },
    "divisao": {
        "label": "Divisão A/B",
        "runtime": "split",
        "required_config": (),
        "optional_keys": ("weights",),
    },
    "api": {
        "label": "API HTTP",
        "runtime": "http",
        "required_config": (),
        "optional_keys": ("url", "method", "headers", "body"),
    },
    "gpt": {
        "label": "GPT / LLM",
        "runtime": "llm",
        "required_config": (),
        "optional_keys": ("prompt", "model", "temperature"),
    },
    "agente_ia": {
        "label": "Agente IA",
        "runtime": "llm",
        "required_config": (),
        "optional_keys": ("instructions",),
    },
    "voice_studio": {
        "label": "Voice",
        "runtime": "tts",
        "required_config": (),
        "optional_keys": ("script",),
    },
    "anotacao": {
        "label": "Anotação",
        "runtime": "note",
        "required_config": (),
        "optional_keys": ("note",),
    },
    "end": {
        "label": "Fim",
        "runtime": "terminal",
        "required_config": [],
        "optional_keys": (),
    },
    "generic": {
        "label": "Genérico",
        "runtime": "passthrough",
        "required_config": (),
        "optional_keys": ("note",),
    },
}


@dataclass
class ValidationIssue:
    level: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"level": self.level, "code": self.code, "message": self.message}


def _safe_text(v: Any, max_len: int = 240) -> str:
    s = str(v or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def public_node_catalog() -> Dict[str, Any]:
    """Expõe metadados para o dashboard (tooltips, campos)."""
    out = {}
    for k, spec in NODE_SPECS.items():
        out[k] = {
            "label": spec.get("label", k),
            "runtime": spec.get("runtime", "passthrough"),
            "required_config": list(spec.get("required_config") or ()),
            "optional_keys": list(spec.get("optional_keys") or ()),
        }
    return {"node_types": out, "allowed": sorted(ALLOWED_NODE_TYPES)}


def _normalize_graph_payload(graph: Any) -> Dict[str, List[Dict[str, Any]]]:
    out_nodes: List[Dict[str, Any]] = []
    out_edges: List[Dict[str, Any]] = []
    if not isinstance(graph, Mapping):
        return {"nodes": out_nodes, "edges": out_edges}
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if isinstance(nodes, list):
        for n in nodes:
            if not isinstance(n, Mapping):
                continue
            cfg = n.get("config")
            if cfg is not None and not isinstance(cfg, dict):
                cfg = {}
            nid = _safe_text(n.get("id"), 120)
            ntype = _safe_text(n.get("type"), 64).lower()
            label = _safe_text(n.get("label"), 200)
            x = n.get("x")
            y = n.get("y")
            out_nodes.append(
                {
                    "id": nid,
                    "type": ntype,
                    "label": label,
                    "x": x,
                    "y": y,
                    "config": dict(cfg) if isinstance(cfg, dict) else {},
                }
            )
    if isinstance(edges, list):
        for e in edges:
            if not isinstance(e, Mapping):
                continue
            eid = _safe_text(e.get("id"), 80)
            src = _safe_text(e.get("from"), 120)
            dst = _safe_text(e.get("to"), 120)
            out_edges.append({"id": eid or None, "from": src, "to": dst})
    return {"nodes": out_nodes, "edges": out_edges}


def _extract_nodes_from_html(nodes_html: str) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    if not nodes_html:
        return nodes
    pattern = re.compile(
        r'data-flow-id="([^"]+)"[^>]*data-node-type="([^"]+)"',
        flags=re.I,
    )
    for m in pattern.finditer(nodes_html):
        nid = _safe_text(m.group(1), 120)
        ntype = _safe_text(m.group(2), 64).lower()
        nodes.append({"id": nid, "type": ntype, "label": "", "x": None, "y": None, "config": {}})
    return nodes


def _extract_edges_from_svg(svg_html: str) -> List[Dict[str, Any]]:
    if not svg_html:
        return []
    paths = re.findall(r"<path\b", svg_html, flags=re.I)
    return [{"id": None, "from": "", "to": ""} for _ in paths]


def _validate_node_config(ntype: str, config: Mapping[str, Any], node_id: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    spec = NODE_SPECS.get(ntype) or NODE_SPECS["generic"]
    req = spec.get("required_config") or ()
    cfg = config if isinstance(config, Mapping) else {}
    for key in req:
        val = cfg.get(key)
        if val is None or (isinstance(val, str) and not str(val).strip()):
            issues.append(
                ValidationIssue(
                    "error",
                    "missing_node_config",
                    f"Nó '{node_id}' ({ntype}): campo obrigatório em config: '{key}'.",
                )
            )
    # Validações por tipo
    if ntype == "delay" and "seconds" in cfg:
        try:
            s = float(cfg["seconds"])
            if s < 0 or s > 86400:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "delay_range",
                        f"Nó '{node_id}': delay em segundos fora do intervalo típico (0–86400).",
                    )
                )
        except (TypeError, ValueError):
            issues.append(
                ValidationIssue(
                    "error",
                    "delay_invalid",
                    f"Nó '{node_id}': 'seconds' deve ser número.",
                )
            )
    if ntype == "api" and cfg.get("method"):
        m = str(cfg["method"]).upper()
        if m not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            issues.append(
                ValidationIssue(
                    "warning",
                    "http_method",
                    f"Nó '{node_id}': método HTTP incomum: {m}.",
                )
            )
    return issues


def _detect_cycle_and_order(
    node_ids: Set[str],
    edges: List[Dict[str, Any]],
) -> Tuple[bool, List[str], List[ValidationIssue]]:
    """
    Ordenação topológica (Kahn). Deteta ciclo se nem todos os nós forem visitados.
    """
    issues: List[ValidationIssue] = []
    adj: Dict[str, List[str]] = {n: [] for n in node_ids}
    indeg0: Dict[str, int] = {n: 0 for n in node_ids}
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if not a or not b or a not in node_ids or b not in node_ids:
            continue
        adj[a].append(b)
        indeg0[b] = indeg0.get(b, 0) + 1

    indeg = dict(indeg0)
    roots = [n for n in node_ids if indeg.get(n, 0) == 0]
    if not roots:
        if edges:
            return True, [], [
                ValidationIssue("error", "no_root", "Grafo sem nó inicial (todos têm entrada). Possível ciclo.")
            ]
        roots = sorted(node_ids)

    q = deque(sorted(roots))
    order: List[str] = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in adj.get(u, []):
            indeg[v] = indeg.get(v, 0) - 1
            if indeg[v] == 0:
                q.append(v)

    has_cycle = len(order) < len(node_ids)
    if has_cycle:
        issues.append(
            ValidationIssue(
                "error",
                "cycle_or_unreachable",
                "Ciclo detetado ou nós inatingíveis a partir das raízes.",
            )
        )
    unreachable = node_ids - set(order)
    if unreachable and not has_cycle:
        issues.append(
            ValidationIssue(
                "warning",
                "unreachable_nodes",
                f"Nós possivelmente inatingíveis: {', '.join(sorted(unreachable)[:5])}"
                + ("…" if len(unreachable) > 5 else ""),
            )
        )
    return has_cycle, order, issues


def compile_flow_plan(doc: Mapping[str, Any]) -> Dict[str, Any]:
    """Compila documento validado num plano linear de passos."""
    g = _normalize_graph_payload(doc.get("graph"))
    nodes = g["nodes"]
    edges = [e for e in g["edges"] if e.get("from") and e.get("to")]
    if not nodes:
        return {"ok": False, "error": "sem nós", "steps": [], "issues": []}

    ids = {n["id"] for n in nodes}
    id_to_type = {n["id"]: n.get("type") or "generic" for n in nodes}
    id_to_cfg = {n["id"]: n.get("config") or {} for n in nodes}

    has_cycle, order, topo_issues = _detect_cycle_and_order(ids, edges)
    steps: List[Dict[str, Any]] = []
    if has_cycle:
        return {
            "ok": False,
            "steps": [],
            "issues": [i.to_dict() for i in topo_issues],
            "edge_count": len(edges),
            "node_count": len(nodes),
        }
    if order:
        for i, nid in enumerate(order):
            steps.append(
                {
                    "order": i + 1,
                    "node_id": nid,
                    "type": id_to_type.get(nid, "generic"),
                    "config": id_to_cfg.get(nid, {}),
                }
            )
    else:
        sorted_nodes = sorted(nodes, key=lambda n: (float(n.get("x") or 0), float(n.get("y") or 0)))
        for i, n in enumerate(sorted_nodes):
            nid = n["id"]
            steps.append(
                {
                    "order": i + 1,
                    "node_id": nid,
                    "type": n.get("type") or "generic",
                    "config": n.get("config") or {},
                }
            )

    return {
        "ok": True,
        "steps": steps,
        "issues": [i.to_dict() for i in topo_issues],
        "edge_count": len(edges),
        "node_count": len(nodes),
    }


def simulate_flow(doc: Mapping[str, Any], *, max_steps: int = 40) -> Dict[str, Any]:
    """Simula execução conceitual (dry-run) para revisão humana."""
    plan = compile_flow_plan(doc)
    steps = plan.get("steps") or []
    trace: List[Dict[str, Any]] = []
    ctx: Dict[str, Any] = {"vars": {}, "messages_sent": 0}

    for st in steps[:max_steps]:
        nid = st.get("node_id")
        ntype = str(st.get("type") or "generic")
        cfg = st.get("config") or {}
        spec = NODE_SPECS.get(ntype) or NODE_SPECS["generic"]
        rk = spec.get("runtime", "passthrough")
        desc = f"[{ntype}] {spec.get('label', ntype)}"
        if rk == "message" or rk == "action":
            if ntype == "conteudo" and isinstance(cfg.get("contents"), list) and cfg["contents"]:
                parts = []
                for it in cfg["contents"][:20]:
                    if not isinstance(it, dict):
                        continue
                    t = str(it.get("type") or "text").lower()
                    if t == "text":
                        parts.append(f"texto:{_safe_text(str(it.get('body')), 40)}")
                    elif t == "delay":
                        parts.append(f"delay:{it.get('seconds', '?')}s")
                    elif t in ("image", "audio", "video", "document"):
                        parts.append(f"{t}:{_safe_text(str(it.get('url')), 50)}")
                desc += " → sequência: " + (" · ".join(parts) if parts else "(vazio)")
                ctx["messages_sent"] = int(ctx.get("messages_sent", 0)) + max(1, len(parts))
            else:
                body = cfg.get("body") or cfg.get("question") or cfg.get("payload") or "(vazio)"
                desc += f" → enviar: {_safe_text(str(body), 120)}"
                ctx["messages_sent"] = int(ctx.get("messages_sent", 0)) + 1
        elif rk == "note":
            body = cfg.get("note") or cfg.get("body") or "(vazio)"
            desc += f" → anotação: {_safe_text(str(body), 120)}"
        elif rk == "delay":
            desc += f" → esperar {cfg.get('seconds', '?')}s"
        elif rk == "http":
            desc += f" → {cfg.get('method', 'GET')} {_safe_text(cfg.get('url'), 80)}"
        elif rk == "branch":
            desc += f" → avaliar: {_safe_text(cfg.get('expression'), 80)}"
        elif rk == "entry":
            desc += " → início do fluxo (gatilho)"
        elif rk == "terminal":
            desc += " → fim"
        trace.append({"node_id": nid, "type": ntype, "runtime": rk, "description": desc})

    return {
        "ok": True,
        "max_steps": max_steps,
        "context_snapshot": ctx,
        "trace": trace,
        "compile": plan,
    }


def validate_flow_document(doc: Mapping[str, Any]) -> Dict[str, Any]:
    issues: List[ValidationIssue] = []
    title = _safe_text(doc.get("title"), 200)
    if not title:
        issues.append(ValidationIssue("error", "missing_title", "Título do fluxo é obrigatório."))

    if doc.get("format") != "acassia-flow":
        issues.append(ValidationIssue("error", "invalid_format", "Formato inválido; esperado 'acassia-flow'."))
    try:
        ver = int(doc.get("version") or 0)
    except (TypeError, ValueError):
        ver = 0
    if ver != 1:
        issues.append(ValidationIssue("error", "invalid_version", "Versão inválida; esperado version=1."))

    graph = _normalize_graph_payload(doc.get("graph"))
    if not graph["nodes"]:
        graph["nodes"] = _extract_nodes_from_html(str(doc.get("nodesInnerHTML") or ""))
    if not graph["edges"]:
        graph["edges"] = _extract_edges_from_svg(str(doc.get("svgInner") or ""))

    nodes = graph["nodes"]
    edges_raw = graph["edges"]
    edges = [e for e in edges_raw if e.get("from") and e.get("to")]

    if not nodes:
        issues.append(ValidationIssue("error", "empty_flow", "Fluxo sem nós no canvas."))

    ids: Set[str] = set()
    trigger_count = 0
    for n in nodes:
        nid = _safe_text(n.get("id"), 120)
        ntype = _safe_text(n.get("type"), 64).lower() or "generic"
        if not nid:
            issues.append(ValidationIssue("error", "node_missing_id", "Existe nó sem identificador."))
            continue
        if nid in ids:
            issues.append(ValidationIssue("error", "duplicate_node_id", f"ID de nó duplicado: {nid}"))
        ids.add(nid)
        if ntype in ("trigger", "webhook"):
            trigger_count += 1
        if ntype not in ALLOWED_NODE_TYPES:
            issues.append(
                ValidationIssue(
                    "warning",
                    "unknown_node_type",
                    f"Nó '{nid}' usa tipo não catalogado: '{ntype}'.",
                )
            )
        cfg = n.get("config") if isinstance(n.get("config"), dict) else {}
        issues.extend(_validate_node_config(ntype, cfg, nid))

    if trigger_count == 0:
        issues.append(
            ValidationIssue("warning", "missing_trigger", "Fluxo sem nó de gatilho (trigger/webhook).")
        )
    elif trigger_count > 1:
        issues.append(
            ValidationIssue("warning", "many_triggers", "Fluxo com múltiplos gatilhos; confirme se é intencional.")
        )

    for e in edges:
        if e["from"] not in ids or e["to"] not in ids:
            issues.append(
                ValidationIssue(
                    "error",
                    "edge_ref_invalid",
                    f"Conexão inválida: {e['from']} -> {e['to']}.",
                )
            )

    if nodes and not edges:
        issues.append(
            ValidationIssue(
                "warning",
                "unresolved_edges",
                "Sem arestas estruturadas: compile usará ordem por posição (fallback).",
            )
        )

    has_cycle, _, topo_issues = _detect_cycle_and_order(ids, edges)
    issues.extend(topo_issues)
    if has_cycle:
        pass  # já erro em topo_issues

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    # Normalizar saída com configs garantidos
    norm_nodes = []
    for n in nodes:
        nid = _safe_text(n.get("id"), 120)
        if not nid:
            continue
        cfg = n.get("config") if isinstance(n.get("config"), dict) else {}
        norm_nodes.append(
            {
                "id": nid,
                "type": _safe_text(n.get("type"), 64).lower() or "generic",
                "label": _safe_text(n.get("label"), 200),
                "x": n.get("x"),
                "y": n.get("y"),
                "config": dict(cfg),
            }
        )

    normalized = {
        "format": "acassia-flow",
        "version": 1,
        "title": title,
        "graph": {"nodes": norm_nodes, "edges": [e for e in edges_raw if e.get("from") and e.get("to")]},
    }

    return {
        "ok": len(errors) == 0 and not has_cycle,
        "errors": [i.to_dict() for i in errors],
        "warnings": [i.to_dict() for i in warnings],
        "normalized": normalized,
        "compile_hint": compile_flow_plan(normalized),
    }
