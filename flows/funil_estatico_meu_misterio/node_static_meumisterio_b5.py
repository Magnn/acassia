"""Bloco 5 — ver `roteiro.py`."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    cfg = R.cfg(ctx)

    if meta.get(R.META_B5_SEQ):
        if (meta.get(R.META_B5_PHASE) or "").strip() == "awaiting_reply":
            if not R.lead_respondeu_texto_ou_midia(ctx):
                return [], "static_meumisterio_b5"
            logger.info("event=static_mm_b5_avanca_para_b6 lead=%s", getattr(ctx, "lead_id", "?"))
            return [Acao(tipo="delay", segundos=R.B5_DELAY_ANTES_B6_S)], "static_meumisterio_b6"
        return [], "static_meumisterio_b5"

    meta[R.META_B5_SEQ] = True
    meta[R.META_B5_PHASE] = "awaiting_reply"
    return R.montar_acoes_bloco5(cfg), "static_meumisterio_b5"
