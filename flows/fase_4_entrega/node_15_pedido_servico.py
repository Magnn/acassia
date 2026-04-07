"""
flows/fase_4_entrega/node_15_pedido_servico.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Segunda parte da troca (honra) — sem narrativa manipulativa.

PROPÓSITO:
  Cobrar a parcela combinada após resultado, alinhada ao pacto 65+65 do funil.
  Tom direto, digno, sem histórias familiares ou urgência emocional falsa.
"""

import logging
import random
from schema import Acao
from copy_sanitizer import genero_efetivo_para_copy, nome_lead_para_exibicao, vocativo_cigana

logger = logging.getLogger(__name__)


def executar_v2(ctx) -> tuple:
    nome = (ctx.nome_lead or "meu bem").strip() or "meu bem"
    nome_fmt = nome_lead_para_exibicao(nome)

    meta = getattr(ctx, "metadata", {}) or {}
    msg_lead = str(getattr(ctx, "texto_recebido", "") or "").strip()
    meta["genero_lead"] = genero_efetivo_para_copy(nome, meta, texto_discurso=msg_lead or None)
    voc = vocativo_cigana(nome, metadata=meta)
    config = meta.get("__config__", {})

    link = meta.get("link_pagamento", config.get("link_pagamento", "[LINK]"))
    p_honra = config.get("preco_servico", "60")

    acoes = [
        Acao(tipo="delay", segundos=random.randint(10, 15)),
        Acao(
            tipo="text",
            conteudo=f"{voc}, como você está? Quero saber se já sentiu alguma mudança no peito desde a firmação... 💜",
        ),
        Acao(tipo="delay", segundos=random.randint(14, 22)),
        Acao(
            tipo="text",
            conteudo="A gente combinou a troca em duas partes: materiais no começo e a honra depois que você colhe o que pediu aos guias.",
        ),
        Acao(tipo="delay", segundos=random.randint(12, 18)),
        Acao(
            tipo="text",
            conteudo="Se já notou abertura nos caminhos, é o momento de fechar a segunda parte com retidão, como fechamos na conversa.",
        ),
        Acao(tipo="delay", segundos=random.randint(12, 20)),
        Acao(
            tipo="text",
            conteudo=f"Quando puder, ajusta aí os R$ {p_honra},00 da nossa troca final pelo mesmo portal seguro.",
        ),
        Acao(tipo="delay", segundos=random.randint(10, 15)),
        Acao(tipo="text", conteudo="O mesmo portal seguro de antes — toca no endereço abaixo:"),
        Acao(tipo="delay", segundos=random.randint(5, 9)),
        Acao(
            tipo="text",
            conteudo=str(link).strip(),
            metadata={"skip_gancho_final": True},
        ),
        Acao(tipo="delay", segundos=random.randint(8, 12)),
        Acao(tipo="text", conteudo="Quando enviar, manda o comprovante aqui para eu registrar no altar. ✨"),
    ]

    logger.info("event=node15_honra_disparada lead=%s valor=%s", nome_fmt, p_honra)

    ctx.estado_coleta = "node15_aguardando_segunda_parcela"
    ctx.metadata = meta
    return acoes, "aguardando_pagamento_servico"
