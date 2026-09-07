"""
MEU_MISTERIO ESMERALDA — Constituição de copy (lógica de persuasão + universos).
Injetada nos nodes 6–8. Prazos do playbook NÃO vão ao prompt como promessa (compliance).
"""

from __future__ import annotations

import re
from typing import Any, Mapping

# ── Filosofia (síntese v1.0) ────────────────────────────────────────────────
FILOSOFIA_CENTRAL_RESUMO = """
CONSTITUIÇÃO DE COPY (internalizar, não recitar em bloco):
1) O lead sente DOR; o que vende é revelar o PROBLEMA (causa no plano que ela não nomeou) — sem humilhar.
2) Pontos lógicos: partir do que ela JÁ ACREDITA → ~80% conhecido + ~20% novo → conclusão: só o caminho espiritual nomeado fecha o ciclo.
3) Em cada apertura emocional: funcional (o que acontece) → dimensional (no dia a dia) → emocional (como ela se sente).
4) Story Brand negativo: externo (sintoma) + interno (vergonha/medo) + filosófico (por que isso não deveria ser com ela).
5) O mecanismo nomeado ancora leitura → agitação → oferta (uma linha só; não dispersar).
6) Urgência real = intensidade × frequência do padrão e janela da conversa — sem timer falso nem “últimas vagas”.
7) Mini-transações: atenção → visualização → credibilidade → autoridade → mecanismo → solução → oferta (se uma falha, a próxima sofre).
"""

INSTRUCAO_PONTOS_LOGICOS_RESUMO = """
PONTOS LÓGICOS (Thiago Filemon — esqueleto):
- Abra com o que ela JÁ ACREDITA (primeiro “sim” fácil). Depois encadeie: afirmação → prova (metáfora, lógica, “você mesma percebe quando…”) → consequência (funcional + dimensional + emocional).
- A “virada” (novo) vem após 2–3 passos de acordo; não estique afirmação ousada sem prova.
- Provas fortes para público espiritual: autoridade de tradição, padrão observável na vida dela, analogia (“é como…”), sem listar rótulos vazios.
"""

INSTRUCAO_LEITURA_12_BLOCOS = """
MAPEAMENTO CONSTITUIÇÃO → 12 BLOCOS (Node 6):
- B1–B2: saúde do esforço + contraste emocional (sem solução cedo) — primeiro SIM.
- B3: interrupção / mudança de ritmo (curto, suspense).
- B4–B8: núcleo do “problema criado” + pontos lógicos (espalhe P1→P5+; use dados dela). Diagnóstico firme, causa invisível, injustiça.
- B9: tentativas que ela já fez (eco do histórico) + por que não seguraram no plano certo.
- B10–B11: potencial represado + ponte de esperança (sem prometer resultado garantido).
- B12: XEQUE-MATE (pergunta forte com ?) — obrigatório.
"""

INSTRUCAO_AGITACAO_7_BLOCOS = """
MAPEAMENTO AGITAÇÃO (constituição 9 batidas → 7 BLOCOS do Node 7):
- B1: reação REAL à última mensagem do lead (confirmou, duvidou, empolgou).
- B2: transferência de culpa / alívio (o que pesa não é “falta de força” dela).
- B3: sangramento — padrão vaza para outras áreas (externo + interno + filosófico), sem terrorismo.
- B4: MECANISMO com nome EXATO do system + por que é diferente do que ela tentou (pontos lógicos rápidos).
- B5: desqualificação empática das tentativas passadas (validar esforço → atacar só o plano errado).
- B6: autoridade + prova (e depoimento se o roteiro mandar).
- B7: permissão para explicar valores / próximo passo (micro-compromisso), alinhado à janela da conversa — sem urgência falsa.
"""

