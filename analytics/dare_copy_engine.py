"""
analytics/dare_copy_engine.py — Framework D.A.R.E (Descoberta → Ativação → Ressonância → Execução)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Motor de copy para venda fria via WhatsApp no ramo espiritual.

Inspirações técnicas:
  - Eugene Schwartz: 5 níveis de consciência → lead frio de ads entra no nível 1-2
  - Russell Brunson: Hook → Story → Offer (Epiphany Bridge)
  - Gary Halbert: Especificidade = credibilidade ("The Boron Letters")
  - Joe Sugarman: 7 gatilhos psicológicos para copy conversacional
  - Alex Hormozi: Value stack antes do preço ($100M Offers)

Uso: cada node importa as funções que precisar e injeta no system prompt do Gemini.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional


# ══════════════════════════════════════════════════════════════════════════════
# MAPA DE DESEJOS — coração do roteamento DARE
# ══════════════════════════════════════════════════════════════════════════════

DESEJO_TIPOS = ("amor", "prosperidade", "proposito", "familia", "protecao")

_DESIRE_MAP: Dict[str, Dict[str, Any]] = {
    "amor": {
        "keywords": [
            "amor", "ex", "namor", "relacion", "casamento", "separar", "solidão",
            "solidao", "sozinha", "sozinho", "voltar", "reaproxim", "saudade",
            "traição", "traicao", "parceiro", "parceira", "casar", "noivo", "noiva",
            "vínculo", "vinculo", "afeto", "rejeição", "rejeicao", "abandono",
        ],
        "medo_oculto": "ser abandonada novamente no momento em que a coisa poderia virar algo real",
        "sonho_declarado": "ter uma relação estável, onde você se sente segura e escolhida de verdade",
        "padrao_invisivel": "o ciclo de aproximação e afastamento que se repete toda vez que algo começa a ficar real",
        "nome_padrao": "Ciclo de Aproximação e Recuo",
        "hook_frio": (
            "Tem algo no padrão do que você descreveu que quase ninguém "
            "consegue ver sozinho. Posso te mostrar?"
        ),
        "revelacao_nucleo": (
            "O que acontece no seu campo afetivo não é falta de amor seu. "
            "É um padrão que opera antes mesmo de você conscientizar qualquer decisão — "
            "e ele se repete porque ainda não foi visto pela raiz."
        ),
        "urgencia_invisivel": (
            "Enquanto esse padrão não for reconhecido, ele continua se reescrevendo "
            "— com essa pessoa, ou com a próxima."
        ),
        "transicao_gap": (
            "O que acabei de te mostrar é a camada visível. "
            "A raiz é mais profunda e eu consigo lê-la. "
            "Quer que eu veja isso com você?"
        ),
        "valor_stack": [
            "leitura focada no padrão específico que identificamos",
            "identificação de onde esse ciclo tem origem no seu campo energético",
            "direção clara sobre o próximo passo — sem achismo, sem promessa falsa",
            "firmação direcionada ao que você disse que quer, não ao que 'todo mundo quer'",
            "acompanhamento enquanto o trabalho está ativo",
        ],
    },
    "prosperidade": {
        "keywords": [
            "dinheiro", "trabalho", "emprego", "renda", "venda", "financeir",
            "dívida", "divida", "prosper", "abundância", "abundancia", "grana",
            "negócio", "negocio", "empresa", "cliente", "salário", "salario",
            "investimento", "crise", "desempregad", "falência", "falencia",
        ],
        "medo_oculto": "nunca sair do lugar onde está, mesmo se esforçando mais",
        "sonho_declarado": "ter estabilidade financeira e a sensação de que o esforço está valendo",
        "padrao_invisivel": "o bloqueio que faz o dinheiro escorrer pelas mãos antes de se firmar",
        "nome_padrao": "Bloqueio de Firmação de Prosperidade",
        "hook_frio": (
            "Tem algo no que você me descreveu sobre sua situação financeira "
            "que vai além do que parece ser só 'azar'. Posso te mostrar?"
        ),
        "revelacao_nucleo": (
            "O que você está vivendo na área financeira não é incapacidade sua. "
            "É um bloqueio que opera no campo energético antes de qualquer esforço — "
            "e enquanto ele estiver ali, o esforço encontra resistência sem explicação."
        ),
        "urgencia_invisivel": (
            "Bloqueios de prosperidade não se desfazem sozinhos com o tempo. "
            "Eles se consolidam. E quanto mais tempo passa, mais difícil a abertura."
        ),
        "transicao_gap": (
            "O que te mostrei agora é a superfície. "
            "A origem do bloqueio eu consigo ver numa leitura focada. "
            "Quer que eu faça isso com você?"
        ),
        "valor_stack": [
            "leitura focada no bloqueio específico que está travando seu campo material",
            "identificação da origem energética — não é achismo, é leitura nas linhas",
            "firmação direcionada à abertura de caminhos com intenção firme",
            "orientação sobre o próximo passo concreto que favorece o movimento",
            "acompanhamento durante o período de firmação",
        ],
    },
    "proposito": {
        "keywords": [
            "propósito", "proposito", "sentido", "missão", "missao", "identidade",
            "perdida", "perdido", "vazia", "vazio", "não sei", "nao sei",
            "quem sou", "caminho", "escolha", "direção", "direcao", "angústia",
            "angustia", "espiritualidade", "despertar", "crescimento", "evolução",
            "evolucao", "transformação", "transformacao",
        ],
        "medo_oculto": "chegar ao fim sem ter descoberto quem realmente é ou para que está aqui",
        "sonho_declarado": "sentir que sua vida tem direção, que cada escolha faz sentido",
        "padrao_invisivel": "a névoa que impede você de ver com clareza qual é o próximo passo real",
        "nome_padrao": "Nevoeiro de Propósito",
        "hook_frio": (
            "O que você está descrevendo tem um nome no campo espiritual — "
            "e é mais específico do que 'fase difícil'. Posso te contar?"
        ),
        "revelacao_nucleo": (
            "A sensação de vazio ou falta de direção que você sente "
            "não é fraqueza nem falta de esforço. "
            "É o sinal de que uma parte do seu campo ainda não se alinhou "
            "com o que sua alma veio fazer aqui."
        ),
        "urgencia_invisivel": (
            "Esse nevoeiro não se dissolve sozinho com o tempo. "
            "Ele precisa ser lido e atravessado com intencionalidade."
        ),
        "transicao_gap": (
            "O que te mostrei agora é a entrada. "
            "O que está do outro lado — qual é o próximo passo real — eu consigo ver. "
            "Quer que eu leia isso com você?"
        ),
        "valor_stack": [
            "leitura focada no que está impedindo a clareza de propósito",
            "identificação do bloqueio específico no campo da direção e identidade",
            "firmação de alinhamento — não para o que 'deveria ser', mas para o que é verdadeiro em você",
            "orientação sobre o próximo passo com base no que as linhas mostram",
            "acompanhamento no período de transição",
        ],
    },
    "familia": {
        "keywords": [
            "família", "familia", "filho", "filha", "mãe", "mae", "pai", "irmão",
            "irmao", "irmã", "irma", "parente", "conflito familiar", "briga",
            "herança", "heranca", "luto", "morte", "perda", "ancestral",
            "cura familiar", "relacionamento familiar", "afastamento",
        ],
        "medo_oculto": "que o vínculo familiar esteja rompido de forma irreversível",
        "sonho_declarado": "paz e harmonia dentro da família, sem o peso que carrega hoje",
        "padrao_invisivel": "o nó ancestral que se repete de geração em geração e que chegou até você",
        "nome_padrao": "Nó de Herança Familiar",
        "hook_frio": (
            "O que você me descreveu sobre sua família carrega algo "
            "que vai além do que parece ser só desentendimento. Posso te mostrar?"
        ),
        "revelacao_nucleo": (
            "O que acontece na sua família não começa com você. "
            "Há padrões que atravessam gerações e chegam até o presente — "
            "e enquanto não forem vistos e tratados, eles continuam se expressando."
        ),
        "urgencia_invisivel": (
            "Padrões ancestrais não se resolvem com o tempo — eles se repassam. "
            "A intervenção intencional é o que quebra o ciclo."
        ),
        "transicao_gap": (
            "O que acabei de te mostrar é só a camada de cima. "
            "A origem eu consigo identificar numa leitura focada. "
            "Quer que eu veja isso com você?"
        ),
        "valor_stack": [
            "leitura focada no padrão familiar específico que identificamos",
            "identificação da origem ancestral — onde o nó se formou",
            "firmação de cura e reordenamento no campo da família",
            "orientação sobre como se posicionar dentro dessa dinâmica",
            "acompanhamento durante o processo de firmação",
        ],
    },
    "protecao": {
        "keywords": [
            "inveja", "macumba", "trabalho feito", "amarração", "olho gordo",
            "energia ruim", "perseguição", "perseguicao", "azar", "má sorte",
            "ma sorte", "tudo dá errado", "tudo da errado", "coisa ruim",
            "medo espiritual", "entidade", "assombração", "assombracao",
            "proteção espiritual", "protecao espiritual", "limpeza",
        ],
        "medo_oculto": "estar sendo alvo de algo que não consegue ver nem se defender sozinha",
        "sonho_declarado": "sentir-se protegida, com a sensação de que o caminho está livre de interferências",
        "padrao_invisivel": "a interferência energética que está criando resistência em várias áreas da sua vida ao mesmo tempo",
        "nome_padrao": "Interferência Energética Ativa",
        "hook_frio": (
            "O que você está descrevendo — várias coisas dando errado ao mesmo tempo — "
            "tem um padrão que eu consigo identificar. Posso te contar o que estou vendo?"
        ),
        "revelacao_nucleo": (
            "Quando várias áreas da vida começam a travar ao mesmo tempo, "
            "raramente é coincidência. "
            "Há algo no seu campo energético que está criando resistência — "
            "e isso tem raiz, forma e saída."
        ),
        "urgencia_invisivel": (
            "Interferências não se dissipam sozinhas. "
            "Sem tratamento intencional, elas se consolidam e se espalham."
        ),
        "transicao_gap": (
            "O que te mostrei é o que aparece na superfície. "
            "A natureza e a origem da interferência eu consigo leer numa leitura focada. "
            "Quer que eu faça isso com você?"
        ),
        "valor_stack": [
            "leitura focada no campo de proteção e identificação da interferência",
            "diagnóstico da origem — de onde vem e como opera",
            "firmação de proteção e corte da interferência com intenção direcionada",
            "orientação sobre como se blindar no cotidiano",
            "acompanhamento durante o período de firmação",
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICAÇÃO DE DESEJO
# ══════════════════════════════════════════════════════════════════════════════

def classificar_desejo_tipo(meta: Mapping[str, Any], texto_usuario: str = "") -> str:
    """
    Identifica o tipo de desejo dominante do lead.
    Prioridade: campo explícito → universo_desejo existente → análise de texto.
    Retorna uma das chaves de DESEJO_TIPOS.
    """
    # 1. Campo direto já salvo
    salvo = str(meta.get("desejo_tipo") or "").strip().lower()
    if salvo in DESEJO_TIPOS:
        return salvo

    # 2. Universo do funil legado (compatibilidade retroativa)
    uni = str(meta.get("universo_desejo") or "").strip().lower()
    _uni_map = {
        "amor_de_volta": "amor",
        "reaproximacao": "amor",
        "salvar_relacionamento": "amor",
        "superar_padrao": "amor",
        "encontrar_amor": "amor",
        "vinculo_reaproximacao": "amor",
        "vinculo_novo_amor": "amor",
        "vinculo_separacao": "amor",
        "vinculo_superar_ex": "amor",
        "vinculo_salvar_casal": "amor",
        "caminho_material": "prosperidade",
        "justica_caminho": "prosperidade",
        "protecao_interferencia": "protecao",
        "peso_emocional": "proposito",
    }
    if uni in _uni_map:
        return _uni_map[uni]

    # 3. Análise de texto (desabafo + mensagem atual)
    blob = " ".join([
        str(meta.get("desabafo_original") or ""),
        str(meta.get("resumo_dor") or ""),
        str(meta.get("desejo_declarado") or ""),
        str(meta.get("desejo_oculto") or ""),
        texto_usuario,
    ]).lower()

    scores: Dict[str, int] = {k: 0 for k in DESEJO_TIPOS}
    for tipo, dados in _DESIRE_MAP.items():
        for kw in dados["keywords"]:
            if kw in blob:
                scores[tipo] += 1

    melhor = max(scores, key=lambda k: scores[k])
    if scores[melhor] > 0:
        return melhor

    return "amor"  # default (maior volume no nicho espiritual BR)


# ══════════════════════════════════════════════════════════════════════════════
# GETTERS DO MAPA
# ══════════════════════════════════════════════════════════════════════════════

def _dados(desejo_tipo: str) -> Dict[str, Any]:
    return _DESIRE_MAP.get(desejo_tipo, _DESIRE_MAP["amor"])


def medo_oculto(desejo_tipo: str) -> str:
    return _dados(desejo_tipo)["medo_oculto"]


def sonho_declarado(desejo_tipo: str) -> str:
    return _dados(desejo_tipo)["sonho_declarado"]


def nome_padrao_invisivel(desejo_tipo: str) -> str:
    return _dados(desejo_tipo)["nome_padrao"]


# ══════════════════════════════════════════════════════════════════════════════
# FASE D — DESCOBERTA: Hook (Schwartz nível 1-2 + Brunson pattern interrupt)
# ══════════════════════════════════════════════════════════════════════════════

def hook_abertura_para_prompt(desejo_tipo: str, meta: Mapping[str, Any]) -> str:
    """
    Instrução de hook para o system prompt do Node 1.
    Lead frio de ads está no nível 1-2 de consciência (Schwartz).
    Objetivo: quebrar o padrão mental ANTES da saudação genérica.
    """
    nome = str(meta.get("nome") or "").strip()
    vocativo = nome.split()[0] if nome else ""
    dados = _dados(desejo_tipo)
    hook = dados["hook_frio"]

    base = f"""HOOK DARE — ABERTURA POR QUEBRA DE PADRÃO (Schwartz nível 1-2):
