"""Bloco 5 — placeholder até o roteiro ser definido."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    if meta.get("static_mm_b5_placeholder_enviado"):
        return [], "static_meumisterio_b5"

    meta["static_mm_b5_placeholder_enviado"] = True
    texto = (
        "Perfeito — seguimos para a próxima etapa. 💙 "
        "O *Bloco 5* ainda vai ser montado no código quando você enviar o roteiro."
    )
    return (
        [
            R.acao_texto_copy_exata(
                texto,
                source="static_meumisterio_b5",
                kind="placeholder_b5",
            )
        ],
        "static_meumisterio_b5",
    )
