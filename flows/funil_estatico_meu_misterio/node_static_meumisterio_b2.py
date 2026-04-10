"""Bloco 2 — ver `roteiro.py`."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    cfg = R.cfg(ctx)

    if (meta.get(R.META_B2_PHASE) or "").strip() == "awaiting_nome_amado":
        if not R.lead_respondeu_texto_ou_midia(ctx):
            return [], "static_meumisterio_b2"
        nome = (ctx.texto_recebido or "").strip()
        if nome:
            meta[R.META_NOME_AMADO] = nome[:200]
        logger.info("event=static_mm_b2_avanca_para_b3 lead=%s", getattr(ctx, "lead_id", "?"))
        return [], "static_meumisterio_b3"

    if meta.get(R.META_B2_SEQ):
        return [], "static_meumisterio_b2"

    if not R.url_audio_b2_publica(cfg):
        logger.warning(
            "static_meumisterio_b2: sem URL pública para áudio — defina PUBLIC_URL e coloque o .ogg em "
            "assets/funil_estatico_meu_misterio/audio/ (ver roteiro.AUDIO_B2_PRIORIDADE)."
        )

    meta[R.META_B2_SEQ] = True
    meta[R.META_B2_PHASE] = "awaiting_nome_amado"
    return R.montar_acoes_bloco2(cfg), "static_meumisterio_b2"