- O lead veio frio de anúncio: ainda não sabe que existe uma saída, apenas sente que algo está errado.
- NÃO comece com saudação genérica de telemarketing. Comece com presença e especificidade.
- Se o lead trouxe qualquer contexto emocional, use este hook como norte da abertura:
  "{hook}"
- Após o hook (ou após a saudação se contexto for neutro), peça o nome de forma humana.
- Objetivo deste turno: fazer o lead responder com mais de 5 palavras — primeiro micro-compromisso.
- PROIBIDO: "posso te ajudar?", "estou aqui para te atender", "fala o que você precisa"."""

    if vocativo:
        base += f"\n- Nome já coletado: use '{vocativo}' com naturalidade, não repita em todo balão."

    return base


def instrucao_diagnostico_para_prompt(desejo_tipo: str) -> str:
    """
    Instrução para o Node 3: fazer UMA pergunta de diagnóstico, não dez.
    Alinhada ao tipo de desejo já identificado ou ao mapeamento inicial.
    """
    perguntas = {
        "amor": (
            "Me conta uma coisa — essa situação que você está vivendo no campo do amor: "
            "ela está mais pesada por causa de uma pessoa específica, "
            "ou é uma sensação de solidão que não tem rosto?"
        ),
        "prosperidade": (
            "Me fala — esse peso financeiro que você está carregando: "
            "ele é mais recente, ou você sente que nunca conseguiu sair do lugar "
            "mesmo quando se esforça muito?"
        ),
        "proposito": (
            "Me conta — essa sensação de estar perdida ou sem direção: "
            "ela é mais sobre não saber o que quer, "
            "ou sobre saber mas sentir que algo sempre trava na hora de ir?"
        ),
        "familia": (
            "Me fala — esse peso que você carrega em relação à família: "
            "ele vem de uma situação específica recente, "
            "ou é algo que parece existir há muito tempo, antes mesmo de você?"
        ),
        "protecao": (
            "Me conta — essas coisas que estão dando errado: "
            "elas estão acontecendo em áreas diferentes da sua vida ao mesmo tempo, "
            "ou estão concentradas em uma área específica?"
        ),
    }
    pergunta = perguntas.get(desejo_tipo, perguntas["amor"])

    return f"""DIAGNÓSTICO DARE — UMA PERGUNTA CIRÚRGICA:
