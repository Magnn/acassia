"""Bloco 6 — fecho do funil estático Meu Mistério (ver `roteiro.py`)."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    if meta.get(R.META_B6_SEQ):
        return [], "static_meumisterio_b6"

    meta[R.META_B6_SEQ] = True
    return R.montar_acoes_bloco6(R.cfg(ctx)), "static_meumisterio_b6"
