"""
flows/fase_4_entrega/node_16_downsell.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOWNSELL ESTRATÉGICO — MASTER SUPREMA v1.0

PROPÓSITO:
  Recuperar leads que não pagaram R$60. 
  Oferece R$30 (metade) em materiais, com o restante pago pós-resultado.
"""

import logging
import random
from schema import Acao
from copy_sanitizer import genero_efetivo_para_copy, nome_lead_para_exibicao, vocativo_cigana
from flows.funnel_gates import VOCATIVO_SEM_NOME

logger = logging.getLogger(__name__)

def executar_v2(ctx) -> tuple:
    nome = (ctx.nome_lead or "").strip() or VOCATIVO_SEM_NOME
    nome_fmt = nome_lead_para_exibicao(nome)
    
    meta = getattr(ctx, "metadata", {}) or {}
    msg_lead = str(getattr(ctx, "texto_recebido", "") or "").strip()
    meta["genero_lead"] = genero_efetivo_para_copy(nome, meta, texto_discurso=msg_lead or None)
    voc = vocativo_cigana(nome, metadata=meta)
    config = meta.get("__config__", {})
    # Aqui você deve configurar um link de checkout de R$30 no seu .env se desejar automação total
    link_downsell = config.get("link_downsell", config.get("link_pagamento", "[LINK]"))

    acoes = [
        Acao(tipo="delay", segundos=random.randint(8, 12)),
        Acao(tipo="text", conteudo=f"{voc}, eu tenho uma ótima notícia para você... 🕯️"),
        
        Acao(tipo="delay", segundos=random.randint(15, 25)),
        Acao(tipo="text", conteudo="Eu sei que muitas vezes o que nos trava é a parte financeira, e eu não quero que você perca a sua chance de libertação por causa disso."),
        
        Acao(tipo="delay", segundos=random.randint(12, 18)),
        Acao(tipo="text", conteudo="Conversei com o meu fornecedor agora pouco. Ele autorizou eu preparar o seu material por apenas R$ 30,00... metade do valor que lhe passei antes!"),

        Acao(tipo="delay", segundos=random.randint(15, 22)),
        Acao(tipo="text", conteudo="A outra metade você paga junto com o meu serviço, só quando já estiver colhendo os seus resultados. Fiz isto porque acredito de verdade na sua transformação."),

        Acao(tipo="delay", segundos=random.randint(10, 15)),
        Acao(
            tipo="text",
            conteudo="Se couber no seu bolso agora, o caminho do material reduzido é este — toca no link abaixo:",
        ),
        Acao(tipo="delay", segundos=random.randint(5, 9)),
        Acao(
            tipo="text",
            conteudo=str(link_downsell).strip(),
            metadata={"skip_gancho_final": True},
        ),
        
        Acao(tipo="delay", segundos=random.randint(8, 12)),
        Acao(tipo="text", conteudo="Assim que concluir, mande-me o comprovante para eu liberar os seus materiais imediatamente! ✨"),
    ]
    
    logger.info(f"📉 [DOWNSELL] Oferta de R$30 enviada para {nome_fmt}.")
    ctx.metadata = meta
    return acoes, "aguardando_pagamento_downsell"