- Após coletar o desabafo inicial, faça UMA única pergunta de diagnóstico.
- Não faça lista de perguntas. Não mostre formulário. Uma pergunta, humana, específica.
- Use esta pergunta como referência (adapte ao contexto real da conversa):
  "{pergunta}"
- O objetivo é identificar a RAIZ (pessoa específica vs. padrão geral; recente vs. crônico; interno vs. externo).
- Salve a resposta no contexto — ela vai guiar toda a revelação nas próximas fases."""


# ══════════════════════════════════════════════════════════════════════════════
# FASE A — ATIVAÇÃO: Revelação do padrão invisível (Halbert especificidade)
# ══════════════════════════════════════════════════════════════════════════════

def revelacao_padrao_para_prompt(
    desejo_tipo: str,
    meta: Mapping[str, Any],
    msg_lead: str = "",
) -> str:
    """
    Instrução para Node 5/6: revelar o padrão invisível com especificidade (Halbert).
    Cria o momento 'ela me viu' — lead pensa: como ela sabe?
    """
    dados = _dados(desejo_tipo)
    padrao = dados["padrao_invisivel"]
    revelacao = dados["revelacao_nucleo"]
    urgencia = dados["urgencia_invisivel"]

    # Extrair especificidades do lead para injetar na revelação (Halbert)
    nome_pessoa = str(meta.get("nome_pessoa_envolvida") or "").strip()
    tempo = str(meta.get("tempo_exato") or "").strip()
    dor = str(meta.get("resumo_dor") or meta.get("desabafo_original") or "")[:200].strip()

    especificidade = ""
    if nome_pessoa and nome_pessoa.upper() not in ("INDEFINIDO", "INDEFINIDA", "N/A"):
        primeiro = nome_pessoa.split()[0]
        especificidade += f"\n- Há uma pessoa específica envolvida ({primeiro}): use o nome naturalmente, sem julgamento."
    if tempo and tempo.upper() not in ("INDEFINIDO", "N/A"):
        especificidade += f"\n- O lead carrega esse peso há {tempo}: isso é dado concreto — use, não ignore."
    if dor:
        especificidade += f"\n- Dor declarada em palavras do lead: '{dor[:120]}' — espelhe isso de volta, elevado."

    return f"""REVELAÇÃO DO PADRÃO INVISÍVEL (Halbert — especificidade cria credibilidade):

