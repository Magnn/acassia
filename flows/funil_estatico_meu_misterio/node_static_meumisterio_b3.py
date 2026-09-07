"""Bloco 3 — ver `roteiro.py`."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    cfg = R.cfg(ctx)

    if meta.get(R.META_B3_SEQ):
        if (meta.get(R.META_B3_PHASE) or "").strip() == "awaiting_reply":
            if not bool(meta.get("static_mm_b3_entregue")):
                if R.lead_respondeu_texto_ou_midia(ctx) and R.dispatch_em_andamento_recente(meta, "static_mm_b3"):
                    logger.info("event=static_mm_b3_reply_durante_dispatch lead=%s", getattr(ctx, "lead_id", "?"))
                    return [], "static_meumisterio_b4"
                meta[R.META_B3_PHASE] = "awaiting_reply"
                return R.montar_acoes_bloco3(cfg), "static_meumisterio_b3"
            if not R.lead_respondeu_texto_ou_midia(ctx):
                return [], "static_meumisterio_b3"
            logger.info("event=static_mm_b3_avanca_para_b4 lead=%s", getattr(ctx, "lead_id", "?"))
            return [], "static_meumisterio_b4"
        return [], "static_meumisterio_b3"

    meta[R.META_B3_SEQ] = True
    meta[R.META_B3_PHASE] = "awaiting_reply"
    return R.montar_acoes_bloco3(cfg), "static_meumisterio_b3"
