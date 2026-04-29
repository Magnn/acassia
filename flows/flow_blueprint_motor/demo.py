"""Exemplo de hook para o bloco *Referência motor Python* (`module_hint` = `flows.flow_blueprint_motor.demo:demo_greeting`)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from schema import Acao


def demo_greeting(
    flow_vars: Dict[str, Any],
    *,
    node_id: str = "",
    blueprint_id: Optional[int] = None,
    tenant_id: Optional[str] = None,
) -> List[Acao]:
    nome = str(flow_vars.get("nome") or "visitante")
    return [
        Acao(
            tipo="text",
            conteudo=f"[motor_ref demo] Olá, {nome}!",
            metadata={"motor_demo": True},
        )
    ]