PADRÃO A NOMEAR: "{padrao}"

NÚCLEO DA REVELAÇÃO (adapte com as palavras reais do lead, não use igual):
"{revelacao}"

URGÊNCIA DO INVISÍVEL (use no final da revelação, suave mas firme):
"{urgencia}"

REGRAS DE HALBERT (obrigatórias neste turno):
- Quanto mais específico, mais parece leitura real. Genérico = robô.
- Repita as PALAVRAS EXATAS do lead, elevadas — não parafraseie com sinônimos bonitos.
- O lead deve ler e pensar: "como ela sabe exatamente isso?"
- NÃO invente fatos que o lead não disse. Especificidade vem do que ele trouxe.
{especificidade}

PROIBIDO neste turno:
- Ir direto para a oferta. A revelação precede a transição.
- Elogio genérico ("você é forte", "parabéns por buscar ajuda").
- Texto que poderia se encaixar em qualquer pessoa (efeito Barnum)."""


# ══════════════════════════════════════════════════════════════════════════════
# FASE R — RESSONÂNCIA: Espelho elevado + Sugarman 7 gatilhos
# ══════════════════════════════════════════════════════════════════════════════

_SUGARMAN_TRIGGERS = {
    "esperanca": "Existe uma saída que você ainda não conseguiu ver — e ela é mais simples do que o peso que você está carregando.",
    "curiosidade": "Há algo no fundo desse padrão que quase ninguém alcança sozinho. É o que eu consigo ver.",
    "exclusividade": "Não é toda conversa que chega ao ponto que chegamos aqui. O que aparece pra mim no seu caso é específico.",
    "autoridade": "Já vi esse padrão em centenas de pessoas. Ele tem nome, tem raiz, e tem saída.",
    "espelho": "[USE AS PALAVRAS EXATAS DO LEAD, elevadas — o que ela disse, dito de volta com mais profundidade]",
    "inimigo_externo": "O problema não é você. É um padrão que opera fora do alcance da sua consciência — por isso o esforço sozinho não resolve.",
    "pertencimento": "Você não está passando por isso por acaso. As pessoas que chegam até aqui geralmente estão no limite de um ciclo que está pedindo fechamento.",
}

def ressonancia_para_prompt(desejo_tipo: str, meta: Mapping[str, Any]) -> str:
    """
    Instrução para Node 7: criar o pico de ressonância emocional antes da transição para oferta.
    Usa os 7 gatilhos de Sugarman + espelho de Halbert.
    """
    dados = _dados(desejo_tipo)
    medo = dados["medo_oculto"]
    sonho = dados["sonho_declarado"]

    # Selecionar 3-4 gatilhos relevantes para este turno
    gatilhos_ativos = ["espelho", "inimigo_externo", "esperanca", "autoridade"]
    gatilhos_str = "\n".join(
        f"  • {g.upper()}: {_SUGARMAN_TRIGGERS[g]}"
        for g in gatilhos_ativos
    )

    return f"""RESSONÂNCIA DARE — PICO EMOCIONAL ANTES DA TRANSIÇÃO (Sugarman + Halbert):

