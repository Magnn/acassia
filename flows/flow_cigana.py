# ==========================================
# FUNIL DE VENDAS DA MEU_MISTERIO ESMERALDA (VSL Imersivo)
# Arquitetura Visual em Nó
# ==========================================

FLOW_MEU_MISTERIO = {
    "NODE_INICIAL": {
        "tipo": "roteamento",
        "acao_sucesso": "NODE_SAUDACAO"
    },
    
    # --- ETAPA 1: SAUDAÇÃO E COMPROMETIMENTO ---
    "NODE_SAUDACAO": {
        "tipo": "disparo_imediato",
        "mensagens": [
            {
                "formato": "texto", 
                "conteudo": "🔮 Olá! Senti a tua energia. Para que eu possa me conectar, preciso que me diga os nomes completos e as datas de nascimento de vocês.",
                "delay": 2
            },
            {
                "formato": "texto", 
                "conteudo": "Vou preparar o baralho enquanto você digita.",
                "delay": 4
            }
        ],
        "proximo_node": "NODE_ESPERA_DADOS"
    },
    "NODE_ESPERA_DADOS": {
        "tipo": "espera_resposta",
        "validacao": "tem_mais_de_duas_palavras",
        "mensagem_erro": "As cartas precisam de mais clareza. Por favor, digite os dados completos.",
        "acao_sucesso": "NODE_ESCOLHA_CARTAS"
    },

    # --- ETAPA 2: O RITUAL DE ESCOLHA ---
    "NODE_ESCOLHA_CARTAS": {
        "tipo": "disparo_imediato",
        "mensagens": [
            {
                "formato": "texto", 
                "conteudo": "🔮 Entrando em sintonia... Deitei o baralho na mesa.",
                "delay": 3
            },
            {
                "formato": "imagem", 
                "conteudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Tarot_cards_at_the_Museo_del_Naipe.jpg/800px-Tarot_cards_at_the_Museo_del_Naipe.jpg",
                "delay": 2
            },
            {
                "formato": "texto", 
                "conteudo": "Imagine a cena mental do que você deseja. Escolha uma das cartas e me diga apenas o número.",
                "delay": 5
            }
        ],
        "proximo_node": "NODE_ESPERA_ESCOLHA"
    },
    "NODE_ESPERA_ESCOLHA": {
        "tipo": "espera_resposta",
        "validacao": "tem_mais_de_zero_palavras", 
        "mensagem_erro": "Concentre-se e me diga apenas o número da carta que você sentiu a energia.",
        "acao_sucesso": "NODE_LEITURA_EMPATIA"
    },

    # --- ETAPA 3: LEITURA FRIA (Empatia - Gerando Valor) ---
    "NODE_LEITURA_EMPATIA": {
        "tipo": "disparo_imediato",
        "mensagens": [
            {
                "formato": "texto", 
                "conteudo": "🔮 Leitura Energética Pronta! Vou te enviar agora.",
                "delay": 2
            },
            # --- A TAG MÁGICA PARA A CARTA SORTEADA PELO MOTOR ---
            {
                "id": "dinamica_carta1", 
                "formato": "imagem", 
                "conteudo": "placeholder_url", 
                "delay": 3
            },
            {
                "formato": "texto", 
                "conteudo": "A primeira carta revela uma jornada de esforço. Vejo que você é uma pessoa de coração bom, mas que ultimamente se sente sobrecarregada.",
                "delay": 10
            },
            {
                "formato": "imagem", 
                "conteudo": "https://upload.wikimedia.org/wikipedia/commons/d/de/RWS_Tarot_06_Lovers.jpg",
                "delay": 5
            },
            {
                "formato": "texto", 
                "conteudo": "Vejo que nos seus relacionamentos, o prazer é rápido e a dor é profunda. Isso não é de agora, concorda?",
                "delay": 8
            }
        ],
        "proximo_node": "NODE_ESPERA_CONCORDANCIA"
    },
    "NODE_ESPERA_CONCORDANCIA": {
        "tipo": "espera_resposta",
        "validacao": "is_afirmacao", 
        "mensagem_erro": "Preciso que você sinta essa energia. Você concorda com o que as cartas revelaram até aqui?",
        "acao_sucesso": "NODE_REVELACAO_PROBLEMA"
    },

    # --- ETAPA 4: REVELAÇÃO DO PROBLEMA (Agitação) ---
    "NODE_REVELACAO_PROBLEMA": {
        "tipo": "disparo_imediato",
        "mensagens": [
            {
                "formato": "texto", 
                "conteudo": "🔮 Agora eu preciso falar com verdade para você.",
                "delay": 2
            },
            {
                "formato": "imagem", 
                "conteudo": "https://upload.wikimedia.org/wikipedia/commons/5/53/RWS_Tarot_16_Tower.jpg",
                "delay": 4
            },
            {
                "formato": "texto", 
                "conteudo": "O verdadeiro problema que está causando todas essas dores e travando a tua vida amorosa é uma energia negativa de inveja.",
                "delay": 10
            },
            {
                "formato": "texto", 
                "conteudo": "Não adianta tentar cancelar concorrentes, fazer simpatias leves ou apenas esperar o tempo passar. Essa energia é profunda e te acompanha.",
                "delay": 12
            },
            {
                "formato": "texto", 
                "conteudo": "Você percebe como essa trava energética está em todas as áreas da sua vida e que precisamos resolver isso na raiz?",
                "delay": 10
            }
        ],
        "proximo_node": "NODE_ESPERA_SOLUCAO"
    },
    "NODE_ESPERA_SOLUCAO": {
        "tipo": "espera_resposta",
        "validacao": "is_afirmacao", 
        "mensagem_erro": "Entenda meu anjo, essa trava está te parando. Você quer realmente resolver isso e ver a sua vida andar?",
        "acao_sucesso": "NODE_OFERTA_SOLUCAO"
    },

    # --- ETAPA 5: A OFERTA (A Solução que Funciona) ---
    "NODE_OFERTA_SOLUCAO": {
        "tipo": "disparo_imediato",
        "mensagens": [
            {
                "formato": "texto", 
                "conteudo": "A intenção desse trabalho espiritual é proteger vocês e quebrar essa trava de vez. O valor é de 180 reais, mas pelo zap faço por 120 (60 agora para os materiais).",
                "delay": 8
            },
            {
                "formato": "texto", 
                "conteudo": "💳 Link de Pagamento (R$ 60): https://seulinkaqui.com",
                "delay": 3
            },
            {
                "formato": "texto", 
                "conteudo": "Assim que fizer o pagamento, manda o comprovante aqui para mim. Tenho certeza que vamos solucionar seus problemas!",
                "delay": 5
            }
        ],
        "proximo_node": "NODE_ESPERA_PAGAMENTO"
    },
    "NODE_ESPERA_PAGAMENTO": {
        "tipo": "espera_resposta",
        "validacao": "is_pagamento", 
        "mensagem_erro": "Ainda não identifiquei o envio. Se tiver alguma dificuldade com o pagamento, me avise!",
        "acao_sucesso": "NODE_FINALIZADO"
    },
    
    # --- ETAPA FINAL ---
    "NODE_FINALIZADO": {
        "tipo": "disparo_imediato",
        "mensagens": [
            {
                "formato": "texto", 
                "conteudo": "As estrelas já traçaram o seu caminho. O trabalho está entregue nas mãos dos Guias. Aguarde os resultados com fé e luz. ✨",
                "delay": 2
            }
        ],
        "proximo_node": "FIM"
    }
}