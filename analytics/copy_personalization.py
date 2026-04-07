"""
Heurísticas de copy personalizada (sem LLM extra): perfil de tom, nome do trabalho espiritual,
entregáveis da oferta para injeção em prompts dos nodes 6–8.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional

_DEFAULT_MECANISMO = "Trabalho de Firmação e Resgate nas Linhas"


def perfil_copy_para_prompt(meta: Mapping[str, Any], msg_lead: str) -> str:
    """
    Descreve o perfil em linguagem natural para o system prompt (adaptação de tom).
    """
    obj = str(meta.get("objecao_silenciosa") or "").strip().lower()
    energia = str(meta.get("nivel_energia") or "").strip().lower()
    ml = (msg_lead or "").strip().lower()

    partes: list[str] = []
    if any(x in ml for x in ("golpe", "enganado", "enganada", "desconfio", "desconfiança", "desconfianca", "funciona de verdade", "é verdade")):
        partes.append("Lead com ceticismo ou medo de golpe: acolha sem debater, seja transparente, sem prometer milagre.")
    elif "medo" in obj or "desconf" in obj:
        partes.append("Objeção silenciosa ligada a medo ou desconfiança: validar e explicar com calma.")
    if energia in ("ansioso", "alto", "esgotado"):
        partes.append("Energia acelerada ou esgotada: frases mais curtas, menos rodeio, mais presença.")
    else:
        partes.append("Ritmo solene e pausado, como leitura de mesa.")

    arq = str(meta.get("arquetipo_lead") or "").strip()
    if arq and arq.lower() not in ("o ferido", "ferido"):
        partes.append(f"Arquétipo percebido: {arq}.")

    return " ".join(partes) if partes else "Tom padrão: acolhimento firme, sem telemarketing."


def norte_editorial_venda_fria_direta_para_prompt() -> str:
    """
    Constituição de copy para agitação (Node 7) e oferta (Node 8):
    fio único comercial no WhatsApp, alinhado a venda direta inbound (produto = trabalho nomeado).
    Complementa `contexto_desejo_resultado_para_prompt` sem repetir as mesmas proibições.
    """
    return """NORTE EDITORIAL — VENDA FRIA DIRETA NO ZAP (não perder a linha):
