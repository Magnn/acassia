"""
flows/fase_4_entrega/node_16_downsell.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOWNSELL ESTRATÉGICO — MASTER SUPREMA v1.0

PROPÓSITO:
  Recuperar leads que não pagaram R$60. 
  Oferece R$30 (metade) em materiais, com o restante pago pós-resultado.
"""

import logging
import math
import random
from schema import Acao
from copy_sanitizer import (
    frase_dor_contextualizada,
    genero_efetivo_para_copy,
    nome_lead_para_exibicao,
    resumo_dor_para_copy,
    vocativo_meumisterio,
)
from flows.funnel_gates import VOCATIVO_SEM_NOME

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> tuple:
    nome = (ctx.nome_lead or "").strip() or VOCATIVO_SEM_NOME
    nome_fmt = nome_lead_para_exibicao(nome)

    meta = getattr(ctx, "metadata", {}) or {}
    msg_lead = str(getattr(ctx, "texto_recebido", "") or "").strip()
    meta["genero_lead"] = genero_efetivo_para_copy(nome, meta, texto_discurso=msg_lead or None)
    voc = vocativo_meumisterio(nome, metadata=meta)
    config = meta.get("__config__", {})

    # Preço do downsell: metade de preco_materiais (ou preco_downsell explícito no config)
    try:
        p_ref = int(str(config.get("preco_materiais", 60) or 60))
    except (TypeError, ValueError):
        p_ref = 60
    try:
        p_down = int(str(config.get("preco_downsell", "") or "").strip() or math.ceil(p_ref / 2))
    except (TypeError, ValueError):
        p_down = math.ceil(p_ref / 2)

    # Link de downsell deve ser um checkout separado (preço diferente = URL diferente)
    link_downsell = str(config.get("link_downsell") or config.get("link_pagamento") or "[LINK]").strip()

    desejo_oculto = str(meta.get("desejo_oculto") or meta.get("desejo_declarado") or "").strip()[:100]
    dor_real = resumo_dor_para_copy(
        str(meta.get("resumo_dor") or "essa situação que carrega no peito"),
        max_len=80,
    )
    dor_ctx = frase_dor_contextualizada(dor_real, abertura="sabendo do que você traz")

    _motivo_desejo = f" para {desejo_oculto}" if desejo_oculto else ""

    acoes = [
        Acao(tipo="delay", segundos=random.randint(8, 12)),
        Acao(tipo="text", conteudo=f"{voc}, tenho uma notícia boa pra você. 🕯️"),
        Acao(tipo="delay", segundos=random.randint(15, 25)),
        Acao(
            tipo="text",
            conteudo=(
                f"Eu sei que {dor_ctx}, e não quero que a parte financeira seja o que impede "
                f"você de dar esse passo{_motivo_desejo}."
            ),
        ),
        Acao(tipo="delay", segundos=random.randint(12, 18)),
        Acao(
            tipo="text",
            conteudo=(
                f"Consegui liberar os materiais por R$ {p_down},00 — metade do valor original. "
                "A outra parte você fecha comigo só quando já estiver sentindo a mudança."
            ),
        ),
        Acao(tipo="delay", segundos=random.randint(15, 22)),
        Acao(
            tipo="text",
            conteudo="Fiz isso porque acredito no que apareceu na sua leitura. O caminho está aberto — depende só de você entrar.",
        ),
        Acao(tipo="delay", segundos=random.randint(10, 15)),
        Acao(tipo="text", conteudo="Se couber no seu momento agora, o acesso é por aqui:"),
        Acao(tipo="delay", segundos=random.randint(5, 9)),
        Acao(
            tipo="text",
            conteudo=link_downsell,
            metadata={"skip_gancho_final": True},
        ),
        Acao(tipo="delay", segundos=random.randint(8, 12)),
        Acao(tipo="text", conteudo="Assim que concluir, manda o comprovante aqui para eu liberar os materiais na hora. ✨"),
    ]

    logger.info("event=node16_downsell lead=%s valor=%s", nome_fmt, p_down)
    ctx.metadata = meta
    return acoes, "aguardando_pagamento_downsell"