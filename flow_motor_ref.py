"""
C3 — Bloco `motor_ref` do Flow Builder: importar e chamar uma função Python controlada.

- **FLOW_BLUEPRINT_ALLOW_MOTOR_REF=1** para executar chamadas reais em `steps_to_acoes`.
- **FLOW_BLUEPRINT_MOTOR_REF_ALLOWLIST** — lista separada por vírgulas de prefixos de módulo
  permitidos (default: `flows.flow_blueprint_motor`).
- **module_hint** no canvas: `pacote.modulo:funcao` (ex.: `flows.flow_blueprint_motor.demo:demo_greeting`).

A função deve devolver `list[Acao]`. Assinatura recomendada::

    def hook(flow_vars: dict, *, node_id: str = "", blueprint_id: int | None = None, tenant_id: str | None = None) -> list[Acao]:
"""
from __future__ import annotations

import importlib
import logging
import os
from dataclasses import replace
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from schema import Acao

logger = logging.getLogger(__name__)

_ALLOW_MOTOR_REF = str(os.getenv("FLOW_BLUEPRINT_ALLOW_MOTOR_REF", "") or "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def flow_blueprint_allow_motor_ref() -> bool:
    """Indica se nós `motor_ref` executam hooks Python (C3)."""
    return _ALLOW_MOTOR_REF


def _allowlist_prefixes() -> List[str]:
    raw = (os.getenv("FLOW_BLUEPRINT_MOTOR_REF_ALLOWLIST") or "flows.flow_blueprint_motor").strip()
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or ["flows.flow_blueprint_motor"]


def _module_allowed(module_name: str) -> bool:
    for p in _allowlist_prefixes():
        if module_name == p or module_name.startswith(p + "."):
            return True
    return False


def _parse_module_hint(hint: str) -> Tuple[str, str, Optional[str]]:
    h = (hint or "").strip()
    if ":" not in h:
        return "", "", "use `pacote.modulo:funcao` em module_hint"
    mod, _, fn = h.rpartition(":")
    mod, fn = mod.strip(), fn.strip()
    if not mod or not fn or ".." in mod or mod.startswith("."):
        return "", "", "module_hint inválido"
    if not _module_allowed(mod):
        return "", "", f"módulo fora da allowlist ({mod})"
    return mod, fn, None


def _resolve_callable(module_name: str, attr: str) -> Tuple[Optional[Callable[..., Any]], Optional[str]]:
    try:
        mod = importlib.import_module(module_name)
    except Exception as e:
        return None, f"import: {e}"
    fn = getattr(mod, attr, None)
    if not callable(fn):
        return None, "função não encontrada"
    return fn, None


def _call_hook(
    fn: Callable[..., Any],
    flow_vars: Dict[str, Any],
    *,
    node_id: str,
    blueprint_id: Optional[int],
    tenant_id: Optional[str],
) -> Any:
    try:
        return fn(
            flow_vars,
            node_id=node_id,
            blueprint_id=blueprint_id,
            tenant_id=tenant_id,
        )
    except TypeError:
        try:
            return fn(flow_vars, node_id=node_id)
        except TypeError:
            return fn(flow_vars)


def invoke_flow_motor_ref(
    module_hint: str,
    flow_vars: Mapping[str, Any],
    *,
    node_id: str,
    blueprint_id: Optional[int],
    tenant_id: Optional[str],
) -> Tuple[List[Acao], Optional[str]]:
    """
    Importa `module_hint`, chama a função e devolve (lista de Acao, erro).
    Se erro não for None, a lista está vazia.
    """
    mod_name, func_name, perr = _parse_module_hint(module_hint)
    if perr:
        return [], perr
    fn, err = _resolve_callable(mod_name, func_name)
    if err:
        return [], err
    fv = dict(flow_vars)
    try:
        raw = _call_hook(
            fn,
            fv,
            node_id=node_id or "",
            blueprint_id=blueprint_id,
            tenant_id=tenant_id,
        )
    except Exception as e:
        logger.exception("invoke_flow_motor_ref: falha ao chamar %s", module_hint)
        return [], str(e)[:500]
    if not isinstance(raw, list):
        return [], "a função deve devolver list[Acao]"
    out: List[Acao] = []
    for i, item in enumerate(raw):
        if not isinstance(item, Acao):
            return [], f"item {i} não é Acao"
        md = dict(item.metadata or {})
        md.setdefault("source", "flow_builder")
        md.setdefault("runtime", "motor_ref")
        md["motor_ref"] = module_hint[:220]
        out.append(replace(item, metadata=md))
    return out, None