OBJETIVO DESTE TURNO: fazer o lead sentir "ela me entendeu de verdade" — não convencer, ressoar.

MEDO OCULTO QUE NÃO FOI DITO (não verbalize diretamente, mas honre):
"{medo}"

SONHO QUE O LEAD CARREGA (norte da copy de ressonância):
"{sonho}"

GATILHOS ATIVOS NESTE TURNO (use 2-3, não todos de uma vez):
{gatilhos_str}

ESTRUTURA DOS BLOCOS:
1. Bloco espelho: repita o que o lead disse, com mais precisão do que ele conseguiu dizer.
2. Bloco inimigo externo: o padrão não é fraqueza dele — é algo que opera antes da consciência.
3. Bloco esperança específica: não "vai melhorar" genérico — o que especificamente pode mudar.
4. Bloco autoridade + gap: "O que te mostrei é a superfície. A raiz eu consigo ver."

TRANSIÇÃO PARA OFERTA (último bloco deste turno — não pule):
- Crie o gap de curiosidade: "o que te mostrei é menos de 20% do que eu consigo ver"
- Convite de baixo atrito: "quer que eu veja a raiz disso com você?"
- NÃO revele o preço aqui. NÃO faça pitch aqui. Apenas o convite.

PROIBIDO:
- Oferta antecipada neste turno.
- Frase genérica que qualquer pessoa poderia receber.
- Tom de motivacional ("você consegue!", "acredite em você")."""


# ══════════════════════════════════════════════════════════════════════════════
# FASE E — EXECUÇÃO: Oferta DARE + Hormozi value stack
# ══════════════════════════════════════════════════════════════════════════════

def oferta_dare_para_prompt(
    desejo_tipo: str,
    meta: Mapping[str, Any],
    preco_mat: str = "65",
    preco_serv: str = "65",
) -> str:
    """
    Instrução para Node 8: oferta personalizada por desejo_tipo com value stack (Hormozi).
    A oferta surge como consequência natural do que o lead disse, não como pitch.
    """
    dados = _dados(desejo_tipo)
    nome_padrao = dados["nome_padrao"]
    valor_stack = dados["valor_stack"]
    sonho = dados["sonho_declarado"]

    nome_lead = str(meta.get("nome") or "").strip()
    vocativo = nome_lead.split()[0] if nome_lead else "você"
    dor = str(meta.get("resumo_dor") or "")[:180].strip()
    nome_pessoa = str(meta.get("nome_pessoa_envolvida") or "").strip()

    contexto_especifico = ""
    if dor:
        contexto_especifico += f"\n- Dor declarada: '{dor}' — a oferta deve soar como solução exata para isso, não para 'todo mundo'."
    if nome_pessoa and nome_pessoa.upper() not in ("INDEFINIDO", "N/A"):
        primeiro = nome_pessoa.split()[0]
        contexto_especifico += f"\n- Pessoa envolvida: {primeiro} — a firmação é direcionada a esse vínculo específico."

    stack_str = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(valor_stack))

    return f"""OFERTA DARE — CONSEQUÊNCIA NATURAL, NÃO PITCH (Hormozi value stack):

