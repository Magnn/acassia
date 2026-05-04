"""
flows/fase_3_oferta/node_8_oferta_principal.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OFERTA PRINCIPAL — v25 (oferta no desejo declarado; sem milagre garantido; Cakto, FIRMO antes do link)

Fase 1: copy completa sem URL; último balão pede FIRMO (skip gancho automático).
Fase 2 (mesmo node, próxima mensagem): só envia o link compacto após confirmação.
"""

import logging
import re
import random
from typing import Optional

from schema import Acao
from api.cakto_api import CaktoAPIClient
from copy_sanitizer import (
    MOBILE_CHARS_POR_LINHA,
    MOBILE_MAX_LINHAS_BALO,
    aplicar_substituicoes_proibidas,
    compactar_url_https_monolitica,
    contexto_lead_para_nodes,
    extrair_blocos_fallback,
    fatiar_texto_ritmo_celular,
    frase_dor_contextualizada,
    genero_efetivo_para_copy,
    genero_hint_para_prompt,
    historico_limpo_para_ia,
    limpar_colagem_primeira_msg_whatsapp_em_texto,
    normalizar_enxerto_dor_sem_contexto,
    normalizar_link_para_envio,
    parse_blocos_leitura_ia,
    remover_marcadores_bloco_ia_vazados,
    sufixo_ancoras_node3_para_prompt,
    unificar_vocativos_por_genero,
)
from analytics.copy_constituicao_meumisterio import camada_constituicao_node8
from conversation_policy import lead_reportou_problema_entrega
from analytics.copy_personalization import (
    contexto_desejo_resultado_para_prompt,
    definir_nome_mecanismo_se_generico,
    entregaveis_oferta_para_prompt,
    instrucao_ancoragem_node6,
    instrucao_eco_esforco_concreto,
    norte_editorial_venda_fria_direta_para_prompt,
    perfil_copy_para_prompt,
)
from analytics.dare_copy_engine import (
    classificar_desejo_tipo,
    oferta_dare_para_prompt,
    calcular_intensidade_ressonancia,
    nome_padrao_invisivel,
)

logger = logging.getLogger(__name__)

_INDICES_AUDIO = {2, 5, 7}
_INDICES_IMPACTO = {4, 6, 8}
_CAKTO_CLIENT_CACHE: dict[str, CaktoAPIClient] = {}
_RE_PROBLEMA_ENTREGA = re.compile(
    r"(?i)(mensagem\s+cortad|t[aá]\s+atropel|n[aã]o\s+deu\s+tempo|"
    r"n[aã]o\s+deu\s+pra\s+ver|n[aã]o\s+carreg|travou|bugou)"
)
def _bloco_e_somente_link(texto: str) -> bool:
    t = (texto or "").strip()
    if not t:
        return False
    t = re.sub(r"[\s🔗🔒📎]+", "", t)
    return t.startswith("http://") or t.startswith("https://")


