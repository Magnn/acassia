"""
flows/fase_3_oferta/node_9_recuperacao.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECUPERAÇÃO DE GHOSTING — MASTER SUPREMA v4.0

PROPÓSITO:
Resgatar leads que silenciaram após receber a oferta.
Lógica de Pacing de Ouro para simular preocupação e misticismo real.

MELHORIAS:
🔥 FIX CIRCULAR: Importação segura via schema.py.
🔥 DELAYS DINÂMICOS: random.randint + cálculo de digitação humana.
🔥 INTEGRAÇÃO MAESTRO: Reancoragem profunda na dor e no gatilho do lead.
🔥 ZERO HARDCODE: Preços e links lidos da configuração centralizada.
"""

import logging
import random
from schema import Acao
from copy_sanitizer import (
    frase_dor_contextualizada,
    genero_efetivo_para_copy,
    nome_lead_para_exibicao,
    resumo_dor_para_copy,
    resolver_gatilho_emocional,
    vocativo_cigana,
    preparar_texto_envio,
)

logger = logging.getLogger(__name__)


def _calcular_delay_humano(texto: str) -> int:
    """Simula o tempo de digitação de uma pessoa real (aprox. 12 caracteres por segundo)."""
    if not texto:
        return 6
    tempo = len(texto) // 12
    return max(7, min(tempo, 15))


def executar_v2(ctx, tentativa: int = 1) -> tuple:
    # 1. Resgate de Inteligência (Dados do Maestro - Node 5)
    metadata = getattr(ctx, "metadata", {}) or {}
    nome = (ctx.nome_lead or "meu bem").strip() or "meu bem"
    nome_fmt = nome_lead_para_exibicao(nome)
    msg_ctx = str(getattr(ctx, "texto_recebido", "") or "").strip()
    metadata["genero_lead"] = genero_efetivo_para_copy(
        nome, metadata, texto_discurso=msg_ctx or None
    )
    dor_real = resumo_dor_para_copy(
        str(metadata.get("resumo_dor") or "essa situação que carrega no peito"),
        max_len=90,
    )
    dor_ctx = frase_dor_contextualizada(dor_real, abertura="quando você traz")
    gatilho = resolver_gatilho_emocional(metadata)
    gatilho = preparar_texto_envio(gatilho, "node9_gatilho").strip() or "essa trava"
    
    # Configurações Dinâmicas
    config = metadata.get("__config__", {})
    preco_mat = config.get("preco_materiais", "60")
    link_pagamento = metadata.get("link_pagamento", config.get("link_pagamento", "[LINK]"))

    acoes = []

    if tentativa == 1:
        # --- TENTATIVA 1: O Check-in de Alma (30-60 min depois) ---
        txt1 = f"{nome_fmt}..."
        txt2 = "Você ainda está por aqui? Vi que ficou em silêncio e passei pra te acompanhar. 🕯️"
        txt3 = "Às vezes a correria corta o ritmo mesmo. Se travou em alguma parte, eu te guio passo a passo."
        txt4 = f"Tua foto ainda está aqui comigo. Não quero que você perca esse momento por causa de {gatilho}."

        acoes += [
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(tipo="text", conteudo=txt1),
            Acao(tipo="delay", segundos=random.randint(5, 8)),
            Acao(tipo="text", conteudo=txt2),
            Acao(tipo="delay", segundos=_calcular_delay_humano(txt3)),
            Acao(tipo="text", conteudo=txt3),
            Acao(tipo="delay", segundos=_calcular_delay_humano(txt4)),
            Acao(tipo="text", conteudo=txt4),
            Acao(tipo="delay", segundos=random.randint(8, 12)),
            Acao(tipo="text", conteudo="Se tiver qualquer dúvida antes de firmar, me fala em uma frase que eu te ajudo."),
        ]
        proximo_node = "aguardando_pagamento"

    elif tentativa == 2:
        # --- TENTATIVA 2: Urgência da Fenda (Mística) ---
        txt_u1 = f"{nome_fmt}, vou ser direta com você: o momento bom que abriu na leitura vai diminuindo com o tempo."
        txt_u2 = "Se a gente não fechar esse passo agora, a energia perde força e volta a ficar pesado."
        
        acoes += [
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(tipo="text", conteudo=txt_u1),
            Acao(tipo="delay", segundos=random.randint(10, 15)),
            Acao(tipo="text", conteudo=txt_u2),
            Acao(tipo="delay", segundos=random.randint(12, 18)),
            Acao(tipo="text", conteudo=f"Ainda vejo que, {dor_ctx}, isso segue te travando. Se fizer sentido pra você, o caminho ainda está aberto."),
            Acao(tipo="delay", segundos=random.randint(8, 12)),
            Acao(
                tipo="text",
                conteudo=f"O link ainda está ativo para a sua firmação de R$ {preco_mat}. Toca no endereço abaixo para abrir no celular:",
            ),
            Acao(tipo="delay", segundos=random.randint(5, 9)),
            Acao(
                tipo="text",
                conteudo=str(link_pagamento).strip(),
                metadata={"skip_gancho_final": True},
            ),
        ]
        proximo_node = "aguardando_pagamento"

    elif tentativa == 3:
        # --- TENTATIVA 3: fechamento sem desconto nem desespero ---
        voc = vocativo_cigana(nome, metadata=metadata)
        txt_f1 = f"{voc}, eu vou recolher seu nome do altar por agora para abrir espaço aos próximos atendimentos."
        txt_f2 = f"Sinto que, {dor_ctx}, isso ainda pesa aí dentro."

        acoes += [
            Acao(tipo="delay", segundos=random.randint(8, 12)),
            Acao(tipo="text", conteudo=txt_f1),
            Acao(tipo="delay", segundos=random.randint(12, 18)),
            Acao(tipo="text", conteudo=txt_f2),
            Acao(tipo="delay", segundos=random.randint(10, 15)),
            Acao(tipo="text", conteudo="Se quiser retomar depois, me chama com calma. Sem pressão, só clareza."),
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(
                tipo="text",
                conteudo=str(link_pagamento).strip(),
                metadata={"skip_gancho_final": True},
            ),
            Acao(tipo="delay", segundos=random.randint(8, 12)),
            Acao(tipo="text", conteudo="Que a luz te encontre. Fique em paz. ✨"),
        ]
        proximo_node = "fluxo_encerrado"

    else:
        return [Acao(tipo="delay", segundos=1)], "fluxo_encerrado"

    ctx.estado_coleta = f"node9_recuperacao_t{tentativa}"
    ctx.metadata = metadata
    logger.info("event=node9_recuperacao tentativa=%s lead=%s", tentativa, nome_fmt)
    return acoes, proximo_node