INSTRUCAO_OFERTA_NODE8 = """
OFERTA (Node 8 — princípios constitucionais adaptados ao sistema atual):
- Preço: use SÓ os números e a lógica R$ já dados no prompt (âncora, total, Cakto). Não invente outros valores.
- Mini-transações nos 9 blocos: confiança → resultado desejado → contraste → mecanismo nomeado → valor (como já fixado) → decisão honesta → Cakto → comprovante/altar → CTA + FIRMO (link vem depois; não colar URL).
- Ancoragem: relate custo de continuar no ciclo; sem humilhar.
- Urgência: janela espiritual da conversa / honestidade — PROIBIDO escassez inventada e prazo mágico garantido.
- Últimos blocos continuam com calor (não fechar seco).
"""

ERROS_PROIBIDOS_RESUMO = """
ERROS QUE QUEBRAM A LINHA (evitar):
- Problema genérico (“você tem problema amoroso”) em vez de problema criado específico.
- Mecanismo sem nome ou trocar o nome do system por outro.
- Pontos lógicos em lista desconexa (tem que soar conversa).
- Ignorar a última resposta do lead no B1 da agitação.
- Desqualificar o que ela tentou sem empatia.
- Prazo ou resultado garantido (dias fixos, “vai voltar certeza”).
- Nome do lead esquecido: use com naturalidade nos blocos (sem exagero vs regra do node).
"""

