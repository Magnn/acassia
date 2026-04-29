"""Blueprints semente de pós-pagamento (clonados pro tenant no onboarding)."""

import json
from pathlib import Path

_HERE = Path(__file__).parent

AVAILABLE_SEEDS = ("express", "premium")


def load_seed(template: str) -> dict:
    """
    Carrega o JSON de um blueprint semente de pós-pagamento.

    Args:
        template: ``'express'`` (Tarot R$19-49) ou ``'premium'`` (Quiromancia R$197+).

    Returns:
        Dict acassia-flow v1 pronto pra clonar via FlowBlueprint.

    Raises:
        ValueError: se ``template`` não está em AVAILABLE_SEEDS.
        FileNotFoundError: se o JSON foi removido do disco.
    """
    if template not in AVAILABLE_SEEDS:
        raise ValueError(f"template inválido: {template!r}. Disponíveis: {AVAILABLE_SEEDS}")

    path = _HERE / f"post_payment_{template}.json"
    return json.loads(path.read_text(encoding="utf-8"))