PRINCÍPIO: A oferta não aparece do nada. Ela surge como o próximo passo lógico
do que já foi revelado. O lead deve pensar: "seria irracional não continuar."

DESEJO_TIPO identificado: {desejo_tipo.upper()}
PADRÃO NOMEADO no turno anterior: "{nome_padrao}"
SONHO QUE A OFERTA SERVE: "{sonho}"
{contexto_especifico}

VALUE STACK (Hormozi — construir valor ANTES de revelar preço):
{stack_str}

ESTRUTURA DA OFERTA (ordem obrigatória):
1. TRANSIÇÃO: retome o que foi revelado — "então, {vocativo}, o que identificamos aqui é..."
2. NOMEAR O TRABALHO: "Vou fazer uma [nome específico do trabalho] com você."
   — Use o nome_mecanismo já definido em turnos anteriores.
3. VALUE STACK: descreva o que está incluído de forma humana (não lista de supermercado).
4. PONTE DO SONHO: conecte o trabalho ao que o lead disse que quer — nas palavras dele.
5. PREÇO: "São R$ {preco_mat} para os materiais do trabalho."
   "A segunda parte (honorário) você paga depois de sentir o resultado nas mãos — são mais R$ {preco_serv}."
6. CTA DE BAIXO ATRITO: "Se quiser avançar, me manda um 'quero' que te passo o próximo passo."