- **Produto em cena**: o trabalho de firmação já nomeado no prompt é o que está à venda; a copy sustenta esse produto até o próximo passo (permissão, valores ou FIRMO), não vira aula genérica, terapia solta ou "texto que não leva a lugar nenhum".
- **Um fio só**: identificação com o que o lead disse → tensão honesta → mecanismo nomeado → (neste nó) fechamento conforme o roteiro. Cada bloco avança o argumento; proibido repetir a mesma ideia em blocos seguidos (parece robô e estoura a linha).
- **Continuidade**: ecoar dor, pessoa ou situação que já entraram na conversa; se a resposta soar genérica demais ou como "outro atendimento", falhou.
- **Desvio do lead**: no máximo uma frase curta de ponte e retome o roteiro comercial desta etapa.
- Tom: direto, adulto, autoridade de quem fecha no WhatsApp; pele de leitura/mesa, sem prolixidade nem segundo grande tema existencial."""


def _clip_txt(s: Any, max_len: int) -> str:
    t = str(s or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


def _montar_blob_mecanismo(meta: Mapping[str, Any], dor_safe: str) -> str:
    partes = [
        str(dor_safe or ""),
        str(meta.get("universo_desejo") or ""),
        str(meta.get("desejo_declarado") or ""),
        str(meta.get("desejo_oculto") or ""),
        str(meta.get("resumo_dor") or ""),
        str(meta.get("desabafo_original") or "")[:2200],
    ]
    return " ".join(partes).lower()


def _blob_tem_justica(blob: str) -> bool:
    return any(
        w in blob
        for w in (
            "justiça",
            "justica",
            "processo",
            "advogad",
            "audiência",
            "audiencia",
            "ação judicial",
            "acao judicial",
            "vara",
            "tribunal",
            "civil",
            "criminal",
            "inventário",
            "inventario",
        )
    )


def _blob_tem_contexto_afetivo(blob: str) -> bool:
    return any(
        w in blob
        for w in (
            "amor",
            "ex",
            "namor",
            "casar",
            "relacion",
            "trai",
            "marido",
            "esposa",
            "esposo",
            "sumiu",
            "casamento",
            "cônjuge",
            "conjuge",
            "divórcio",
            "divorcio",
            "divorciar",
            "separar",
            "separação",
            "separacao",
            "superar",
            "noivo",
            "noiva",
            "união estável",
            "uniao estavel",
        )
    )


def _classificar_vinculo_afetivo(blob: str, meta: Mapping[str, Any]) -> str:
    """
    Distingue o que a pessoa quer no campo afetivo (não assumir só 'volta do ex').
    Ordem: separação > novo amor > superar ex > salvar casal (universo) > reaproximação default.
    """
    # --- separar do cônjuge / encerrar vínculo conjugal
    sep_forte = (
        "separar",
        "separação",
        "separacao",
        "divórcio",
        "divorcio",
        "divorciar",
        "terminar o casamento",
        "terminar casamento",
        "acabar o casamento",
        "acabar casamento",
        "fim do casamento",
        "sair do casamento",
        "quero divorciar",
        "pedir divórcio",
        "pedir divorcio",
        "largar meu marido",
        "largar minha esposa",
        "largar o marido",
        "largar a esposa",
        "largar meu esposo",
        "não aguento mais casada",
        "nao aguento mais casada",
        "não aguento mais casado",
        "nao aguento mais casado",
    )
    if any(k in blob for k in sep_forte) or (
        any(k in blob for k in ("cônjuge", "conjuge", "marido", "esposa", "esposo", "casamento"))
        and any(k in blob for k in ("separar", "separação", "divorc", "terminar", "largar", "sair do", "fim do"))
    ):
        return "vinculo_separacao"

    # --- encontrar um amor / novo vínculo
    novo_amor_kw = (
        "novo amor",
        "outro amor",
        "encontrar alguém",
        "encontrar alguem",
        "encontrar um amor",
        "conhecer alguém",
        "conhecer alguem",
        "namorar de novo",
        "arrumar um namorado",
        "arrumar uma namorada",
        "arrumar namorad",
        "próximo amor",
        "proximo amor",
        "recomeçar amor",
        "recomecar amor",
        "alguém novo",
        "alguem novo",
        "encontrar o amor",
        "quero namorar",
        "quero um namorado",
        "quero uma namorada",
        "cupido",
    )
    if any(k in blob for k in novo_amor_kw):
        return "vinculo_novo_amor"

    # --- superar ex / fechar ciclo (não reaproximação)
    superar_kw = (
        "superar",
        "esquecer ele",
        "esquecer ela",
        "esquecer o ex",
        "esquecer a ex",
        "esquecer minha ex",
        "esquecer meu ex",
        "seguir em frente",
        "tirar da cabeça",
        "tirar ele da cabeça",
        "tirar ela da cabeça",
        "libertar disso",
        "cortar o laço",
        "cortar laco",
        "não quero voltar",
        "nao quero voltar",
        "não quero ele de volta",
        "não quero ela de volta",
        "nao quero ele de volta",
        "nao quero ela de volta",
        "largar esse sentimento",
        "superar a saudade",
        "apagar da vida",
        "tirar do coração",
    )
    if any(k in blob for k in superar_kw):
        return "vinculo_superar_ex"

    uni = str(meta.get("universo_desejo") or "").strip().lower()
    if uni == "encontrar_amor":
        return "vinculo_novo_amor"
    if uni == "superar_padrao":
        return "vinculo_superar_ex"
    if uni == "salvar_relacionamento":
        return "vinculo_salvar_casal"
    if uni == "amor_de_volta":
        return "vinculo_reaproximacao"

    # --- default afetivo: reaproximar / trazer de volta / vínculo em aberto
    return "vinculo_reaproximacao"


def _resolver_tema_mecanismo(meta: Mapping[str, Any], dor_safe: str) -> str:
    blob = _montar_blob_mecanismo(meta, dor_safe)
    if _blob_tem_justica(blob):
        return "justica_caminho"
    if _blob_tem_contexto_afetivo(blob):
        return _classificar_vinculo_afetivo(blob, meta)
    if any(
        w in blob
        for w in ("dinheiro", "trabalho", "emprego", "venda", "financeir", "dívida", "divida", "prosper")
    ):
        return "caminho_material"
    if any(w in blob for w in ("inveja", "família", "familia", "macumba", "olho", "energia ruim")):
        return "protecao_interferencia"
    if any(w in blob for w in ("ansiedade", "medo", "depress", "insônia", "insonia", "não durmo", "nao durmo")):
        return "peso_emocional"
    return "geral"


def nome_mecanismo_sugerido(meta: Mapping[str, Any], dor_safe: str) -> str:
    """
    Nome único e memorável para o trabalho, derivado do contexto (sem inventar fatos novos).
    """
    tema = _resolver_tema_mecanismo(meta, dor_safe)

    if tema == "vinculo_reaproximacao":
        base = "Firmação para Aproximação no Vínculo e Resgate nas Linhas"
    elif tema == "vinculo_separacao":
        base = "Firmação de Desligamento Honroso e Clareza no Vínculo Conjugal"
    elif tema == "vinculo_novo_amor":
        base = "Firmação para Abrir Caminho ao Novo Amor"
    elif tema == "vinculo_superar_ex":
        base = "Firmação de Liberação Afetiva e Corte do Laço no Peito"
    elif tema == "vinculo_salvar_casal":
        base = "Firmação para Reordenar e Fortalecer o Vínculo a Dois"
    elif tema == "justica_caminho":
        base = "Firmação de Caminho e Clareza na Justiça"
    elif tema == "caminho_material":
        base = "Abertura de Caminhos e Firmação de Prosperidade"
    elif tema == "protecao_interferencia":
        base = "Trabalho de Proteção e Corte de Interferência"
    elif tema == "peso_emocional":
        base = "Firmação de Alívio e Ancoragem nas Linhas"
    else:
        base = _DEFAULT_MECANISMO

    pe = str(meta.get("nome_pessoa_envolvida") or "").strip()
    if pe and pe.upper() not in ("INDEFINIDO", "INDEFINIDA", "N/A") and len(pe) <= 36:
        primeiro = re.split(r"\s+", pe)[0]
        if len(primeiro) >= 2:
            return f"{base} — eixo {primeiro}"

    return base


def definir_nome_mecanismo_se_generico(meta: Dict[str, Any], dor_safe: str) -> str:
    """
    Garante `nome_mecanismo` não genérico quando ainda não foi batizado pela IA em node anterior.
    Retorna o valor final usado nos prompts.
    """
    cur = (meta.get("nome_mecanismo") or "").strip()
    if cur and cur != _DEFAULT_MECANISMO:
        return cur
    novo = nome_mecanismo_sugerido(meta, dor_safe)
    meta["nome_mecanismo"] = novo
    return novo


def contexto_desejo_resultado_para_prompt(meta: Mapping[str, Any], mecanismo: str) -> str:
    """
    Instruções para nodes 7–8: vender o que a pessoa QUER (resultado declarado),
    sem sermão de \"o que precisa\", e sem promessa de milagre ou resultado garantido.
    """
    decl = _clip_txt(meta.get("desejo_declarado"), 320)
    oculto = _clip_txt(meta.get("desejo_oculto"), 240)
    uni = str(meta.get("universo_desejo") or "").strip()
    partes_dados: list[str] = []
    if decl:
        partes_dados.append(f"- O que o lead já verbalizou que quer (use como bússola da oferta): {decl}")
    if oculto and oculto.lower() not in (decl[:120].lower() if decl else ""):
        partes_dados.append(f"- Fio emocional / desejo (Hive Mind, Node 5): {oculto}")
    if uni and uni.lower() not in ("", "geral"):
        partes_dados.append(f"- Universo do funil: {uni}")
    bloco = "\n".join(partes_dados) if partes_dados else (
        "- Não há trecho salvo explícito: infira o que a pessoa busca só a partir da dor, "
        "nomes, tempo, gatilho e mensagens já listados acima — mesmo assim, fale na chave do RESULTADO desejado, não de \"lição\"."
    )
    mec = (mecanismo or _DEFAULT_MECANISMO).strip()
    return f"""RESULTADO QUE A PESSOA QUER (as pessoas compram o que desejam, não o que alguém acha que \"precisam\" ouvir):
{bloco}

POSICIONAMENTO (obrigatório):
- O trabalho «{mec}» e toda a sequência devem soar como caminho de firmação **em direção ao que ela já disse que quer**. Exemplos de norte (use o que bate com o texto dela, sem misturar desejos opostos):
  • **Reaproximação**: trazer de volta / reatar com a pessoa citada.
  • **Separar do cônjuge**: encerrar ou afastar o vínculo conjugal com clareza e honra (não empurrar volta se ela pediu saída).
  • **Superar o ex**: fechar ciclo, tirar peso do peito, seguir sem prometer que fulano volta.
  • **Novo amor**: abrir caminho para outro vínculo, sem julgar o passado.
  • **Salvar o casal** (quando for o caso): fortalecer/reordenar o vínculo a dois, não confundir com \"trazer ex de anos atrás\" se ela falou em casamento atual.
  • **Justiça / material**: como já combinado nos blocos anteriores (clareza na causa, caminhos, etc.).
- PROIBIDO assumir que \"todo mundo quer o amor de volta\": se ela pediu separação, superação ou alguém novo, a copy **acompanha esse desejo**.
- PROIBIDO tom de convencimento moral: \"você precisa entender\", \"o que você precisa é\", \"antes de tudo você tem que\". Substitua por respeito ao desejo dela e clareza do que o ritual **favorece intencionalmente**.
- PROIBIDO: milagre, garantia de resultado externo, prazo certo (\"em X dias volta\", \"divórcio sai na hora\"), \"vai ganhar o processo com certeza\", \"fulano volta garantido\", \"vai aparecer um amor perfeito amanhã\".
- PERMITIDO: deixar claro que o trabalho é feito com intenção firme **voltada ao que ela busca**, acompanhamento honesto, e abertura de caminho/espiritualidade sem engodo."""


def entregaveis_oferta_para_prompt(config: Mapping[str, Any]) -> str:
    """
    Lista de entregáveis embalada para o prompt do node 8 (sem PII).
    """
    p_mat = str(config.get("preco_materiais") or "65").strip()
    p_serv = str(config.get("preco_servico") or "65").strip()
    return (
        "ENTREGÁVEIS (obrigatório citar de forma humana, não como lista de supermercado): "
        f"1) Primeira parte (ato de fé / materiais do trabalho) R$ {p_mat}. "
        f"2) Segunda parte (honorário após você sentir resultado nas mãos) R$ {p_serv}. "
        "3) Acompanhamento operacional: registro do seu nome no altar, envio de foto da firmação quando aplicável, "
        "e leitura do comprovante para iniciar o ritual com segurança."
    )


def instrucao_ancoragem_node6(
    nome_pessoa_envolvida: str,
    tempo_exato: str,
    evento_gatilho: str,
) -> str:
    """
    Instruções explícitas para a IA não fazer leitura genérica quando há dados.
    """
    partes: list[str] = []
    te = (tempo_exato or "").strip()
    eg = (evento_gatilho or "").strip()
    np = (nome_pessoa_envolvida or "").strip()

    indef = frozenset({"", "indefinido", "indefinida", "n/a", "none"})

    if te and te.upper() not in indef:
        partes.append(f"inclua o tempo citado pelo lead ({te}) em pelo menos dois blocos, de forma natural")
    if eg and eg.upper() not in indef:
        partes.append(f"inclua o gatilho/evento ({eg}) em pelo menos um bloco, sem dramatizar demais")
    if np and np.upper() not in indef:
        partes.append(f"quando falar de vínculo ou terceiro, use o nome citado ({np.split()[0]}) com respeito, sem julgar")

    if not partes:
        return "Se não houver dados específicos de terceiro/tempo/gatilho, não invente: ancora só na dor resumida e no que o lead já disse."

    return "ANCORAGEM OBRIGATÓRIA: " + "; ".join(partes) + "."


def instrucao_eco_esforco_concreto(meta: Mapping[str, Any]) -> str:
    """
    Força eco de lugares/rotinas que o lead citou (prova de escuta), sem Barnum.
    """
    blob = " ".join(
        str(x or "").strip()
        for x in (
            meta.get("desabafo_original"),
            meta.get("contexto_extra_final"),
            meta.get("node3_percepcoes_multas"),
        )
        if x
    ).lower()
    if len(blob) < 30:
        return ""
    # Palavras que costumam vir em “o que já tentei” (amor / vida social)
    alvo = re.findall(
        r"\b(pra[çc]as?|praça|parques?|restaurantes?|eventos?|baladas?|"
        r"igrejas?|academias?|apps?|tinders?|terapias?|viaj\w*|trabalhos?|"
        r"festas?|shows?|cinema|barz?|clubes?)\b",
        blob,
        re.I,
    )
    if not alvo:
        return ""
    uniq = []
    for w in alvo:
        wl = w.lower()
        if wl not in uniq:
            uniq.append(wl)
        if len(uniq) >= 5:
            break
    amostra = ", ".join(uniq)
    return (
        "ECO_DE_ESFORÇO (obrigatório se acima fizer sentido): o lead descreveu tentativas reais. "
        f"Em pelo menos um bloco, cite de forma natural elementos como ({amostra}) "
        "mostrando que ela saiu, tentou, e o vazio ou o padrão voltou. "
        "Não troque isso por frase genérica tipo 'lugares' ou 'saía para sair'."
    )
