"""Bloco 7 — pós-pagamento aprovado (Cakto); ver `roteiro.py`."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    if meta.get(R.META_B7_SEQ):
        return [], "static_meumisterio_b7"

    meta[R.META_B7_SEQ] = True
    return R.montar_acoes_bloco7(R.cfg(ctx)), "static_meumisterio_b7"