REGRAS DE HORMOZI (obrigatórias):
- O preço aparece DEPOIS do value stack — nunca antes.
- Cada item do stack deve soar como algo de alto valor que justifica o investimento.
- Não descontar sem que o lead peça. Preço é ancoragem — não se desculpe por ele.
- A oferta não convence pelo argumento — convence porque o lead se vê dentro do que foi descrito.

PROIBIDO:
- "Tenho uma promoção especial só hoje."
- "Todo mundo que fez isso..."
- Tom de urgência artificial.
- Descrever o trabalho de forma genérica ("uma leitura"). Seja específico ao desejo_tipo.
- Prometer resultado garantido ou prazo certo."""


# ══════════════════════════════════════════════════════════════════════════════
# INTENSIDADE DE RESSONÂNCIA — Gatilho para timing da oferta
# ══════════════════════════════════════════════════════════════════════════════

def calcular_intensidade_ressonancia(meta: Mapping[str, Any], historico_recente: str = "") -> str:
    """
    Estima se o lead atingiu ressonância suficiente para receber a oferta.
    Retorna: "baixa", "media" ou "alta".

    Alta = pronto para oferta.
    Média = precisa mais de um turno de ressonância.
    Baixa = ainda na fase de descoberta/ativação.
    """
    score = 0

    # Sinal de engajamento
    eng = float(meta.get("score_engajamento") or 0.5)
    if eng >= 0.75:
        score += 3
    elif eng >= 0.55:
        score += 1

    # Dados coletados (desabafo, dor, desejo)
    if meta.get("desabafo_recebido"):
        score += 2
    if meta.get("resumo_dor") or meta.get("desejo_declarado"):
        score += 2
    if meta.get("desejo_tipo"):
        score += 1

    # Sinais no histórico recente (palavras que indicam receptividade)
    blob = historico_recente.lower()
    sinais_positivos = [
        "é exatamente", "é isso", "como você sabe", "parece que me conhece",
        "como assim", "continua", "me conta mais", "quero saber",
        "verdade", "é verdade", "perfeito", "sim", "nossa", "uau", "uau",
    ]
    for sinal in sinais_positivos:
        if sinal in blob:
            score += 1

    # Nó atual indica que fases anteriores foram concluídas
    node = str(meta.get("node_atual") or "").lower()
    if "7" in node or "interesse" in node or "desejo" in node:
        score += 2

    if score >= 8:
        return "alta"
    if score >= 4:
        return "media"
    return "baixa"


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO UNIFICADA — gera todo o contexto DARE para um node de uma vez
# ══════════════════════════════════════════════════════════════════════════════

def contexto_dare_para_prompt(
    fase: str,
    meta: Mapping[str, Any],
    msg_lead: str = "",
    preco_mat: str = "65",
    preco_serv: str = "65",
) -> str:
    """
    Ponto de entrada único para qualquer node.

    fase: "hook" | "diagnostico" | "revelacao" | "ressonancia" | "oferta"
    Retorna string pronta para injeção no system prompt do Gemini.
    """
    desejo_tipo = classificar_desejo_tipo(meta, msg_lead)

    # Salvar classificação no meta para downstream (quando meta for mutável)
    if isinstance(meta, dict) and not meta.get("desejo_tipo"):
        meta["desejo_tipo"] = desejo_tipo

    if fase == "hook":
        return hook_abertura_para_prompt(desejo_tipo, meta)
    if fase == "diagnostico":
        return instrucao_diagnostico_para_prompt(desejo_tipo)
    if fase == "revelacao":
        return revelacao_padrao_para_prompt(desejo_tipo, meta, msg_lead)
    if fase == "ressonancia":
        return ressonancia_para_prompt(desejo_tipo, meta)
    if fase == "oferta":
        return oferta_dare_para_prompt(desejo_tipo, meta, preco_mat, preco_serv)

    return ""
