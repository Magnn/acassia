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

def executar_v2(ctx) -> tuple:
    nome = (ctx.nome_lead or "").strip() or VOCATIVO_SEM_NOME
    meta = getattr(ctx, "metadata", {}) or {}
    voc = vocativo_cigana(nome, metadata=meta)
    genero = genero_efetivo_para_copy(nome, meta)
    meta["genero_lead"] = genero
    ctx.metadata = meta

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
        
        # Pedido de dados para o ritual
        Acao(tipo="delay", segundos=random.randint(14, 22)),
        Acao(tipo="text", conteudo="Para eu fazer a consagração perfeita e colocar o seu nome no trabalho de forma definitiva, escreva aqui o seu nome completo e a data de nascimento."),
        Acao(tipo="delay", segundos=random.randint(4, 7)),
        Acao(tipo="text", conteudo="Se houver outra pessoa no meio da história, pode incluir o nome dela também."),
        
        # Fechamento acolhedor
        Acao(tipo="delay", segundos=random.randint(8, 12)),
        Acao(tipo="text", conteudo="Estou a aguardar com todo o carinho para dar início a tudo! 🔮")
    ]
    
    logger.info("event=node14_pos_venda_ok lead=%s", nome)

    ctx.estado_coleta = "node14_pos_pagamento_boas_vindas"
    # Mantém o lead no estado de pausa "aguardando_dados_altar"
    # Isso impede que a IA interfira enquanto ele digita os dados pessoais.
    return acoes, "aguardando_dados_altar"