"""
flows/fase_4_entrega/node_14_confirmacao_entrega.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PÓS-VENDA E BOAS VINDAS — MASTER SUPREMA v2.0

Este node é o "tapete vermelho" da Cigana. É disparado 
automaticamente pelo engine.py quando o webhook do Cakto 
confirma que o pagamento foi concluído.

MELHORIAS APLICADAS:
🔥 FIX CIRCULAR: Importação segura via schema.py.
🔥 DELAYS DINÂMICOS: random.randint para simular a preparação mística real.
🔥 RITUAL DE BOAS-VINDAS: Pacing fragmentado para aumentar a percepção de valor.
"""

import logging
import random
from schema import Acao  # 🚨 FIX CIRCULAR: Importação centralizada para estabilidade
from copy_sanitizer import genero_efetivo_para_copy, vocativo_cigana
from flows.funnel_gates import VOCATIVO_SEM_NOME

logger = logging.getLogger(__name__)


def _pergunta_dados_altar(voc: str) -> str:
    opcoes = [
        f"Para eu fazer a consagração com precisão, {voc}, me envia seu nome completo e data de nascimento?",
        f"{voc}, para eu fechar seu altar do jeito certo, me manda seu nome completo e sua data de nascimento?",
        f"Me confirma aqui, {voc}: qual seu nome completo e sua data de nascimento para eu iniciar agora?",
    ]
    return random.choice(opcoes)


def executar_v2(ctx) -> tuple:
    nome = (ctx.nome_lead or "").strip() or VOCATIVO_SEM_NOME
    meta = getattr(ctx, "metadata", {}) or {}
    voc = vocativo_cigana(nome, metadata=meta)
    genero = genero_efetivo_para_copy(nome, meta)
    meta["genero_lead"] = genero
    ctx.metadata = meta
    desejo = str(meta.get("desejo_declarado") or meta.get("desejo_oculto") or "").strip()
    dor = str(meta.get("resumo_dor") or "").strip()
    eco_ctx = ""
    if desejo:
        eco_ctx = f"Eu mantenho firme aqui o seu pedido de {desejo[:90]}."
    elif dor:
        eco_ctx = f"Eu estou cuidando com atenção desse ponto que você trouxe: {dor[:110]}."

    acoes = [
        # Reação imediata à vibração do altar
        Acao(tipo="delay", segundos=random.randint(6, 10)),
        Acao(
            tipo="text",
            conteudo=f"{voc}... o meu altar acabou de vibrar agora mesmo. O sistema avisou-me que a sua firmação foi concluída com sucesso! 🙏",
        ),
        Acao(tipo="delay", segundos=random.randint(3, 6)),
        Acao(tipo="text", conteudo="Sinto o peso a levantar daqui. ✨"),
        
        # Transição para o compromisso assumido
        Acao(tipo="delay", segundos=random.randint(12, 18)),
        Acao(tipo="text", conteudo="A partir deste exato momento, o seu caminho está oficialmente cruzado com o meu. O seu trabalho já entrou na minha fila de prioridades sagradas."),
        
        # Simulação de ação física (separar materiais)
        Acao(tipo="delay", segundos=random.randint(10, 15)),
        Acao(tipo="text", conteudo="Vou separar agora mesmo todos os materiais que lhe mostrei e começar a sua preparação energética individual."),
        *(
            [
                Acao(tipo="delay", segundos=random.randint(6, 10)),
                Acao(tipo="text", conteudo=eco_ctx),
            ]
            if eco_ctx
            else []
        ),
        
        # Pedido de dados para o ritual
        Acao(tipo="delay", segundos=random.randint(14, 22)),
        Acao(
            tipo="text",
            conteudo=_pergunta_dados_altar(voc),
            metadata={"skip_gancho_final": True},
        ),
        Acao(tipo="delay", segundos=random.randint(4, 7)),
        Acao(
            tipo="text",
            conteudo="Se houver outra pessoa no meio da história, pode incluir o nome dela também.",
            metadata={"skip_gancho_final": True},
        ),
    ]

    total_textos = sum(1 for a in acoes if getattr(a, "tipo", "") == "text")
    total_delays = sum(int(getattr(a, "segundos", 0) or 0) for a in acoes if getattr(a, "tipo", "") == "delay")
    logger.info(
        "event=node14_pos_venda_ok lead=%s textos=%s delay_total_s=%s",
        nome,
        total_textos,
        total_delays,
    )

    ctx.estado_coleta = "node14_pos_pagamento_boas_vindas"
    # Mantém o lead no estado de pausa "aguardando_dados_altar"
    # Isso impede que a IA interfira enquanto ele digita os dados pessoais.
    return acoes, "aguardando_dados_altar"