# Chaves = universo_desejo do funil (+ justica para texto misto)
UNIVERSOS_COPY: dict[str, dict[str, Any]] = {
    "amor_de_volta": {
        "dor_conhecida": "a separação e a saudade de quem ela ama",
        "problema_criado": (
            "não é a falta de amor — é uma âncora energética que foi formada entre vocês "
            "e está repelindo ativamente qualquer tentativa de reconexão. "
            "Quanto mais você tenta forçar o reencontro, mais essa âncora se aperta. "
            "Por isso nada que você tentou funcionou — você estava atacando o sintoma, "
            "não a raiz."
        ),
        "por_que_falhou": (
            "esperar o tempo, mandar mensagem, tentar conversa, pedir explicação — "
            "tudo isso não toca o plano energético onde o bloqueio realmente está. "
            "É como tentar varrer sujeira do chão sem ver que o vento continua jogando mais."
        ),
        "crenca_final_a_instalar": (
            "Só o desmanche dessa âncora no plano espiritual pode liberar "
            "o caminho para o reencontro real. Sem isso, qualquer tentativa no plano físico "
            "vai continuar encontrando a mesma parede invisível."
        ),
        "pontos_logicos": [
            "Você sabe que quando dois corações se conectaram de verdade, esse fio não desaparece — ele pode ficar invisível, mas continua lá.",
            "Toda separação tem uma causa energética antes de ter uma causa física. Algo cria distância no plano espiritual antes de qualquer discussão ou afastamento.",
            "Esse algo tem um nome no mundo espiritual: âncora de separação. Ela se forma nos momentos de conflito intenso e passa a repelir ativamente qualquer aproximação.",
            "Por isso quanto mais você tenta se aproximar, mais a situação piora. Não é rejeição — é a âncora respondendo ao estímulo.",
            "E por isso nada que você tentou no plano físico funcionou. Conversa, distância, mensagem, conselho de amiga — nenhum deles toca onde o bloqueio realmente está.",
            "A única forma de desfazer isso é agir diretamente sobre a âncora espiritual — dissolve-la antes que ela se torne permanente.",
        ],
        "objecao_principal": (
            "Não importa se a pessoa te bloqueou, está com outra, ou mora em outro estado. "
            "A distância física não existe no plano espiritual. O trabalho age diretamente na âncora."
        ),
    },
    "superar_padrao": {
        "dor_conhecida": "a dificuldade de soltar e seguir em frente, a sensação de estar presa",
        "problema_criado": (
            "não é fraqueza emocional — é um vínculo que prende sua energia a essa pessoa "
            "ou padrão. Esse vínculo atua como um imã invertido: sempre que você tenta avançar, "
            "ele te puxa de volta. Por isso você repete os mesmos ciclos mesmo quando racionalmente "
            "já sabe que quer ir embora."
        ),
        "por_que_falhou": (
            "terapia, força de vontade, distância física, novas amizades — "
            "tudo isso trabalha no nível do comportamento. O vínculo está no nível mais profundo do padrão. "
            "Você não vai desfazer com esforço o que foi criado no plano espiritual."
        ),
        "crenca_final_a_instalar": (
            "O ciclo só vai quebrar quando o vínculo for trabalhado na raiz. "
            "Sem isso, o campo energético continua atraindo o mesmo padrão, independente "
            "do esforço consciente."
        ),
        "pontos_logicos": [
            "Você já sabe que padrões se repetem. Mesmo quando você muda o cenário, a mesma dinâmica aparece — pessoa diferente, mesma dor.",
            "Isso não é coincidência e não é falha de caráter. É o campo energético se comportando como foi programado.",
            "Essa programação tem uma origem: vínculos formados em relações onde houve entrega profunda e ruptura dolorosa.",
            "Esses vínculos funcionam como cordas invisíveis que te conectam ao passado. Sempre que você tenta avançar, eles puxam de volta.",
            "Por isso força de vontade e terapia têm limite. Eles trabalham no consciente — o nó está mais fundo.",
            "Desatar essa corda é o caminho. E isso se faz no plano energético, não só no plano da mente.",
        ],
        "objecao_principal": (
            "Não importa há quanto tempo esse padrão se repete, ou quantas vezes você já tentou. "
            "Quando a âncora do padrão é trabalhada, o campo se libera — e começa a atrair diferente."
        ),
    },
    "encontrar_amor": {
        "dor_conhecida": "a solidão e o desejo de encontrar um amor verdadeiro",
        "problema_criado": (
            "não é falta de oportunidade ou de sorte — é um bloqueio no campo amoroso "
            "que está funcionando como um escudo invisível. Esse escudo afasta as pessoas certas "
            "antes mesmo de qualquer contato real. Por isso você encontra mas não conecta, "
            "ou conecta mas a pessoa some sem explicação."
        ),
        "por_que_falhou": (
            "aplicativos, festas, apresentações de amigos — tudo isso são canais físicos. "
            "O bloqueio está no campo energético que você projeta. Enquanto ele estiver ativo, "
            "mesmo a pessoa certa vai sentir algo que a afasta sem saber explicar por quê."
        ),
        "crenca_final_a_instalar": (
            "Amor não se encontra — se atrai. E a atração depende do campo energético estar limpo "
            "e aberto. Esse bloqueio precisa ser removido primeiro para que qualquer tentativa "
            "no plano físico tenha resultado real."
        ),
        "pontos_logicos": [
            "Você sabe que amor real não depende só de estar no lugar certo na hora certa.",
            "Cada pessoa emite uma frequência energética. Essa frequência é o que atrai ou repele antes de qualquer palavra ser dita.",
            "Quando há um bloqueio no campo amoroso, essa frequência está distorcida — e atrai o errado ou afasta o certo.",
            "Esse bloqueio se forma em momentos de dor profunda: decepções, traições, término que não foi superado completamente.",
            "Por isso os aplicativos e as festas não resolvem sozinhos. O problema não é só onde você está procurando — é o sinal que você está emitindo.",
            "Quando o campo se abre, a vida tende a encaixar pessoas diferentes — porque a frequência muda.",
        ],
        "objecao_principal": (
            "Não importa há quanto tempo você está só, ou como está sua vida agora. "
            "Quando a barreira energética é trabalhada, o campo se abre — e as coisas começam a mudar."
        ),
    },
    "salvar_relacionamento": {
        "dor_conhecida": "o afastamento, as brigas, a sensação de que o amor está acabando",
        "problema_criado": (
            "não é só incompatibilidade — pode haver uma energia externa na relação "
            "criando distância artificial. Inveja de fora, olho gordo, ou desequilíbrio vibracional entre os dois. "
            "Isso explica brigas por coisas pequenas e afastamento que cresce sem motivo claro."
        ),
        "por_que_falhou": (
            "conversar, tentar dar mais atenção, mudar hábitos — tudo isso são tentativas "
            "no plano físico. O que pesa no campo do casal muitas vezes não se remove só com diálogo. "
            "Precisa neutralizar espiritualmente o que entrou entre vocês."
        ),
        "crenca_final_a_instalar": (
            "O amor ainda pode estar lá — sufocado por interferência. "
            "Remover essa camada é o que permite reconexão sem o mesmo peso."
        ),
        "pontos_logicos": [
            "Você sabe que quando duas pessoas se amam de verdade, o amor não some do dia pra noite sem motivo.",
            "Toda relação tem um campo energético compartilhado. Quando esse campo é invadido, o casal sente atrito sem explicação lógica.",
            "Esse atrito vira discussão por detalhe, afastamento, estranhamento.",
            "Por isso às vezes a conversa não segura. Vocês chegam perto e algo desfaz. Não é sempre falta de amor — é interferência.",
            "A forma de restaurar é limpar esse campo e blindar a relação espiritualmente.",
            "O trabalho age na causa, não no sintoma do dia."
        ],
        "objecao_principal": (
            "Não importa o quanto o afastamento avançou. "
            "O trabalho age na causa raiz — não no sintoma."
        ),
    },
    "prosperidade": {
        "dor_conhecida": "dificuldade financeira, dívidas, dinheiro que nunca sobra",
        "problema_criado": (
            "não é falta de esforço nem má administração — é um bloqueio de prosperidade "
            "que está impedindo o dinheiro de entrar e ficar. Esse bloqueio funciona como "
            "uma parede invisível: você trabalha, recebe, mas o dinheiro escoa."
        ),
        "por_que_falhou": (
            "organização financeira, novos empregos, empréstimos — tudo isso são soluções "
            "no plano físico para um problema que também tem camada energética. "
            "Enquanto o bloqueio estiver ativo, mais dinheiro pode significar mais que some."
        ),
        "crenca_final_a_instalar": (
            "Prosperidade não é só trabalho duro — é o campo alinhado "
            "para receber e reter. O bloqueio precisa ser trabalhado para o esforço "
            "se converter em resultado que fica."
        ),
        "pontos_logicos": [
            "Você sabe que tem gente que trabalha menos e sobra mais — e outra que se mata e não sobra nada.",
            "Isso não é só sorte. É o campo de cada um respondendo diferente.",
            "Quando há bloqueio, a energia do dinheiro não fixa. Circula e escoa.",
            "Esse bloqueio pode vir de mau-olhado, humilhação financeira passada, ou crença de merecimento.",
            "Por isso organização e esforço têm teto. Você tenta encher um balde com buraco.",
            "Fechar o buraco na raiz é o que permite reter."
        ],
        "objecao_principal": (
            "Não importa o tamanho da dívida ou há quanto tempo está nessa situação. "
            "O trabalho vai na raiz energética — não nos sintomas financeiros."
        ),
    },
    "familia_cura": {
        "dor_conhecida": "conflito familiar, distância afetiva, problema de saúde na família",
        "problema_criado": (
            "não é falta de amor nem má vontade — pode haver uma ferida ancestral atuando "
            "no núcleo familiar. Padrões de conflito, doenças recorrentes, afastamentos sem motivo "
            "claro — sintomas de energia que vem de mais longe que qualquer briga recente."
        ),
        "por_que_falhou": (
            "conversas, desculpas, tentativas de reaproximação — movimentos "
            "no presente para uma ferida que vem do passado. Sem tratar a raiz, "
            "os padrões se repetem."
        ),
        "crenca_final_a_instalar": (
            "Famílias carregam padrões por gerações. Trabalhar o vínculo na raiz "
            "permite novos padrões — harmonia, proteção, respiro."
        ),
        "pontos_logicos": [
            "Você sabe que algumas famílias carregam um peso que se repete de geração em geração.",
            "Esse peso é padrão energético — ferida que não foi curada e se manifesta de novo.",
            "Conflitos que voltam, doenças recorrentes, afastamento sem motivo claro — sintomas disso.",
            "Conversa sozinha não resolve se o padrão não é só pessoal — é energético e antigo.",
            "Intervenção no plano espiritual é o que muda o padrão de fundo.",
            "Quando a ferida é tratada, o núcleo começa a respirar diferente."
        ],
        "objecao_principal": (
            "Não importa o quanto o conflito avançou ou se a pessoa está distante. "
            "No plano espiritual não há barreira de distância como no físico."
        ),
    },
    "justica": {
        "dor_conhecida": "peso em torno de processo, causa ou decisão na justiça",
        "problema_criado": (
            "não é só papel faltando — é um travamento no campo da justiça e da clareza "
            "que mantém você girando em volta do mesmo medo, da mesma espera, do mesmo desgaste "
            "enquanto a vida cobra por fora."
        ),
        "por_que_falhou": (
            "só advogado, só esperar, só reunir documento — importante no físico, "
            "mas quando o campo está emaranhado, a causa não anda com a leveza que deveria "
            "e você sente que algo invisível puxa para trás."
        ),
        "crenca_final_a_instalar": (
            "Alinhar o campo espiritual ao que você busca na justiça abre espaço para clareza e caminho — "
            "sem prometer sentença nem resultado garantido."
        ),
        "pontos_logicos": [
            "Você sabe que causas demoram e desgastam mesmo quando você faz a parte certa.",
            "Esse desgaste não é só burocracia — é peso acumulado no peito, noite mal dormida, medo de perder.",
            "O plano físico e o emocional ficam presos um ao outro.",
            "Quando o campo se organiza espiritualmente, você para de lutar sozinha só no papel.",
            "O trabalho favorece clareza e caminho — não substitui advogado nem decisão de juiz.",
            "É firmação séria voltada ao que você quer ver resolvido."
        ],
        "objecao_principal": (
            "Não importa em que fase está o processo. O trabalho age na camada energética — "
            "sem garantir ganho de causa."
        ),
    },
    "geral": {
        "dor_conhecida": "algo que está travado e não consegue resolver",
        "problema_criado": (
            "não é falta de esforço — é uma obstrução energética que está "
            "bloqueando o fluxo natural da sua vida. Cada área travada é um sintoma "
            "dessa obstrução maior."
        ),
        "por_que_falhou": "tentativas no plano físico para um problema que também tem camada espiritual",
        "crenca_final_a_instalar": (
            "Existe uma causa energética por trás de cada travamento. "
            "Trabalhar essa causa é o que libera o fluxo de volta."
        ),
        "pontos_logicos": [
            "Você sabe que às vezes parece que algo invisível trabalha contra você.",
            "Não é só coincidência. É padrão — bloqueio que se instalou e afeta várias áreas.",
            "Esse bloqueio se manifesta como obstáculo no pior momento.",
            "Por isso o esforço tem limite. Você empurra uma porta trancada do outro lado.",
            "A chave está no plano espiritual — não só no físico.",
            "Quando o bloqueio é trabalhado, o que estava represado começa a fluir."
        ],
        "objecao_principal": "Não importa há quanto tempo está assim — o bloqueio pode ser trabalhado com honestidade.",
    },
}

