"""
Percurso do grafo do Flow Builder com ramificação real em nós `condicao` (B1) e `divisao` (B2).

- B1: regras alinhadas ao simulador (`flowSimEvaluateCondicaoRulesDetailed`).
- B2: divisão A/B com pesos (A:50,B:50 ou lista), escolha **determinística** por lead/tenant/blueprint,
  persistência em `metadata_json` com chave `flow_divisao__<node_id>`.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

logger = logging.getLogger(__name__)

_MAX_WALK_STEPS = 400


def _substitute_vars(template: str, ctx: Mapping[str, Any]) -> str:
    s = str(template or "")
    if "{{" not in s:
        return s
    out = s
    for k, v in ctx.items():
        key = str(k).strip()
        if not key:
            continue
        out = out.replace("{{" + key + "}}", str(v if v is not None else ""))
        out = out.replace("{{ " + key + " }}", str(v if v is not None else ""))
    return out


def _resolve_operand(raw: Any, ctx: Mapping[str, Any]) -> str:
    """
    Operando de regra: se tiver `{{ }}` substitui; senão, se a string for chave em ctx usa o valor;
    caso contrário trata como literal (ex.: comparar campo `nome` com o texto Maria).
    """
    s = str(raw or "").strip()
    if not s:
        return ""
    if "{{" in s:
        return _substitute_vars(s, ctx)
    if s in ctx:
        v = ctx[s]
        return "" if v is None else str(v)
    return s


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _evaluate_one_rule(rule: Mapping[str, Any], ctx: Mapping[str, Any]) -> bool:
    op_aliases = {
        "equals": "eq",
        "not_equals": "ne",
        "before": "lt",
        "after": "gt",
    }
    op = str(rule.get("op") or "eq").strip().lower()
    op = op_aliases.get(op, op)
    raw_var = rule.get("var")
    custom_field = str(rule.get("custom_field") or "").strip()
    if custom_field and str(raw_var or "") in ("contact.custom", "flow.field", "webhook.data"):
        raw_var = custom_field
    left = _resolve_operand(raw_var, ctx)
    right = _resolve_operand(rule.get("val") if "val" in rule else rule.get("value"), ctx)
    if op == "eq":
        return _normalize(left) == _normalize(right)
    if op == "ne":
        return _normalize(left) != _normalize(right)
    if op == "contains":
        return _normalize(right) in _normalize(left)
    if op == "not_contains":
        return _normalize(right) not in _normalize(left)
    if op == "gt":
        try:
            def _number(value: Any) -> float:
                raw = str(value).strip()
                if re.fullmatch(r"\d{1,2}:\d{2}", raw):
                    hours, minutes = raw.split(":", 1)
                    return float(int(hours) * 60 + int(minutes))
                return float(raw.replace(",", ".").replace(" ", ""))

            a = _number(left)
            b = _number(right)
            return a > b
        except (TypeError, ValueError):
            return False
    if op == "lt":
        try:
            def _number(value: Any) -> float:
                raw = str(value).strip()
                if re.fullmatch(r"\d{1,2}:\d{2}", raw):
                    hours, minutes = raw.split(":", 1)
                    return float(int(hours) * 60 + int(minutes))
                return float(raw.replace(",", ".").replace(" ", ""))

            a = _number(left)
            b = _number(right)
            return a < b
        except (TypeError, ValueError):
            return False
    if op == "empty":
        return str(left).strip() == ""
    if op == "not_empty":
        return str(left).strip() != ""
    return False


def evaluate_condicao_rules(cfg: Mapping[str, Any], ctx: Mapping[str, Any]) -> Tuple[bool, str, bool]:
    """
    Retorna (pass, logic_upper, has_rules).
    Sem regras válidas: has_rules False e pass False (execução automática conservadora).
    """
    rules_all = cfg.get("rules")
    if not isinstance(rules_all, list):
        rules_all = []
    rules = [r for r in rules_all if isinstance(r, dict) and str(r.get("var") or "").strip()]
    if not rules:
        return False, "AND", False
    logic = "OR" if str(cfg.get("logic") or "AND").upper() == "OR" else "AND"
    parts = [_evaluate_one_rule(r, ctx) for r in rules]
    if logic == "OR":
        passed = any(parts)
    else:
        passed = all(parts)
    return passed, logic, True


def pick_condicao_next_node(
    cfg: Mapping[str, Any],
    outgoing: List[Dict[str, Any]],
    pass_true: bool,
) -> Optional[str]:
    """Escolhe o id do nó destino (alinhado ao canvas / flowSimPickCondicaoBranch)."""
    if not outgoing:
        return None
    want_key = "true_to" if pass_true else "false_to"
    want = str(cfg.get(want_key) or "").strip()
    if want:
        for e in outgoing:
            if str(e.get("to") or "").strip() == want:
                return str(e.get("to")).strip()
    lab_sim = None
    lab_nao = None
    for e in outgoing:
        # Prioriza o novo padrão (sourceHandle: 'true' / 'false')
        sh = str(e.get("sourceHandle") or "").lower()
        if sh == "true":
            lab_sim = e
        elif sh == "false":
            lab_nao = e
        else:
            # Fallback para o padrão legado (edges com texto 'sim' / 'não')
            lab = str(e.get("label") or "")
            if re.search(r"sim|yes|true|v\b", lab, re.I):
                lab_sim = e
            if re.search(r"não|nao|no|false|f\b", lab, re.I):
                lab_nao = e
    if pass_true:
        pick = lab_sim or (outgoing[0] if outgoing else None)
    else:
        pick = lab_nao or (outgoing[1] if len(outgoing) > 1 else outgoing[0] if outgoing else None)
    if pick is None:
        return None
    return str(pick.get("to") or "").strip() or None


def graph_has_condicao(doc: Mapping[str, Any]) -> bool:
    g = doc.get("graph") if isinstance(doc.get("graph"), dict) else {}
    nodes = g.get("nodes")
    if not isinstance(nodes, list):
        return False
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if str(n.get("type") or "").lower() == "condicao":
            return True
    return False


def graph_has_divisao(doc: Mapping[str, Any]) -> bool:
    g = doc.get("graph") if isinstance(doc.get("graph"), dict) else {}
    nodes = g.get("nodes")
    if not isinstance(nodes, list):
        return False
    for n in nodes:
        if not isinstance(n, dict):
            continue
        ntype = str(n.get("type") or "").lower()
        if ntype in ("divisao", "ab_split"):
            return True
    return False


def graph_needs_context_walk(doc: Mapping[str, Any]) -> bool:
    return graph_has_condicao(doc) or graph_has_divisao(doc)


def divisao_branch_labels(edges: List[Dict[str, Any]]) -> List[str]:
    letters = list("ABCDEFGHIJ")
    out: List[str] = []
    for i, e in enumerate(edges):
        raw = str(e.get("label") or "").strip()
        out.append(raw or f"Ramo {letters[i] if i < len(letters) else i + 1}")
    return out


def parse_divisao_weights(weights_str: Optional[str], edges: List[Dict[str, Any]]) -> Optional[List[float]]:
    """Alinha a `flowSimParseDivisaoWeights` no dashboard."""
    n = len(edges)
    if n == 0:
        return None
    raw = str(weights_str or "").strip()
    if not raw:
        return None
    pairs = []
    re_pat = re.compile(r"([A-Za-z0-9_]+)\s*:\s*(\d+(?:\.\d+)?)")
    for m in re_pat.finditer(raw):
        pairs.append((m.group(1).upper(), max(0.0, float(m.group(2)) or 0.0)))
    if pairs:
        by_key = {a[0]: a[1] for a in pairs}
        letters = list("ABCDEFGHIJ")
        out_w: List[float] = []
        for i, e in enumerate(edges):
            lab = str(e.get("label") or "").strip().upper()
            if lab and lab in by_key:
                out_w.append(by_key[lab])
            else:
                L = letters[i] if i < len(letters) else ""
                if L and L in by_key:
                    out_w.append(by_key[L])
                else:
                    out_w.append(1.0)
        return out_w
    nums: List[float] = []
    for part in re.split(r"[,;]", raw):
        try:
            v = float(str(part).strip())
            if v >= 0 and math.isfinite(v):
                nums.append(v)
        except ValueError:
            pass
    if len(nums) >= n:
        return nums[:n]
    if len(nums) == 2 and n == 2:
        return nums
    return None


def divisao_persist_key(node_id: str) -> str:
    safe = re.sub(r"[^\w\-.]+", "_", str(node_id))
    return f"flow_divisao__{safe}"


def stable_weighted_index(weights: List[float], seed_parts: Tuple[str, ...]) -> int:
    s = sum(weights)
    if s <= 0:
        h = int(hashlib.sha256("|".join(seed_parts).encode("utf-8")).hexdigest()[:8], 16)
        return h % len(weights)
    r = (int(hashlib.sha256("|".join(seed_parts).encode("utf-8")).hexdigest()[:8], 16) % 1000000) / 1000000.0 * s
    cum = 0.0
    for i, w in enumerate(weights):
        cum += w
        if r < cum:
            return i
    return len(weights) - 1


def pick_divisao_next_node(
    node_id: str,
    cfg: Mapping[str, Any],
    outgoing: List[Dict[str, Any]],
    ctx: Dict[str, Any],
    *,
    blueprint_id: Optional[int],
    tenant_id: Optional[str],
    divisao_metadata_out: Optional[Dict[str, Any]],
) -> Optional[str]:
    if not outgoing:
        return None
    pkey = divisao_persist_key(node_id)
    stored = ctx.get(pkey)
    to_id: Optional[str] = None
    if isinstance(stored, dict):
        to_id = str(stored.get("to") or "").strip()
    elif isinstance(stored, str):
        to_id = stored.strip()
    if to_id:
        for e in outgoing:
            if str(e.get("to") or "").strip() == to_id:
                return to_id
    labels = divisao_branch_labels(outgoing)
    synthetic: List[Dict[str, Any]] = []
    for i, e in enumerate(outgoing):
        d = dict(e)
        d["label"] = labels[i]
        synthetic.append(d)
    wts = parse_divisao_weights(str(cfg.get("weights") or ""), synthetic)
    if not wts or len(wts) != len(outgoing):
        wts = [1.0] * len(outgoing)
    lid = str(ctx.get("lead_id") or "")
    tid = str(tenant_id or ctx.get("tenant_id") or "default")
    bid = str(blueprint_id or ctx.get("blueprint_id") or "0")
    seed = (tid, lid, node_id, bid)
    idx = stable_weighted_index(wts, seed)
    edge = outgoing[idx]
    nxt = str(edge.get("to") or "").strip()
    payload = {"to": nxt, "label": labels[idx], "blueprint_id": blueprint_id}
    ctx[pkey] = payload
    if divisao_metadata_out is not None:
        divisao_metadata_out[pkey] = dict(payload)
    return nxt or None


def graph_walk_steps(
    doc: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    blueprint_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
    divisao_metadata_out: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Percorre o DAG a partir do nó inicial; em `condicao` avalia regras e segue **um** ramo.
    Em `divisao` escolhe ramo por pesos (determinístico) ou reutiliza `flow_divisao__*` no contexto.
    Não inclui `condicao` / `divisao` na lista de passos (só roteiam).
    """
    g = doc.get("graph") if isinstance(doc.get("graph"), dict) else {}
    nodes_raw = g.get("nodes")
    edges_raw = g.get("edges")
    if not isinstance(nodes_raw, list) or not nodes_raw:
        return []
    nodes: Dict[str, Dict[str, Any]] = {}
    for n in nodes_raw:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or "").strip()
        if not nid:
            continue
        cfg = n.get("config") if isinstance(n.get("config"), dict) else {}
        nodes[nid] = {
            "id": nid,
            "type": str(n.get("type") or "generic").lower(),
            "label": str(n.get("label") or ""),
            "config": dict(cfg),
        }
    ids = set(nodes.keys())
    edges = []
    if isinstance(edges_raw, list):
        for e in edges_raw:
            if not isinstance(e, dict):
                continue
            a, b = str(e.get("from") or "").strip(), str(e.get("to") or "").strip()
            if a and b and a in ids and b in ids:
                edges.append(
                    {
                        "from": a,
                        "to": b,
                        "id": e.get("id"),
                        "label": str(e.get("label") or ""),
                        "sourceHandle": str(e.get("sourceHandle") or ""),
                        "targetHandle": str(e.get("targetHandle") or ""),
                    }
                )

    by_from: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in edges:
        by_from[str(e["from"])].append(e)

    incoming: Set[str] = set()
    for e in edges:
        incoming.add(str(e["to"]))

    roots = [i for i in ids if i not in incoming]
    if not roots:
        roots = sorted(ids)

    id_to_type = {k: v["type"] for k, v in nodes.items()}
    start: Optional[str] = None
    for r in roots:
        if id_to_type.get(r) in ("trigger", "webhook"):
            start = r
            break
    if start is None and roots:
        start = roots[0]
    if start is None:
        return []

    ctx: Dict[str, Any] = dict(context) if context else {}
    if blueprint_id is not None:
        ctx.setdefault("blueprint_id", blueprint_id)
    if tenant_id is not None:
        ctx.setdefault("tenant_id", tenant_id)

    order: List[Dict[str, Any]] = []
    steps = 0
    visited_global: Set[str] = set()

    def dfs(nid: str, path: Set[str]) -> None:
        nonlocal steps
        if steps > _MAX_WALK_STEPS:
            logger.warning("graph_walk_steps: limite de passos (%s)", _MAX_WALK_STEPS)
            return
        if nid not in nodes:
            return
        if nid in path:
            logger.warning("graph_walk_steps: ciclo detetado em %s", nid)
            return
            
        if nid in visited_global:
            return
            
        visited_global.add(nid)
        path = set(path)
        path.add(nid)
        steps += 1

        n = nodes[nid]
        typ = n["type"]
        cfg = n["config"]

        if typ == "condicao":
            passed, logic, has_rules = evaluate_condicao_rules(cfg, ctx)
            if not has_rules:
                logger.info(
                    "event=flow_condicao_sem_regras node=%s — ramo falso (defina regras no bloco)",
                    nid,
                )
                passed = False
            nxt = pick_condicao_next_node(cfg, by_from.get(nid, []), passed)
            logger.debug(
                "event=flow_condicao_branch node=%s pass=%s logic=%s next=%s",
                nid,
                passed,
                logic,
                nxt,
            )
            if nxt:
                dfs(nxt, path)
            return

        if typ == "divisao":
            outs_div = by_from.get(nid, [])
            nxt = pick_divisao_next_node(
                nid,
                cfg,
                outs_div,
                ctx,
                blueprint_id=blueprint_id,
                tenant_id=tenant_id,
                divisao_metadata_out=divisao_metadata_out,
            )
            logger.debug("event=flow_divisao_branch node=%s next=%s", nid, nxt)
            if nxt:
                dfs(nxt, path)
            return

        if typ == "ab_split":
            # A/B Split: roteamento determinístico + persistência (fim do random flutuante)
            pkey = divisao_persist_key(nid)
            stored = ctx.get(pkey)
            variant = None
            
            if isinstance(stored, dict):
                variant = str(stored.get("variant") or "").upper()
            elif isinstance(stored, str):
                variant = stored.strip().upper()
                
            outs_ab = by_from.get(nid, [])
            
            # Backwards compatibility e suporte dinâmico a N pesos
            weights_arr = []
            raw_wts = cfg.get("weights")
            if isinstance(raw_wts, list) and len(raw_wts) >= 2:
                weights_arr = [float(w) for w in raw_wts]
            else:
                wa = max(1, min(99, int(cfg.get("weight_a") or 50)))
                weights_arr = [float(wa), 100.0 - float(wa)]
            
            if variant is None or variant == "":
                lid = str(ctx.get("lead_id") or "")
                tid = str(tenant_id or ctx.get("tenant_id") or "default")
                bid = str(blueprint_id or ctx.get("blueprint_id") or "0")
                seed = (tid, lid, nid, bid)
                idx = stable_weighted_index(weights_arr, seed)
                # idx 0 -> A, idx 1 -> B, idx 2 -> C...
                variant = chr(65 + idx)
                
                # Persiste a variante para que o frontend/motor consigam recarregar exatamente a mesma rota
                payload = {"variant": variant, "blueprint_id": blueprint_id}
                ctx[pkey] = payload
                if divisao_metadata_out is not None:
                    divisao_metadata_out[pkey] = dict(payload)

            order.append({
                "order": len(order) + 1,
                "node_id": nid,
                "type": typ,
                "config": {**cfg, "_chosen_variant": variant},
            })

            nxt = None
            for e in outs_ab:
                sh = str(e.get("sourceHandle") or "").upper()
                if sh == variant:
                    nxt = str(e.get("to") or "").strip()
                    break
            
            if not nxt:
                # Fallback: a variante 'A' é índice 0, 'B' é 1, 'C' é 2...
                idx = ord(variant) - 65
                if 0 <= idx < len(outs_ab):
                    nxt = str(outs_ab[idx].get("to") or "").strip()
                    
            if nxt:
                logger.debug("event=flow_ab_split node=%s variant=%s next=%s", nid, variant, nxt)
                dfs(nxt, path)
            return

        if typ in ("end",):
            return

        if typ in ("trigger", "webhook"):
            outs = by_from.get(nid, [])
            for edge in outs:
                dfs(str(edge["to"]), path)
            return

        order.append(
            {
                "order": len(order) + 1,
                "node_id": nid,
                "type": typ,
                "config": cfg,
            }
        )

        outs = by_from.get(nid, [])
        if not outs:
            return
        
        # Faz o trace em todas as rotas filhas, garantindo que timeouts e respostas não sejam perdidos
        for edge in outs:
            dfs(str(edge["to"]), path)

    dfs(start, set())
    return order
