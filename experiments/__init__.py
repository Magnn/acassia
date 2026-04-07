"""Registro leve de hipóteses A/B e experimentos (ligação futura ao template_registry)."""

from experiments.registry import listar_experimentos, obter_experimento

__all__ = ["listar_experimentos", "obter_experimento"]