REGRAS_CETICISMO: dict[str, dict[str, str]] = {
    "baixo": {
        "tom": "fluido, místico, caloroso; prova por autoridade e histórias; ritmo pode ser mais pausado.",
        "mecanismo": "pode usar linguagem mais esotérica com naturalidade.",
    },
    "medio": {
        "tom": "equilíbrio entre místico e observacional; mix de prova lógica + espiritual.",
        "mecanismo": "explicar simples, sem empilhar rótulos.",
    },
    "alto": {
        "tom": "concreto, observacional, menos floreio; mais direto.",
        "mecanismo": "causa e efeito claros; dados dela obrigatórios nos blocos centrais da leitura.",
    },
}


def _universo_chave(meta: Mapping[str, Any]) -> str:
    u = str(meta.get("universo_desejo") or "geral").strip().lower()
    if u in UNIVERSOS_COPY:
        return u
    blob = " ".join(
        str(meta.get(k) or "")
        for k in ("desabafo_original", "desejo_declarado", "resumo_dor", "dor_central")
    ).lower()
    if re.search(
        r"justi[cç]a|processo|advogad|judicial|tribunal|\bvara\b|ação judicial|acao judicial|processo\s+civil",
        blob,
    ):
        return "justica"
    return "geral"


def constituicao_universo_para_prompt(meta: Mapping[str, Any], mecanismo_sistema: str) -> str:
    """Camada narrativa do universo; nome do ritual = sempre o do sistema."""
    key = _universo_chave(meta)
    pack = UNIVERSOS_COPY[key]
    pl = pack.get("pontos_logicos") or []
    if isinstance(pl, str):
        pl = [pl]
    pts = "\n".join(f"  {i + 1}. {p}" for i, p in enumerate(pl))
    mec = (mecanismo_sistema or "").strip()
    return f"""UNIVERSO DE COPY ({key}) — narrativa de “problema criado” (sem prometer prazo nem resultado garantido):
- Dor que o lead já sente: {pack["dor_conhecida"]}
- Problema / leitura (causa que ela não nomeou): {pack["problema_criado"]}
- Por que o que tentou não segurou sozinho: {pack["por_que_falhou"]}
- Objeção típica (neutralizar com empatia): {pack["objecao_principal"]}
- Crença a instalar (sem milagre garantido): {pack["crenca_final_a_instalar"]}
- Pontos lógicos sugeridos (conversação, não lista seca):
{pts}
- Nome oficial do trabalho NESTE FUNIL (usar ao citar o ritual): «{mec}». A narrativa acima explica o porquê; não troque esse nome."""