def _delay_digitacao(texto: str, eh_audio: bool = False, energia: str = "Baixa") -> int:
    if not texto:
        return 8
    base_fator = 14 if eh_audio else 18
    fator = base_fator - 3 if energia == "Ansioso" else base_fator
    return max(10, min(len(str(texto)) // fator, 32))


def _cadencia_oferta(num_bloco: int, delay_pre: int, pausa_pos: int, score: float) -> tuple[int, int]:
    """
    Cadência emocional da oferta:
    - antes do valor (bloco 5) e no CTA final (bloco 9), pausa maior de assimilação;
    - lead mais engajado recebe ritmo levemente mais ágil, sem perder solenidade.
    """
    s = max(0.0, min(score, 1.0))
    pre = delay_pre
    pos = pausa_pos

    if num_bloco in (5, 9):
        pre += 4
        pos += 6
    elif num_bloco in (3, 4, 6):
        pos += 2

    if s >= 0.75:
        pre = max(8, pre - 2)
        pos = max(6, pos - 1)
    elif s <= 0.35:
        pre += 2
        pos += 2

    return pre, pos


def _normalizar_link_checkout(link: str) -> str:
    s = (link or "").strip()
    if not s or s.startswith("["):
        return s
    norm = normalizar_link_para_envio(s, instagram_mode=False)
    return norm or "[LINK_NÃO_CONFIGURADO]"


def _link_checkout_valido(link: str) -> bool:
    s = re.sub(r"\s+", "", str(link or "")).strip()
    if not s:
        return False
    if "[" in s or "]" in s or "{" in s or "}" in s or "<" in s or ">" in s:
        return False
    low = s.lower()
    if "nao_configurado" in low or "não_configurado" in low:
        return False
    return low.startswith("https://") or low.startswith("http://")


def _cakto_client_from_config(config: dict) -> Optional[CaktoAPIClient]:
    ck = (config or {}).get("cakto") or {}
    if not isinstance(ck, dict):
        return None
    if not ck.get("enabled"):
        return None
    key = f"{ck.get('base_url','')}|{ck.get('client_id','')}"
    cli = _CAKTO_CLIENT_CACHE.get(key)
    if cli:
        return cli
    cli = CaktoAPIClient(
        base_url=str(ck.get("base_url") or "https://api.cakto.com.br"),
        client_id=str(ck.get("client_id") or ""),
        client_secret=str(ck.get("client_secret") or ""),
    )
    _CAKTO_CLIENT_CACHE[key] = cli
    return cli


def _resolver_link_checkout_dinamico(meta: dict, config: dict, link_fallback: str) -> str:
    # Cache por lead para não chamar API repetidamente na mesma jornada.
    cached = normalizar_link_para_envio(str(meta.get("node8_checkout_link") or ""), instagram_mode=False)
    if cached:
        return cached
    ck = (config or {}).get("cakto") or {}
    cli = _cakto_client_from_config(config)
    if not cli:
        return link_fallback
    try:
        link_api = cli.resolve_checkout_url(
            offer_id=str(ck.get("offer_id") or ""),
            offer_slug=str(ck.get("offer_slug") or ""),
        )
        if link_api:
            meta["node8_checkout_link"] = link_api
            return link_api
    except Exception as e:
        logger.warning("⚠️ [NODE 8] Cakto checkout dinâmico indisponível: %s", e)
    return link_fallback


def _preco_total_promocional(p_mat: str, p_serv: str) -> str:
    try:
        return str(int(p_mat) + int(p_serv))
    except ValueError:
        return "130"


def _lead_pediu_link(txt: str) -> bool:
    """Confirmação explícita — não usa 'ok' solto (evita link sem intenção)."""
    t = (txt or "").strip().lower()
    if not t:
        return False
    if re.search(r"\bfirmo\b", t):
        return True
    if re.search(r"\b(link|manda\s+link|envia\s+r?o?\s*link)\b", t):
        return True
    if len(t) <= 48 and re.search(
        r"\b(sim|quero|confirmo|manda|pode\s+mandar|fecha|fechado|combinado)\b", t
    ):
        return True
    return False


def _extrair_valor_mencionado(txt: str) -> int:
    t = (txt or "").lower()
    m = re.search(r"(?:r\$\s*)?(\d{2,4})(?:[.,]\d{1,2})?", t)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except ValueError:
        return 0


def _tem_objecao_preco(txt: str) -> bool:
    t = (txt or "").lower()
    if not t:
        return False
    if _extrair_valor_mencionado(t) > 0:
        return True
    return bool(
        re.search(
            r"\b(caro|sem\s+dinheiro|sem\s+grana|n[aã]o\s+tenho|não\s+tenho|apertado|"
            r"s[oó]\s+tenho|só\s+tenho|n[aã]o\s+consigo|não\s+consigo|muito\s+alto|"
            r"fica\s+pesado|abaixa|desconto|parcel|mais\s+barato)\b",
            t,
        )
    )


def _ticket_bucket_inicial(meta: dict, lead_id: int) -> int:
    if int(meta.get("node8_ticket_inicial", 0) or 0) in (130, 100, 65):
        return int(meta.get("node8_ticket_inicial"))
    lid = int(lead_id or 0)
    bucket = lid % 3
    val = 130 if bucket == 0 else 100 if bucket == 1 else 65
    meta["node8_ticket_inicial"] = val
    meta["node8_ticket_atual"] = val
    return val


def _offer_id_por_ticket(config: dict, ticket: int) -> str:
    ck = (config or {}).get("cakto") or {}
    om = ck.get("offer_id_map") if isinstance(ck, dict) else {}
    if isinstance(om, dict):
        v = str(om.get(str(int(ticket))) or "").strip()
        if v:
            return v
    return str((ck or {}).get("offer_id") or "").strip()


def _eh_bloco_preco(texto: str) -> bool:
    t = (texto or "").lower()
    if not t:
        return False
    return bool(re.search(r"\br\$\s*\d{2,4}", t)) and bool(
        re.search(r"\b(valor|investimento|hoje|agora|promo|desconto)\b", t)
    )


def _ponte_emocional_preco(nome_fmt: str, dor: str, tempo_ctx: str, ancora_quer: str) -> str:
    alvo = (ancora_quer or "").strip()
    if alvo:
        return (
            f"{nome_fmt}, eu sei o peso de carregar isso há {tempo_ctx}. "
            f"O que eu te proponho aqui é um passo real em direção ao que você quer: {alvo}."
        )
    return (
        f"{nome_fmt}, eu sei o peso de carregar isso há {tempo_ctx}. "
        f"O próximo passo é para tirar você desse ciclo de {dor} com seriedade."
    )


def _cta_firmo_variavel(nome_fmt: str, ticket: int) -> str:
    opcoes = [
        (
            f"{nome_fmt}, se fizer sentido pra você, escreve *FIRMO* e eu te envio o link "
            f"no valor de R$ {ticket} na próxima mensagem, tudo bem?"
        ),
        (
            f"Se você quiser seguir no valor de R$ {ticket}, me chama com *FIRMO* "
            "que eu já te mando o checkout em seguida, pode ser?"
        ),
        (
            f"{nome_fmt}, quando você decidir avançar em R$ {ticket}, escreve *FIRMO* "
            "e eu te envio o link agora, combinado?"
        ),
    ]
    return random.choice(opcoes)


def _resolver_link_ticket(meta: dict, config: dict, link_fallback: str, ticket: int) -> str:
    key = f"node8_checkout_link_{int(ticket)}"
    cached = normalizar_link_para_envio(str(meta.get(key) or ""), instagram_mode=False)
    if cached:
        return cached
    # URLs estáticas por ticket (.env CHECKOUT_URL_65 / _100 / _130) — têm prioridade sobre API Cakto.
    cup = (config or {}).get("checkout_urls") or {}
    if isinstance(cup, dict):
        static_raw = str(cup.get(str(int(ticket))) or "").strip()
        if static_raw:
            norm = normalizar_link_para_envio(static_raw, instagram_mode=False)
            if norm:
                meta[key] = norm
                return norm
    ck = (config or {}).get("cakto") or {}
    cli = _cakto_client_from_config(config)
    if not cli:
        return link_fallback
    try:
        link_api = cli.resolve_checkout_url(
            offer_id=_offer_id_por_ticket(config, ticket),
            offer_slug=str(ck.get("offer_slug") or ""),
        )
        if link_api:
            meta[key] = link_api
            return link_api
    except Exception as e:
        logger.warning("⚠️ [NODE 8] Cakto link ticket=%s indisponível: %s", ticket, e)
    return link_fallback


_SYSTEM_OFERTA_SUPREMA = """Você é Esmeralda Ácassia (Meu Mistério Esmeralda), mesma voz da leitura: firme, acolhedora, transparente no que custa e no que vem depois.

IMPORTANTE: Não escreva tags de estágio, [COLCHETES] técnicos nem metadados na resposta. Não inclua URL nem link na resposta.
CONTEXTO INTERNO (CRÍTICO): use histórico apenas como base interna. PROIBIDO reproduzir texto bruto do histórico, PROIBIDO citar mensagens literais entre aspas, e PROIBIDO imprimir separadores técnicos (ex.: "|", "||", "->").

{norte_venda_fria}

{constituicao_camada}

DADOS (use com respeito):
- Lead: {nome} | Gênero: {genero} | Concordância: {genero_hint}
- Tom: {tom} | Dor (resumo limpo): {dor} | Tempo: {tempo}
- Perfil de copy (adapte tom): {perfil_copy}
- Mecanismo (use o nome EXATO «{mecanismo}» nos blocos que nomeiam o trabalho; não troque por sinônimo genérico) | Energia: {energia}
- Nome/Pessoa envolvida no relato: {nome_pessoa_envolvida}
- Tempo exato citado pelo lead (quando houver): {tempo_exato}
- Evento gatilho citado pelo lead (quando houver): {evento_gatilho}
- Última mensagem do lead: "{msg_lead}"

{entregaveis}

{instrucao_ancoragem}

{instrucao_eco_esforco}

{contexto_desejo_resultado}

Continuidade: não repita paráfrase vazia do que já foi dito na leitura e na agitação; avance com clareza (valores, entrega, próximo passo). A oferta fecha em cima do **que a pessoa quer ver acontecer**, não em palestra sobre o que ela "precisa" aceitar.

VALORES (não altere números):
- Referência de investimento: R$ {p_ref},00.
- Total promocional fechado: R$ {p_promo_total},00 (R$ {p_mat} agora + R$ {p_serv} depois de sentir resultado).
- Pagamento online: Cakto (cartão ou PIX). Não escreva o link; o sistema envia depois.

MISSÃO — exatamente 9 BLOCOS (BLOCO_1:: … BLOCO_9::); cada bloco CURTO (ritmo celular, ~160 caracteres ou menos quando possível); pode continuar o texto nas linhas abaixo até o próximo BLOCO_N::; nunca coloque o próximo BLOCO_N:: no fim da mesma linha do texto anterior:
1. Pergunte com naturalidade se a leitura ressoou; pode usar "Gostou da sua leitura?" de forma humilde.
2. CENA DO RESULTADO DESEJADO: convide a imaginar o caminho **em direção ao que ela já disse que quer** (trazer a pessoa de volta, **separar com clareza do cônjuge**, **superar e fechar ciclo com o ex**, **encontrar um novo amor**, fortalecer o casamento atual, justiça, prosperidade…), com imagem viva — não frase genérica nem "o que você precisa entender". Não troque o desejo dela por outro.
3. CONTRASTE: ficar só na dor repetida vs dar o passo que favorece o que ela busca — sem humilhar.
4. MECANISMO: nomeie o trabalho com o nome exato «{mecanismo}» como firmação **alinhada ao pedido dela** (sem trocadilho nem título ridículo); não venda "lição", venda continuidade honesta do que ela veio buscar.
5. VALOR: âncora R$ {p_ref}; oferta R$ {p_promo_total} como R$ {p_mat} agora (ato de fé/intenção) + R$ {p_serv} só quando sentir resultado nas mãos; conecte em 1 frase aos entregáveis acima e ao resultado desejado.
6. DECISÃO HONESTA: urgência pela vida dela e pelo que ela quer ver mudar, NUNCA por "vagas", "só duas vagas", "últimas vagas" ou escassez inventada (isso mata a autoridade no WhatsApp).
7. CAKTO: plataforma segura e confiável; cartão ou PIX (sem URL).
8. COMPROVANTE: após pagar, enviar comprovante; você monta o nome no altar e manda foto da firmação.
9. CTA + FIRMO: a frase IMEDIATAMENTE antes de pedir FIRMO deve ecoar o **pedido concreto** dela (nome, tempo {tempo_exato} se couber, pessoa ou situação que ela citou). PROIBIDO clichê espiritual vazio tipo "se o coração vibra e a alma está pronta". Depois peça FIRMO e diga que na mensagem seguinte você envia o link — termine com "tudo bem?" (sem URL).

REGRAS ANTI-IA:
- Sem travessão. Sem "Claro" ou "Com certeza" vazios. Sem búzios/tremor místico forçado.
- PROIBIDO: "você precisa entender", "o que você precisa é", "antes de tudo você tem que" — soa a sermão, não a oferta do que ela deseja.
- PROIBIDO prometer resultado externo garantido (volta de pessoa, ganho de causa, prazo fixo). PERMITIDO: trabalho com intenção firme voltada ao que ela busca, linguagem de abertura de caminho e firmação responsável.
- Siga {genero} e {genero_hint}. Um vocativo só: feminino "meu anjo" ou nome; masculino "meu filho" ou nome; indefinido "meu bem" ou nome (não misturar meu bem / meu anjo).
- Nome do lead no máximo 2 vezes nos 9 blocos.
- Se houver {tempo_exato} e/ou {evento_gatilho}, ancore pelo menos 1 bloco nisso.
- Inclua 1 bloco com ideia de potencial represado ("já era para estar em patamar mais alto") se couber sem repetir a leitura.
- Responda só em BLOCO_N::texto.
"""


def _fallback_oferta(
    nome_fmt: str,
    voc: str,
    dor_c: str,
    tempo: str,
    tempo_exato: str,
    evento_gatilho: str,
    mecanismo: str,
    p_ref: str,
    p_mat: str,
    p_serv: str,
    p_promo_total: str,
    ancora_quer: str = "",
) -> list[str]:
    dor_ctx = frase_dor_contextualizada(dor_c, abertura="quando você traz")
    tempo_ctx = tempo_exato if (tempo_exato or "").upper() != "INDEFINIDO" else tempo
    gatilho_ctx = (
        f" Quando você lembra de {evento_gatilho}, isso fica ainda mais claro."
        if (evento_gatilho or "").upper() != "INDEFINIDO"
        else ""
    )
    alvo = (ancora_quer or "").strip()
    if len(alvo) > 140:
        alvo = alvo[:137].rstrip() + "…"
    b2 = (
        f"Imagina o caminho ficando mais claro em direção ao que você veio buscar, {voc}, com menos peso repetido no peito."
        if alvo
        else f"Imagina os próximos dias com menos peso no peito e mais direção prática, {voc}."
    )
    mec_linha = (
        f"O {mecanismo} é firmação séria voltada ao que você pediu"
        + (f" — no que você descreveu: {alvo}" if alvo else "")
        + ". Corta o nó na raiz, sem promessa de milagre nem data certa."
    )
    bloco_valor = (
        f"O valor de referência é R$ {p_ref},00. Eu consigo fazer por R$ {p_promo_total} pra você, em pagamento direto hoje."
        if str(p_serv) == "0"
        else (
            f"O valor de referência é R$ {p_ref},00. Eu consigo fazer por R$ {p_promo_total} pra você: "
            f"R$ {p_mat} neste momento como ato de fé e intenção real de mudar de vida, "
            f"e os outros R$ {p_serv} somente quando você estiver feliz e em paz com o que sentir nas mãos."
        )
    )
    return [
        f"{nome_fmt}, a leitura que você recebeu tocou em algo real. Posso te mostrar o próximo passo com clareza?",
        b2,
        f"O caminho é simples: ou a gente toca a raiz agora, ou o ciclo continua — há {tempo_ctx} você carrega esse peso sem sair do lugar.{gatilho_ctx}",
        f"{mec_linha} Com o que apareceu nas suas linhas, você já era pra estar em um patamar mais alto do que está hoje.",
        bloco_valor,
        "A leitura já mostrou o padrão. A decisão agora é honesta: mudar de verdade ou continuar no mesmo ciclo. "
        "Sem história de vaga limitada, isso é respeito com você.",
        "O pagamento é pela Cakto: plataforma segura, confiável, cartão ou PIX.",
        "Se decidir seguir, me envia o comprovante pra gente iniciar — eu monto seu nome no altar e te mando a foto da firmação.",
        (
            f"{nome_fmt}, você carrega isso há {tempo_ctx}.{gatilho_ctx} "
            "Chegou a hora de atacar a raiz, não só o sintoma. "
            "Se quiser começar hoje, me manda FIRMO aqui que na mensagem seguinte eu te envio o link de pagamento, tudo bem?"
        ),
    ]


def executar_v2(ctx) -> tuple:
    meta = getattr(ctx, "metadata", {}) or {}
    _seg = contexto_lead_para_nodes(ctx.nome_lead or "", meta, dor_max_len=95, desabafo_max_len=1200)
    nome_fmt = _seg["nome_fmt"]
    tts_ativo = meta.get("tts_ativo", False)
    config = meta.get("__config__", {}) or {}

    energia = meta.get("nivel_energia", "Baixa")
    tom = meta.get("tom_cirurgico", "Maternal")
    dor = _seg["resumo_dor_safe"]
    tempo = meta.get("tempo_sofrimento", "muito tempo")
    tempo_exato = str(meta.get("tempo_exato", "INDEFINIDO") or "INDEFINIDO")
    evento_gatilho = str(meta.get("evento_gatilho", "INDEFINIDO") or "INDEFINIDO")
    nome_pessoa_envolvida = str(meta.get("nome_pessoa_envolvida", "INDEFINIDO") or "INDEFINIDO")
    mecanismo = definir_nome_mecanismo_se_generico(meta, dor)
    ctx_desejo_res = contexto_desejo_resultado_para_prompt(meta, mecanismo)
    ancora_quer_fb = str(meta.get("desejo_declarado") or meta.get("desejo_oculto") or "").strip()
    # Sanitiza: remove apresentações de nome ("me chamo X") que podem ter sido capturadas
    # junto com o desejo quando o lead enviou duas mensagens simultâneas.
    _re_nome_n8 = re.compile(
        r"(?:^|[\s,;])[^\n.]{0,60}(?:me\s+chamo|meu\s+nome\s+[eéh]|chamo[- ]?me|sou\s+(?:o|a)\s+)\s*\w+[^\n.]{0,80}",
        re.IGNORECASE,
    )
    _quer_limpo = _re_nome_n8.sub("", ancora_quer_fb)
    _quer_limpo = re.sub(r"\s{2,}", " ", _quer_limpo).strip().rstrip(",;.")
    if _quer_limpo and len(_quer_limpo) > 5:
        ancora_quer_fb = _quer_limpo
    msg_lead = str(ctx.texto_recebido or "").strip()
    if lead_reportou_problema_entrega(msg_lead):
        ctx.estado_coleta = "node8_reparo_entrega"
        ctx.metadata = meta
        return (
            [
                Acao(tipo="delay", segundos=random.randint(3, 6)),
                Acao(
                    tipo="text",
                    conteudo=f"Vi seu aviso, {nome_fmt}. Vou seguir com mensagens menores para não cortar nada.",
                    metadata={"skip_gancho_final": True},
                ),
                Acao(tipo="delay", segundos=random.randint(2, 4)),
                Acao(
                    tipo="text",
                    conteudo="Me manda *ok* e eu continuo exatamente de onde paramos.",
                    metadata={"skip_gancho_final": True},
                ),
            ],
            "8_oferta_principal",
        )
    perfil_copy = perfil_copy_para_prompt(meta, msg_lead)
    entregaveis = entregaveis_oferta_para_prompt(config)
    instrucao_anc = instrucao_ancoragem_node6(nome_pessoa_envolvida, tempo_exato, evento_gatilho)
    instrucao_eco_esf = instrucao_eco_esforco_concreto(meta) or ""
    score_eng = float(getattr(ctx, "score_engajamento", 0.5) or 0.5)

    genero = genero_efetivo_para_copy(
        (ctx.nome_lead or "").strip() or nome_fmt,
        meta,
        texto_discurso=msg_lead or None,
    )
    meta["genero_lead"] = genero
    genero_hint = genero_hint_para_prompt(meta)

    if genero == "masculino":
        voc = "meu filho"
    elif genero == "feminino":
        voc = "meu anjo"
    else:
        voc = "meu bem"

    ticket_inicial = _ticket_bucket_inicial(meta, int(getattr(ctx, "lead_id", 0) or 0))
    ticket_atual = int(meta.get("node8_ticket_atual", ticket_inicial) or ticket_inicial)
    p_mat = str(ticket_atual).strip()
    p_serv = "0"
    p_ref = str(config.get("preco_original") or "360").strip()
    p_promo_total = p_mat
    link_raw = config.get("link_pagamento", "[LINK_NÃO_CONFIGURADO]")
    link = _normalizar_link_checkout(str(link_raw))

    # ── Fase 2: lead já recebeu a oferta; só libera link após FIRMO/sim curto ──
    if meta.get("node8_fase") == "esperando_firmo":
        if _tem_objecao_preco(msg_lead):
            atual = int(meta.get("node8_ticket_atual", ticket_inicial) or ticket_inicial)
            insist = int(meta.get("node8_neg_insist_count", 0) or 0)
            pediu_qt = bool(meta.get("node8_neg_perguntou_quanto_pode"))
            valor = _extrair_valor_mencionado(msg_lead)
            alvo = atual
            msg_neg = ""

            if atual >= 130:
                alvo = 100
                msg_neg = (
                    f"{nome_fmt}, eu te escuto. Pra não te perder nesse passo, eu consigo abrir por R$ {alvo} agora. "
                    "É o ajuste máximo que consigo manter com seriedade no trabalho."
                )
            elif atual == 100:
                if insist < 3:
                    meta["node8_neg_insist_count"] = insist + 1
                    msg_neg = (
                        f"{nome_fmt}, já te dei um desconto forte para R$ 100 e esse valor segura a estrutura do ritual. "
                        "Se você topar, eu te mando o link agora."
                    )
                else:
                    meta["node8_neg_perguntou_quanto_pode"] = True
                    if valor >= 30:
                        alvo = max(30, min(50, valor))
                        msg_neg = (
                            f"Entendi. Eu consigo te liberar por R$ {alvo} agora para não travar seu caso, "
                            "e você acerta o restante depois."
                        )
                    else:
                        msg_neg = "Me fala com sinceridade: quanto você consegue hoje pra gente não perder seu processo?"
            elif atual == 65:
                alvo = 40
                msg_neg = (
                    f"{nome_fmt}, pra te ajudar hoje eu consigo baixar para R$ {alvo} agora. "
                    "Se topar, te mando o checkout já."
                )
            elif atual == 40:
                alvo = 30
                msg_neg = (
                    "Último ajuste que consigo manter com responsabilidade: R$ 30 agora. "
                    "Abaixo disso eu não consigo segurar com seriedade."
                )
            elif atual == 30:
                msg_neg = "R$ 30 é o mínimo que eu consigo aceitar para iniciar com responsabilidade. Se topar, eu te mando."
            else:
                if pediu_qt and valor >= 30:
                    alvo = max(30, min(50, valor))
                    msg_neg = f"Fecho com você em R$ {alvo} agora e o restante você acerta depois."
                else:
                    msg_neg = "Pra não te perder agora, me diz quanto você consegue hoje."

            if alvo != atual:
                meta["node8_ticket_atual"] = alvo
                meta["node8_neg_perguntou_quanto_pode"] = False
                if alvo in (50, 40, 30):
                    meta["node8_pagamento_restante_pendente"] = True
            ctx.metadata = meta
            return (
                [
                    Acao(tipo="delay", segundos=random.randint(3, 6)),
                    Acao(tipo="text", conteudo=msg_neg, metadata={"skip_gancho_final": True}),
                    Acao(tipo="delay", segundos=random.randint(2, 5)),
                    Acao(tipo="text", conteudo="Se fizer sentido, escreve *FIRMO* que eu te mando o link agora."),
                ],
                "8_oferta_principal",
            )

        if _lead_pediu_link(msg_lead):
            ticket_envio = int(meta.get("node8_ticket_atual", ticket_inicial) or ticket_inicial)
            link_resolvido = _resolver_link_ticket(meta, config, link, ticket_envio)
            link_candidato = compactar_url_https_monolitica(link_resolvido) or compactar_url_https_monolitica(
                re.sub(r"\s+", "", str(link_resolvido or ""))
            )
            link_final = (link_candidato or "").strip()
            if not _link_checkout_valido(link_final):
                fallback = _normalizar_link_checkout(str(config.get("link_pagamento") or ""))
                if _link_checkout_valido(fallback):
                    link_final = fallback
                else:
                    logger.warning("event=node8_link_invalido lead=%s ticket=%s", nome_fmt, ticket_envio)
                    ctx.metadata = meta
                    return (
                        [
                            Acao(tipo="delay", segundos=random.randint(3, 6)),
                            Acao(
                                tipo="text",
                                conteudo=(
                                    "Eu não vou te enviar link quebrado, meu bem. "
                                    "Me responde *LINK* que eu te envio um checkout válido na sequência."
                                ),
                                metadata={"skip_gancho_final": True},
                            ),
                        ],
                        "8_oferta_principal",
                    )

            meta["node8_fase"] = "concluido"
            ctx.estado_coleta = "node8_link_enviado"
            ctx.metadata = meta
            logger.info("event=node8_link_ok lead=%s", nome_fmt)

            acoes = [
                Acao(tipo="delay", segundos=random.randint(4, 8)),
                Acao(
                    tipo="text",
                    conteudo=f"Aqui está o link do valor combinado (R$ {ticket_envio}) — Cakto, seguro pra cartão ou PIX:",
                    metadata={"skip_gancho_final": True},
                ),
                Acao(tipo="delay", segundos=random.randint(5, 9)),
                Acao(
                    tipo="text",
                    conteudo=link_final,
                    metadata={"skip_gancho_final": True},
                ),
                Acao(tipo="delay", segundos=random.randint(8, 12)),
                Acao(
                    tipo="text",
                    conteudo=(
                        "Após o pagamento, me envia o comprovante aqui. "
                        "Eu monto o seu nome no altar e te mando a foto da firmação na sequência, tudo bem?"
                    ),
                    metadata={"skip_gancho_final": True},
                ),
            ]
            return acoes, "aguardando_pagamento"

        nudge = _cta_firmo_variavel(
            nome_fmt,
            int(meta.get("node8_ticket_atual", ticket_inicial) or ticket_inicial),
        )
        ctx.metadata = meta
        return (
            [
                Acao(tipo="delay", segundos=random.randint(3, 6)),
                Acao(tipo="text", conteudo=nudge, metadata={"skip_gancho_final": True}),
            ],
            "8_oferta_principal",
        )

    # ── Fase 1: oferta completa, sem URL ──
    blocos_gerados: list[str] = []

    try:
        if ctx.personalizer:
            logger.info(
                "💰 [NODE 8 v25] Oferta (sem link) para %s (gênero=%s).",
                nome_fmt,
                genero_hint,
            )
            meta_ia = dict(meta)
            meta_ia["node_copy_venda_direta"] = True
            prompt_ia = (
                f"Lead: {nome_fmt}. Gere os 9 blocos (BLOCO_1:: … BLOCO_9::), "
                f"valores R$ {p_ref} de referência e total promocional R$ {p_promo_total} ({p_mat}+{p_serv}), "
                "Cakto sem URL, último bloco FIRMO para link na mensagem seguinte. "
                f"Nome do trabalho (manter exato): «{mecanismo}». "
                "Ancorar a oferta no RESULTADO que o lead quer (ver bloco RESULTADO no system), não em sermão de \"o que precisa\". "
                f"{entregaveis}"
            )
            prompt_ia += sufixo_ancoras_node3_para_prompt(meta)
            # DARE: oferta personalizada por desejo_tipo (Hormozi value stack + intensidade)
            _desejo_tipo_n8 = classificar_desejo_tipo(meta, msg_lead)
            _historico_blob_n8 = " ".join(
                str((h.get("texto") if isinstance(h, dict) else getattr(h, "texto", "")) or "")
                for h in (getattr(ctx, "historico", None) or [])[-8:]
            )
            _intensidade_n8 = calcular_intensidade_ressonancia(meta, _historico_blob_n8)
            _padrao_n8 = nome_padrao_invisivel(_desejo_tipo_n8)
            _dare_oferta_injecao = oferta_dare_para_prompt(_desejo_tipo_n8, meta, p_mat, p_serv)
            sys_oferta = _SYSTEM_OFERTA_SUPREMA.format(
                nome=nome_fmt,
                genero=genero,
                genero_hint=genero_hint,
                tom=tom,
                perfil_copy=perfil_copy,
                dor=dor,
                tempo=tempo,
                mecanismo=mecanismo,
                energia=energia,
                msg_lead=msg_lead,
                nome_pessoa_envolvida=nome_pessoa_envolvida,
                tempo_exato=tempo_exato,
                evento_gatilho=evento_gatilho,
                entregaveis=entregaveis,
                instrucao_ancoragem=instrucao_anc,
                instrucao_eco_esforco=instrucao_eco_esf,
                contexto_desejo_resultado=ctx_desejo_res,
                norte_venda_fria=norte_editorial_venda_fria_direta_para_prompt(),
                constituicao_camada=camada_constituicao_node8(meta, mecanismo),
                p_ref=p_ref,
                p_mat=p_mat,
                p_serv=p_serv,
                p_promo_total=p_promo_total,
            ) + (
                f"\n\nPADRÃO INVISÍVEL IDENTIFICADO: \"{_padrao_n8}\""
                f"\nINTENSIDADE DE RESSONÂNCIA DO LEAD: {_intensidade_n8.upper()}"
                f"\n\n{_dare_oferta_injecao}"
            )
            resposta = ""
            ultima_exc: Optional[Exception] = None
            _temps = (0.82, 0.88, 0.9)
            ie = ((ctx.metadata or {}).get("__config__", {}) or {}).get("ia_economia", {}) or {}
            max_tent = max(1, min(int(ie.get("max_tentativas_ia_por_node", 2) or 2), 3))
            for tentativa in range(max_tent):
                try:
                    hist_ia = historico_limpo_para_ia(ctx)
                    resposta = ctx.personalizer.gerar_resposta(
                        system_prompt=sys_oferta,
                        historico_lista=hist_ia,
                        mensagem_lead=prompt_ia,
                        metadata=meta_ia,
                        max_output_tokens=6144,
                        temperature=_temps[min(tentativa, len(_temps) - 1)],
                    )
                    blocos_dict = parse_blocos_leitura_ia(resposta, max_bloco=9, min_len=8)
                    blocos_gerados = [blocos_dict.get(i, "") for i in range(1, 10) if blocos_dict.get(i)]
                    blocos_gerados = [b for b in blocos_gerados if not _bloco_e_somente_link(b)]
                    if len(blocos_gerados) < 5:
                        blocos_gerados = extrair_blocos_fallback(resposta, 9, min_len=8, filtrar_links=True)
                    if len(blocos_gerados) >= 4:
                        break
                    if len(blocos_gerados) >= 3:
                        logger.info(
                            "event=node8_resposta_parcial_aproveitada blocos=%s tentativa=%s",
                            len(blocos_gerados),
                            tentativa + 1,
                        )
                        break
                    raise ValueError("Copy insuficiente.")
                except Exception as ex:
                    ultima_exc = ex
                    blocos_gerados = []
            if len(blocos_gerados) < 3:
                raise ValueError(str(ultima_exc) if ultima_exc else "Copy insuficiente.")
        else:
            raise ValueError("IA Offline.")
    except Exception as e:
        logger.warning("⚠️ [NODE 8] Geração incompleta (%s). Fallback v25.", e)
        meta["node8_fallback_acionado_turno"] = True
        meta["node8_fallback_motivo"] = str(e or "")[:180]
        blocos_gerados = _fallback_oferta(
            nome_fmt,
            voc,
            dor,
            tempo,
            tempo_exato,
            evento_gatilho,
            mecanismo,
            p_ref,
            p_mat,
            p_serv,
            p_promo_total,
            ancora_quer=ancora_quer_fb,
        )

    idx_preco = -1
    for i, b in enumerate(blocos_gerados):
        if _eh_bloco_preco(str(b)):
            idx_preco = i
            break
    if idx_preco > 0:
        bloco_ant = str(blocos_gerados[idx_preco - 1] or "").lower()
        if not re.search(r"\b(você quer|você busca|peso|dor|ciclo|coração|pedido)\b", bloco_ant):
            tempo_ctx = tempo_exato if tempo_exato.upper() != "INDEFINIDO" else tempo
            blocos_gerados.insert(
                idx_preco,
                _ponte_emocional_preco(nome_fmt, dor, tempo_ctx, ancora_quer_fb),
            )

    _DELAY_BUDGET_S = 210
    _delay_acumulado = 0

    acoes: list = []
    _d_inicial = random.randint(9, 15)
    acoes.append(Acao(tipo="delay", segundos=_d_inicial))
    _delay_acumulado += _d_inicial

    for i, conteudo_raw in enumerate(blocos_gerados):
        if not conteudo_raw:
            continue
        conteudo_str = re.sub(r"\[.*?\]", "", str(conteudo_raw).strip())
        if not re.search(r"https?://", conteudo_str, re.I):
            conteudo_str = re.sub(r"[-–—*•]+", "", conteudo_str).strip()
        else:
            conteudo_str = re.sub(r"https?://\S+", "", conteudo_str, flags=re.I)
            conteudo_str = re.sub(r"\s+", " ", conteudo_str).strip()
        conteudo_str = limpar_colagem_primeira_msg_whatsapp_em_texto(conteudo_str)
        conteudo_str = normalizar_enxerto_dor_sem_contexto(conteudo_str)
        conteudo_str = remover_marcadores_bloco_ia_vazados(conteudo_str)
        conteudo_str = unificar_vocativos_por_genero(conteudo_str, genero, nome_fmt)
        conteudo_str = aplicar_substituicoes_proibidas(conteudo_str)
        if not conteudo_str:
            continue

        num_bloco = i + 1
        pedacos = fatiar_texto_ritmo_celular(
            conteudo_str,
            max_linhas_visuais=MOBILE_MAX_LINHAS_BALO,
            chars_por_linha=MOBILE_CHARS_POR_LINHA,
        )
        eh_audio = (
            (num_bloco in _INDICES_AUDIO)
            and tts_ativo
            and ctx.personalizer is not None
            and len(pedacos) == 1
        )

        for j, pedaco in enumerate(pedacos):
            if not (pedaco or "").strip():
                continue
            delay_pre = _delay_digitacao(pedaco, eh_audio and j == 0, energia)
            if num_bloco in _INDICES_IMPACTO:
                delay_pre += random.randint(6, 12)
            pausa_pos = 16 if num_bloco in _INDICES_IMPACTO else 9
            delay_pre, pausa_pos = _cadencia_oferta(num_bloco, delay_pre, pausa_pos, score_eng)

            if _delay_acumulado >= _DELAY_BUDGET_S:
                delay_pre = min(delay_pre, 8)
                pausa_pos = min(pausa_pos, 4)

            acoes.append(Acao(tipo="delay", segundos=delay_pre))
            _delay_acumulado += delay_pre
            if eh_audio and j == 0:
                acoes.append(Acao(tipo="tts", tts_template=pedaco))
                acoes.append(Acao(tipo="delay", segundos=15))
                _delay_acumulado += 15
            else:
                acoes.append(
                    Acao(
                        tipo="text",
                        conteudo=pedaco,
                        metadata={"skip_gancho_final": True},
                    )
                )
                acoes.append(Acao(tipo="delay", segundos=pausa_pos))
                _delay_acumulado += pausa_pos

    meta["node8_fase"] = "esperando_firmo"
    meta["node8_ticket_atual"] = int(meta.get("node8_ticket_atual", ticket_inicial) or ticket_inicial)
    meta["node8_ticket_inicial"] = int(meta.get("node8_ticket_inicial", ticket_inicial) or ticket_inicial)
    ctx.estado_coleta = "node8_oferta_enviada"
    ctx.metadata = meta
    total_textos = sum(1 for a in acoes if getattr(a, "tipo", "") == "text")
    logger.info(
        "event=node8_oferta_ok lead=%s blocos=%s fase=esperando_firmo ticket=%s textos=%s delay_total_s=%s",
        nome_fmt,
        len(blocos_gerados),
        meta.get("node8_ticket_atual"),
        total_textos,
        _delay_acumulado,
    )

    return acoes, "8_oferta_principal"
