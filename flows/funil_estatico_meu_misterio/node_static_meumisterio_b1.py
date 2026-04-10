"""Bloco 1 — ver `roteiro.py` e `__init__.py`."""

from __future__ import annotations

import logging
from typing import List, Tuple

from schema import Acao

from flows.funil_estatico_meu_misterio import roteiro as R

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", None) or {}
    cfg = R.cfg(ctx)
    phase = (meta.get(R.META_B1_PHASE) or "").strip()

    if phase == "awaiting_reply":
        if not R.lead_respondeu_texto_ou_midia(ctx):
            return [], "static_meumisterio_b1"
        meta["static_mm_b1_concluido_em"] = True
        logger.info("event=static_mm_b1_avanca_para_b2 lead=%s", getattr(ctx, "lead_id", "?"))
        return [Acao(tipo="delay", segundos=R.B1_DELAY_ANTES_B2_S)], "static_meumisterio_b2"

    txt = (ctx.texto_recebido or "").strip()
    if R.texto_sistema_ignorar(txt):
        return [], "static_meumisterio_b1"

    if not R.RE_GATILHO_B1.search(txt):
        nudge = (
            "Oi! 💫 Para eu iniciar seu atendimento por aqui, escreve *quero minha consulta* "
            "nesta conversa."
        )
        return (
            [
                R.acao_texto_copy_exata(
                    nudge,
                    source="static_meumisterio_b1",
                    kind="nudge_gatilho",
                )
            ],
            "static_meumisterio_b1",
        )

    if not R.url_imagem_perfil_instagram(cfg):
        logger.warning(
            "static_meumisterio_b1: imagem do Instagram sem URL pública — "
            "defina PUBLIC_URL ou CLIENTE_IMAGEM_PERFIL_INSTAGRAM."
        )

    meta[R.META_B1_PHASE] = "awaiting_reply"
    return R.montar_acoes_bloco1(cfg), "static_meumisterio_b1"