def constituicao_ceticismo_para_prompt(meta: Mapping[str, Any]) -> str:
    raw = str(meta.get("ceticismo_lead") or "medio").strip().lower()
    if raw not in REGRAS_CETICISMO:
        raw = "medio"
    r = REGRAS_CETICISMO[raw]
    return f"CETICISMO DO LEAD ({raw}): {r['tom']} | Mecanismo: {r['mecanismo']}"


def camada_constituicao_node6(meta: Mapping[str, Any], nome_mecanismo: str) -> str:
    return "\n\n".join(
        [
            FILOSOFIA_CENTRAL_RESUMO.strip(),
            INSTRUCAO_PONTOS_LOGICOS_RESUMO.strip(),
            constituicao_universo_para_prompt(meta, nome_mecanismo),
            INSTRUCAO_LEITURA_12_BLOCOS.strip(),
            constituicao_ceticismo_para_prompt(meta),
            ERROS_PROIBIDOS_RESUMO.strip(),
        ]
    )


def camada_constituicao_node7(meta: Mapping[str, Any], mecanismo: str) -> str:
    return "\n\n".join(
        [
            FILOSOFIA_CENTRAL_RESUMO.strip(),
            constituicao_universo_para_prompt(meta, mecanismo),
            INSTRUCAO_AGITACAO_7_BLOCOS.strip(),
            constituicao_ceticismo_para_prompt(meta),
            ERROS_PROIBIDOS_RESUMO.strip(),
        ]
    )


def camada_constituicao_node8(meta: Mapping[str, Any], mecanismo: str) -> str:
    return "\n\n".join(
        [
            FILOSOFIA_CENTRAL_RESUMO.strip(),
            constituicao_universo_para_prompt(meta, mecanismo),
            INSTRUCAO_OFERTA_NODE8.strip(),
            constituicao_ceticismo_para_prompt(meta),
            ERROS_PROIBIDOS_RESUMO.strip(),
        ]
    )
