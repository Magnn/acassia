"""
copy_sanitizer.py — Sanitização global de copy WhatsApp (Cigana Esmeralda)
Aplicar antes de persistir/enviar texto ao lead.

API central para dados do lead nos nodes:
- contexto_lead_para_nodes(nome, meta, dor_max_len=…) → nome_fmt, resumo_dor_safe, desabafo_prompt
- nome_lead_para_exibicao, resumo_dor_para_copy, desabafo_para_prompt_ia
- limpar_colagem_primeira_msg_whatsapp_em_texto (saída IA que colou abertura do WhatsApp)
"""
from __future__ import annotations

import logging
import random
import re
from typing import List, Literal, Optional, Dict, Any, Mapping

from flows.funnel_gates import (
    contato_salvo_ou_declarado,
    nome_eh_placeholder,
    nome_util_para_checklist_fase1,
    VOCATIVO_SEM_NOME,
)
from schema import slice_historico_para_ia

logger = logging.getLogger(__name__)

# Mobile-first: maioria dos leads lê no celular; manter balões enxutos.
MOBILE_MAX_LINHAS_BALO = 3
MOBILE_CHARS_POR_LINHA = 34

# Lista única de primeiros nomes masculinos comuns (PT) — inferência de vocativo antes do Node 5
NOMES_MASCULINOS_COMUNS: frozenset[str] = frozenset({
    "magno", "joão", "joao", "jose", "josé", "carlos", "pedro", "paulo", "marcos",
    "lucas", "gabriel", "rafael", "daniel", "mateus", "bruno", "andre", "andré",
    "rodrigo", "thiago", "gustavo", "felipe", "leonardo", "igor", "victor",
    "vitor", "alan", "alex", "anderson", "antonio", "antônio", "arthur", "caio",
    "diego", "eduardo", "fabricio", "fabrício", "fernando", "guilherme", "henrique",
    "hugo", "ivan", "jonathan", "julio", "júlio", "kevin", "leandro", "marcelo",
    "tiago", "wagner", "william", "davi", "enzo", "heitor", "murilo", "ricardo",
    "sergio", "sérgio", "vinicius", "vinícius", "breno", "cesar", "cesár", "césar",
    "leisson", "edson", "wilson", "nelson", "gilson", "ailton",
})

# Primeiros nomes femininos óbvios — evita heurística -o/-son classificar mulher como homem
NOMES_FEMININOS_COMUNS: frozenset[str] = frozenset({
    "maria", "ana", "julia", "juliana", "fernanda", "patricia", "patrícia",
    "camila", "amanda", "bruna", "larissa", "beatriz", "leticia", "letícia",
    "gabriela", "rafaela", "isabela", "carla", "daniela", "adriana", "sandra",
    "aline", "caroline", "carolina", "vanessa", "priscila", "simone",
})


def primeiro_token_nome(nome: str) -> str:
    return (nome or "").strip().lower().split()[0] if (nome or "").strip() else ""


def nome_sugere_masculino_por_heuristica(token: str) -> bool:
    """Sufixos comuns de nomes masculinos (ex.: Leisson, Edson, Ricardo)."""
    if len(token) < 3:
        return False
    if token in NOMES_FEMININOS_COMUNS:
        return False
    if token.endswith(("sson", "ilson", "elson", "rdo", "lton", "ildo", "aldo", "erto")):
        return True
    if len(token) >= 4 and token.endswith("o"):
        return True
    return False


def nome_parece_feminino(nome: str) -> bool:
    return primeiro_token_nome(nome) in NOMES_FEMININOS_COMUNS


def inferir_masculino_somente_nome(nome: str) -> bool:
    t = primeiro_token_nome(nome)
    if not t:
        return False
    if t in NOMES_MASCULINOS_COMUNS:
        return True
    return nome_sugere_masculino_por_heuristica(t)


def nome_parece_masculino(nome: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    if (metadata or {}).get("genero_lead", "").lower() == "masculino":
        return True
    return inferir_masculino_somente_nome(nome)


def _tem_palavra(hay: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", hay, re.IGNORECASE) is not None


def inferir_genero_pelo_discurso_pt(texto: str) -> Optional[Literal["masculino", "feminino"]]:
    """
    Sinais gramaticais no que o lead escreve sobre si (PT-BR), sem LLM e sem custo de token.
    Usa fronteiras de palavra para evitar 'cansado' dentro de 'descansado'.
    Retorna None se ambíguo ou sem sinal.
    """
    if not texto or len(texto.strip()) < 3:
        return None
    t = texto.lower()

    # Frases explícitas (alta confiança)
    if re.search(r"\b(sou|fui)\s+um\s+homem\b", t):
        return "masculino"
    if re.search(r"\b(sou|fui)\s+uma\s+mulher\b", t):
        return "feminino"
    if re.search(r"\b(sou|fui)\s+o\s+pai\b", t) or re.search(r"\b(sou|fui)\s+o\s+marido\b", t):
        return "masculino"
    if re.search(r"\b(sou|fui)\s+a\s+m[aã]e\b", t) or re.search(r"\b(sou|fui)\s+a\s+esposa\b", t):
        return "feminino"

    # Crise afetiva (quem fala): "minha ex" / "meu ex" — sinal fraco por nicho, útil quando nome é placeholder
    if re.search(r"\bminha\s+ex\b", t) or re.search(
        r"\bminha\s+(namorada|noiva|esposa)\b", t
    ):
        return "masculino"
    if re.search(r"\bmeu\s+ex\b", t) or re.search(
        r"\bmeu\s+(namorado|noivo|marido)\b", t
    ):
        return "feminino"

    masc_part = (
        "casado", "cansado", "sozinho", "apaixonado", "interessado", "preocupado",
        "divorciado", "separado", "solteiro", "grato", "felizardo", "ferido",
        "envergonhado", "perdido", "confuso", "frustrado", "nervoso", "chateado",
    )
    fem_part = (
        "casada", "cansada", "sozinha", "apaixonada", "interessada", "preocupada",
        "divorciada", "separada", "solteira", "grata", "felizarda", "ferida",
        "envergonhada", "perdida", "confusa", "frustrada", "nervosa", "chateada",
    )
    cm = sum(1 for w in masc_part if _tem_palavra(t, w))
    cf = sum(1 for w in fem_part if _tem_palavra(t, w))
    if cm > 0 and cf == 0:
        return "masculino"
    if cf > 0 and cm == 0:
        return "feminino"
    if cm > cf:
        return "masculino"
    if cf > cm:
        return "feminino"
    return None


def genero_efetivo_para_copy(
    nome: str,
    metadata: Optional[Dict[str, Any]] = None,
    *,
    texto_discurso: Optional[str] = None,
) -> str:
    """
    Umifica gênero para prompts e copy: nunca assume feminino por omissão.

    Ordem:
    1) metadata explícito (quando já foi salvo no fluxo)
    2) listas de primeiro nome (feminino / masculino conhecidos)
    3) discurso do lead (particípios e frases — barato, sem LLM)
    4) heurística de grafia do nome (-o, -sson…)
    5) indefinido
    """
    m = metadata or {}
    g = str(m.get("genero_lead") or "").strip().lower()
    if g in ("masculino", "masc", "homem", "m"):
        return "masculino"
    if g in ("feminino", "fem", "mulher", "f"):
        return "feminino"
    if nome_parece_feminino(nome):
        return "feminino"
    tok = primeiro_token_nome(nome)
    if tok in NOMES_MASCULINOS_COMUNS:
        return "masculino"

    partes_txt: List[str] = []
    if (texto_discurso or "").strip():
        partes_txt.append((texto_discurso or "").strip())
    for _k in ("desabafo_original", "texto_inferencia_genero", "texto_recente_lead"):
        _s = str(m.get(_k) or "").strip()
        if _s:
            partes_txt.append(_s)
    texto = " ".join(partes_txt)[:8000]
    if texto:
        pelo_texto = inferir_genero_pelo_discurso_pt(texto)
        if pelo_texto:
            return pelo_texto

    if nome_sugere_masculino_por_heuristica(tok):
        return "masculino"
    return "indefinido"


def genero_hint_para_prompt(metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Trecho para injetar em prompts de sistema (ex.: placeholder {genero_hint}).
    Espera metadata['genero_lead'] já definido (tipicamente após genero_efetivo_para_copy).
    """
    g = str((metadata or {}).get("genero_lead") or "").strip().lower()
    if g == "masculino":
        return "masculino"
    if g == "feminino":
        return "feminino"
    return "indefinido: prefira 'você' e 'suas linhas', sem marcar gênero à força"


def vocativo_cigana(
    nome_raw: str,
    genero_hint: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Tratamento na segunda pessoa: masculino → Meu filho; feminino Meu anjo; indefinido neutro."""
    meta = dict(metadata or {})
    eff = genero_efetivo_para_copy(
        nome_raw,
        {**meta, "genero_lead": genero_hint or meta.get("genero_lead") or ""},
    )
    if eff == "masculino":
        return "Meu filho"
    if eff == "feminino":
        return "Meu anjo"
    return "Meu bem"


# Eco de confirmações do WhatsApp / colagem da IA dentro do campo "dor" (Nodes 6–8)
_RE_LIXO_ECOU_DOR_COPY = re.compile(
    r"\b(já estou te seguindo|já\s+te\s+seguindo|segue\s+lá|tá\s+bom|ta\s+bom|´ta\s+bom)\b",
    re.I,
)
# Corta tudo após primeira frase de stalking repetida (modelo colou confirmação do app)
_RE_CORTA_APOS_STALK = re.compile(
    r"(?is)\s*j[aá]\s+estou\s+te\s+seguindo.*$",
)

# Colagem típica de abertura de WhatsApp dentro de DOR_CENTRAL / resumo_dor (Nodes 5–6)
_RE_CORTA_PRECO_CONSULTA = re.compile(
    r"(?is)[,;]?\s*(quanto\s+custa|qual\s+(é\s+)?o\s+(valor|preço|preco)|"
    r"preço\s+d[ae]\s+consulta|preco\s+d[ae]\s+consulta|valor\s+d[ae]\s+consulta|"
    r"quanto\s+(fica|é)|aceita\s+pix)\b.*$"
)
_RE_TOKENS_ABERTURA_NAO_DOR = re.compile(
    r"(?is)^(boa\s+(tarde|noite|dia)|olá|ola|oi)\s*[,.!]?\s*",
)


def _strip_colagem_whatsapp_em_dor(s: str) -> str:
    """Remove saudação, apresentação e pergunta de preço que não são 'dor central'."""
    t = (s or "").strip()
    if not t:
        return ""
    t = _RE_TOKENS_ABERTURA_NAO_DOR.sub("", t)
    t = re.sub(r"(?is)\bcigana\s+esmeralda\s*[,.]?\s*", "", t)
    t = re.sub(r"(?is)me\s+chamo\s+[A-Za-zÀ-ú']{2,24}\s*[,.]?\s*", "", t)
    # Operacional típico no meio da colagem (Node 6 fallback / eco de dado_concreto)
    t = re.sub(r"(?is)\b(essa\s+)?consulta\s+(é\s+)?paga\??\b", "", t)
    t = re.sub(r"(?is)\btudo\s+bem\??\b", "", t)
    t = re.sub(r"(?is)\bcomo\s+vai\??\b", "", t)
    t = re.sub(r"(?is)\b(tá|ta)\s+(bom|bem)\??\b", "", t)
    t = re.sub(r"(?is)\b(bom|boa)\s+(dia|tarde|noite)\b\s*[,.!]?\s*", "", t)
    t = _RE_CORTA_PRECO_CONSULTA.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.;:?!")
    return t


def resumo_dor_para_copy(dor: str, *, max_len: int = 120) -> str:
    """
    Limpa `resumo_dor` antes de interpolar em prompts ou fallbacks (evita eco de WhatsApp
    tipo "já estou te seguindo", typos "com doi", ou colagem inteira da 1ª mensagem no Node 6).
    """
    s = (dor or "").strip()
    if not s:
        return "esse peso que você trouxe"
    s = _RE_CORTA_APOS_STALK.sub("", s)
    s = _RE_LIXO_ECOU_DOR_COPY.sub("", s)
    s = _strip_colagem_whatsapp_em_dor(s)
    s = re.sub(r"(?i)\bcom\s+doi\b", "com dor", s)
    s = re.sub(r"(?i)\bdoi\s+a\b", "dor e a", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rsplit(" ", 1)[0] + "…"
    if len(s) < 8:
        return "esse peso que você trouxe"
    return s


# Modelo cola a 1ª mensagem do WhatsApp no meio do balão (Nodes 6–8) — remove o bloco inteiro.
_RE_COLAGEM_ABERTURA_NO_MEIO = re.compile(
    r"(?is)\b(boa\s+(?:tarde|noite|dia)\s+cigana\s+esmeralda,\s*me\s+chamo\s+[A-Za-zÀ-ú']+,.*?quanto\s+custa\s+[^.?!…]+[.?!…]?)"
)
_RE_COLAGEM_ABERTURA_NO_MEIO_ALT = re.compile(
    r"(?is)\b(boa\s+(?:tarde|noite|dia)\s*,?\s*cigana\s+esmeralda.*?quanto\s+custa[^.?!…]*[.?!…]?)"
)


def limpar_colagem_primeira_msg_whatsapp_em_texto(
    s: str, *, substituto: str = "esse pedido que você trouxe"
) -> str:
    """
    Remove trechos onde a IA reproduziu a abertura típica (saudação + apresentação + ex + preço).
    Mantém a frase legível para o lead (substituto curto).
    """
    t = (s or "").strip()
    if not t:
        return t
    t = _RE_COLAGEM_ABERTURA_NO_MEIO.sub(substituto, t)
    t = _RE_COLAGEM_ABERTURA_NO_MEIO_ALT.sub(substituto, t)
    return re.sub(r"\s{2,}", " ", t).strip()


def desabafo_para_prompt_ia(desabafo: str, *, max_len: int = 1200) -> str:
    """
    Desabafo para prompts (Nodes 3–5, 4): remove saudação/apresentação/preço do início
    e limita tamanho. Não altera o valor bruto guardado em metadata.
    """
    s = (desabafo or "").strip()
    if not s:
        return ""
    s = _strip_colagem_whatsapp_em_dor(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len] if s else ""


def nome_lead_para_exibicao(nome_raw: str) -> str:
    """
    Vocativo seguro para balões (Node 6+): nunca uma frase inteira colada no campo nome.
    """
    raw = (nome_raw or "").strip()
    if not raw:
        return VOCATIVO_SEM_NOME
    low = raw.lower()
    if low == "meu bem":
        return "meu bem"
    if low == "meu anjo":
        return "meu anjo"
    if len(raw) > 42 or "," in raw or "?" in raw:
        return VOCATIVO_SEM_NOME
    toks = raw.split()
    if not toks:
        return VOCATIVO_SEM_NOME
    first = toks[0].lower().strip(".,;:!?")
    if first in ("boa", "olá", "ola", "oi", "bom"):
        return VOCATIVO_SEM_NOME
    if len(toks) > 4:
        return VOCATIVO_SEM_NOME
    return toks[0].strip().capitalize()


def contexto_lead_para_nodes(
    nome_lead_raw: str,
    meta: Optional[Mapping[str, Any]],
    *,
    dor_max_len: int = 90,
    desabafo_max_len: int = 1200,
) -> Dict[str, str]:
    """
    Dados do lead seguros para qualquer node (prompts, fallbacks, interpolação em balões).

    - nome_fmt: primeiro nome / vocativo curto (nunca colar mensagem inteira no lugar do nome).
    - resumo_dor_safe: dor higienizada (via resumo_dor_para_copy).
    - desabafo_prompt: desabafo limpo para contexto de IA (sem abertura comercial genérica).
    """
    m = dict(meta or {})
    nome = (nome_lead_raw or "").strip() or VOCATIVO_SEM_NOME
    return {
        "nome_fmt": nome_lead_para_exibicao(nome),
        "resumo_dor_safe": resumo_dor_para_copy(
            str(m.get("resumo_dor") or ""), max_len=dor_max_len
        ),
        "desabafo_prompt": desabafo_para_prompt_ia(
            str(m.get("desabafo_original") or ""), max_len=desabafo_max_len
        ),
    }


def extrair_evidencias_conversa(
    *,
    texto_atual: str,
    tipo_mensagem_atual: str,
    historico: List[Any],
    metadata: Optional[Mapping[str, Any]] = None,
    nome_lead: str = "",
) -> Dict[str, bool]:
    """
    Consolida evidências recentes para evitar perguntas redundantes.
    Usado pelo engine como camada global antes do envio.
    """
    m = dict(metadata or {})
    txt = (texto_atual or "").strip().lower()
    tp_atual = (tipo_mensagem_atual or "").strip().lower()
    nome_ok = nome_util_para_checklist_fase1(nome_lead or "")
    nome_confirmado_chat = bool(m.get("nome_confirmado_chat"))
    contato_ritual_ok = contato_salvo_ou_declarado(m, texto_atual or "")
    confirmou_agora = bool(
        re.search(r"\b(ok|sim|pronto|feito|salvei|t[áa]\s+salvo|já\s+salvei|ja\s+salvei|isso\s+mesmo)\b", txt, re.I)
    )
    confirmou_comercial_agora = bool(
        re.search(r"\b(firmo|fechado|confirmo|pode\s+mandar|manda\s+o\s+link|quero\s+fechar)\b", txt, re.I)
    )
    node8_fase_esperando_firmo = str(m.get("node8_fase") or "").strip().lower() == "esperando_firmo"
    tem_foto = bool(m.get("foto_recebida")) or tp_atual in {"image", "video"}
    tem_desabafo = bool(m.get("desabafo_recebido"))
    tem_desejo = bool((m.get("desejo_declarado") or "").strip())
    if m.get("node3_estado") == "aguardando_desejo":
        tem_desejo = False

    tem_aprofundamento = bool((m.get("aprofundamento_texto") or "").strip())
    if m.get("node3_estado") == "aguardando_aprofundamento":
        tem_aprofundamento = False

    for msg in reversed((historico or [])[-18:]):
        rem = getattr(msg, "remetente", None) or (msg.get("remetente") if isinstance(msg, dict) else "")
        if rem != "user":
            continue
        tpm = str(getattr(msg, "tipo", None) or (msg.get("tipo") if isinstance(msg, dict) else "text")).lower()
        txm = str(getattr(msg, "texto", None) or (msg.get("texto") if isinstance(msg, dict) else "")).strip().lower()
        if tpm in {"image", "video"}:
            tem_foto = True
        if not tem_desabafo and len(txm.split()) >= 6 and re.search(
            r"\b(dor|sofr|ang[uú]st|medo|ex|relacion|dinheiro|ansiedade|cansad|piloto)\w*\b",
            txm,
            re.I,
        ):
            tem_desabafo = True
        if not confirmou_agora and re.search(r"\b(ok|sim|pronto|feito|isso\s+mesmo)\b", txm, re.I):
            confirmou_agora = True

    return {
        "nome_ok": nome_ok,
        "nome_confirmado_chat": bool(nome_confirmado_chat),
        "contato_ritual_ok": bool(contato_ritual_ok),
        "tem_foto": bool(tem_foto),
        "tem_desabafo": bool(tem_desabafo),
        "tem_desejo": bool(tem_desejo),
        "tem_aprofundamento": bool(tem_aprofundamento),
        "confirmou_agora": bool(confirmou_agora),
        "confirmou_comercial_agora": bool(confirmou_comercial_agora),
        "node8_fase_esperando_firmo": bool(node8_fase_esperando_firmo),
    }


def motivo_redundancia_texto(texto_balao: str, evidencias: Mapping[str, bool]) -> str:
    """
    Retorna motivo curto de redundância (ou string vazia) para balões que pedem dados já disponíveis.
    """
    low = (texto_balao or "").strip().lower()
    if not low:
        return ""
    if evidencias.get("nome_ok") and evidencias.get("nome_confirmado_chat") and re.search(
        r"\b(como\s+você\s+se\s+chama|qual\s+seu\s+nome|me\s+diz\s+seu\s+nome|meu\s+nome\s+[eé])\b",
        low,
        re.I,
    ):
        return "nome_ja_conhecido"
    # Contato já coberto (declaração, vCard ou texto atual) — alinhado a funnel_gates.contato_salvo_ou_declarado.
    if evidencias.get("contato_ritual_ok") and re.search(
        r"\b(salvar\s+(?:o\s+)?(?:seu\s+|teu\s+)?(?:contato|número|numero)|"
        r"salva\s+(?:na\s+)?(?:sua\s+)?agenda|adiciona\s+na\s+agenda|"
        r"guarda\s+(?:o\s+)?(?:meu\s+)?número|meu\s+cart[aã]o\s+de\s+contato)\b",
        low,
        re.I,
    ):
        return "contato_ja_tratado"
    if evidencias.get("tem_foto") and re.search(r"\b(foto|imagem)\b", low, re.I) and re.search(r"\b(palma|m[ãa]o)\b", low, re.I):
        # Se for um pedido de *outra* foto ou *nova* foto (ex. por erro na validação), não consideramos redundante
        if re.search(r"\b(manda|envia|enviar|preciso|pode\s+mandar|pode\s+enviar)\b", low, re.I):
            if not re.search(r"\b(outra|nova)\b", low, re.I):
                return "foto_ja_recebida"
    if evidencias.get("confirmou_agora") and re.search(r"\bmanda\s+um\s+(\*?ok\*?|sim)\b", low, re.I):
        return "confirmacao_ja_recebida"
    # "Conseguiu salvar, meu bem?" (node 3) contém "conseguiu salvar" mas é pergunta legítima — só suprimir
    # repetições que citam contato/número/agenda ou pedido explícito de sim após confirmação.
    if evidencias.get("confirmou_agora") and re.search(
        r"\b(conseguiu\s+salvar\s+(?:o\s+)?(?:contato|número|numero|celular|na\s+agenda)|manda\s+um\s+sim)\b",
        low,
        re.I,
    ):
        return "confirmacao_ja_recebida"
    if evidencias.get("confirmou_agora") and re.search(
        r"\b(salvou\s+(o\s+)?(número|numero|contato|celular)\s*\?|conseguiu\s+colocar\s+na\s+agenda\s*\?)\b",
        low,
        re.I,
    ):
        return "confirmacao_ja_recebida"
    if evidencias.get("tem_desabafo") and re.search(r"\b(o\s+que\s+mais\s+(aperta|d[oó]i)\s+o\s+peito|me\s+conta\s+o\s+que\s+d[oó]i)\b", low, re.I):
        return "desabafo_ja_recebido"
    if evidencias.get("tem_desejo") and re.search(r"\b(o\s+que\s+você\s+quer|qual\s+seu\s+desejo|o\s+que\s+quer\s+que\s+aconte[çc]a)\b", low, re.I):
        return "desejo_ja_recebido"
    if evidencias.get("tem_aprofundamento") and re.search(r"\b(h[aá]\s+quanto\s+tempo|o\s+que\s+voc[êe]\s+j[aá]\s+tentou)\b", low, re.I):
        return "aprofundamento_ja_recebido"
    # Equivalências de confirmação comercial/operacional:
    # se o lead acabou de confirmar, não pedir de novo "FIRMO" / "ok" / "sim".
    if (
        evidencias.get("node8_fase_esperando_firmo")
        and evidencias.get("confirmou_comercial_agora")
        and re.search(r"\b(escreve|digita|manda)\s+\*?firmo\*?\b", low, re.I)
    ):
        return "confirmacao_comercial_ja_recebida"
    # Não usar tem_foto aqui: no funil a foto é quase sempre a palma (Node 3), não comprovante
    # de PIX — isso suprimia o primeiro pedido legítimo de comprovante na oferta.
    return ""


_RE_ECO_OPERACIONAL_RESIDUAL = re.compile(
    r"(?is)\b(consulta\s+(é\s+)?paga|essa\s+consulta|quanto\s+custa|me\s+chamo|"
    r"cigana\s+esmeralda|pix|comprovante)\b"
)
# Meta-perguntas do funil que não são dor real e não devem aparecer no eco
_RE_ECO_META_PERGUNTA = re.compile(
    r"(?is)^\s*(?:quero\s+sim|sim\s*,|ok\s*,?).{0,100}(?:porque|por\s+que|pq)\b.*\?",
)


def fragmento_seguro_para_eco_fallback(texto: str, *, max_len: int = 100) -> str:
    """
    Trecho para eco no fallback do Node 6: mesmo pipeline da dor, sem colar abertura comercial
    nem pergunta de preço. Retorna vazio se só sobrar lixo operacional ou meta-comentário.
    """
    s = resumo_dor_para_copy((texto or "").strip(), max_len=max_len)
    if not s or s == "esse peso que você trouxe":
        return ""
    if _RE_ECO_OPERACIONAL_RESIDUAL.search(s):
        return ""
    if _RE_ECO_META_PERGUNTA.search(s):
        return ""
    return s


def frase_dor_contextualizada(
    dor: str,
    *,
    abertura: str = "Quando você me diz",
    fallback: str = "esse peso que você trouxe",
) -> str:
    """
    Envolve o resumo de dor em um quadro natural, evitando colagem crua no meio da frase.
    Ex.: "Quando você me diz '...'" / "Quando você traz '...'"
    """
    d = resumo_dor_para_copy(dor or "", max_len=90).strip()
    if not d:
        d = fallback
    # Evita abrir com aspas sobre aspas já presentes no texto
    d = d.strip().strip("'").strip('"').strip()
    return f"{abertura} '{d}'"


def normalizar_enxerto_dor_sem_contexto(texto: str) -> str:
    """
    Corrige frases onde a IA cola o dado bruto da dor sem contexto.
    Ex.: "bloqueio ligado a O que mais doi..." -> "bloqueio ligado ao que você me trouxe..."
    """
    t = (texto or "").strip()
    if not t:
        return ""
    t = re.sub(
        r"(?i)\bligad[oa]\s+a\s+o\s+que\s+mais\s+d[óo]i\b",
        "ligado ao que você me trouxe de dor",
        t,
    )
    t = re.sub(
        r"(?i)\bligad[oa]\s+a\s+quando\s+v[ocêe]\s+me\s+diz\b",
        "ligado ao que você me conta",
        t,
    )
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t


def primeiro_nome_exibicao(nome: str) -> str:
    """Primeiro token com capitalização simples; evita eco estranho de frases inteiras no vocativo."""
    raw = (nome or "").strip()
    if not raw or nome_eh_placeholder(raw):
        return VOCATIVO_SEM_NOME
    return raw.split()[0].strip().capitalize()


def sufixo_ancoras_node3_para_prompt(
    metadata: Optional[Mapping[str, Any]],
    *,
    max_len: int = 720,
) -> str:
    """
    Trecho opcional para `mensagem_lead` / prompts (Nodes 4–8): eco das percepções da coleta (Node 3).
    """
    s = (str((metadata or {}).get("node3_percepcoes_multas") or "")).strip()
    if not s:
        return ""
    return (
        "\n\nÂNCORAS_DA_COLETA_NODE3 (manter coerência; não repetir o mesmo texto ao lead): "
        f"{s[:max_len]}"
    )


def resolver_gatilho_emocional(
    metadata: Optional[Mapping[str, Any]] = None,
    *,
    resumo_dor_coluna: str = "",
    objecao_coluna: str = "",
) -> str:
    """
    Texto curto para ancorar recuperação / node 9 (medo, trava, dor).
    Ordem: gatilho_emocional (metadata) → objecao_silenciosa → resumo_dor → default.
    """
    m = dict(metadata or {})
    lixo = frozenset({"", "nenhuma", "none", "n/a", "ind definida", "indefinida"})

    def _limpar_gatilho(raw: str) -> str:
        t = str(raw or "").strip()
        if not t:
            return ""
        # Remove metadados/colagens comuns e separadores de concatenação.
        t = re.sub(r"[\[\]\{\}]", " ", t)
        partes = [p.strip(" .,:;|-") for p in re.split(r"\s*\|\s*|\s*\/\s*|\s*;\s*", t) if p.strip()]
        # Descarta fragmentos operacionais e ruído de navegação.
        lixo_frag = re.compile(
            r"(?i)\b("
            r"j[áa]\s*salv(ei|ou)|salvei\s+teu\s+contato|"
            r"visitei\s+teu\s+instagram|j[áa]\s+visitei|"
            r"instagram|insta\b|link\b|contato\b|"
            r"ok|sim|pronto|blz|beleza|firme|firmo|"
            r"quero\s+saber|consulta|pre[cç]o|valor"
            r")\b"
        )
        candidatas: List[str] = []
        for p in partes:
            p = re.sub(r"\s+", " ", p).strip()
            if len(p) < 6:
                continue
            if lixo_frag.search(p):
                continue
            candidatas.append(p)
        base = candidatas[0] if candidatas else (partes[0] if partes else t)
        base = re.sub(r"\s+", " ", base).strip(" .,:;|-")
        return base[:140]

    g = _limpar_gatilho(str(m.get("gatilho_emocional") or "").strip())
    if g and g.lower() not in lixo:
        return g[:140]

    obj = _limpar_gatilho(str(m.get("objecao_silenciosa") or objecao_coluna or "").strip())
    if obj and obj.lower() not in lixo:
        return obj[:140]

    dor = str(m.get("resumo_dor") or resumo_dor_coluna or "").strip()
    if dor and dor.upper() not in ("INDEFINIDA", "INDEFINIDO"):
        return resumo_dor_para_copy(dor, max_len=100)

    return "essa angústia"

# Frases saturadas / proibidas (detecção = log; substituir trechos genéricos quando possível)
_FRASES_PROIBIDAS: List[tuple[re.Pattern, str]] = [
    (re.compile(r"energia\s+negativa\s+que\s+te\s+acompanha", re.I), "..."),
    (re.compile(r"malef[ií]cios\s+graves\s+e\s+contagiosos?", re.I), "..."),
    (re.compile(r"lei\s+da\s+troca\s+energ[eé]tica", re.I), "a troca que os guias pedem"),
    (re.compile(r"resultado\s+em\s+5\s+a\s+7\s+dias?", re.I), "mudança sentida no seu ritmo"),
    (re.compile(r"isso\s+faz\s+sentido\s+para\s+voc[eê]\s*\?", re.I), "isso ressoa com você?"),
    (re.compile(r"me\s+deu\s+um\s+arrepio", re.I), "isso bateu forte aqui"),
    (re.compile(r"para\s+voc[eê]\s+especialmente\s+fa[çc]o\s+por", re.I), "para o seu caso abro"),
    (re.compile(r"\bclaro\b\s*!?", re.I), ""),
    (re.compile(r"\bcom\s+certeza\b[!.\s]*", re.I), ""),
    (re.compile(r"\bentendido\s*!?", re.I), ""),
    # Assinatura de IA / gatilhos artificiais (leitura + oferta)
    (re.compile(r"\bquase\s+um\s+eco\s+k[aá]rmico\b", re.I), "um ciclo que se repete"),
    (re.compile(r"\bé\s+um\s+padrão,\s*quase\s+um\s+eco\s+k[aá]rmico\b", re.I), "é um padrão que se repete"),
    (re.compile(r"\btessitura\s+mais\s+densa\b", re.I), "camada mais pesada"),
    (re.compile(r"\bÉ\s+aqui\s+que\s+se\s+abre\s+a\s+possibilidade\s+de\s+uma\b", re.I), "É neste ponto que entra a"),
    (re.compile(r"\bSinto\s+um\s+leve\s+tremor\s+em\s+meus\s+b[uú]zios\b[^.!?…]*[.!?…]?", re.I), ""),
    (re.compile(r"[^.!?…]*\b(?:somente\s+)?duas\s+vagas\b[^.!?…]*[.!?…]", re.I), ""),
]

# "já trabalho há 10 anos" isolado (sem complemento na mesma frase)
_RE_10_ANOS_SOZINHO = re.compile(
    r"\bj[aá]\s+trabalho\s+h[aá]\s+10\s+anos\b(?![^.?!…]{0,80}\b(caso|altar|linha|m[aã]o|cliente|pessoa|hist[oó]ria)\b)",
    re.I,
)


def delay_pre_texto(texto: str) -> int:
    """Simula digitação: base = max(4, min(len//15, 18)); variação humana."""
    t = texto or ""
    base = max(4, min(len(t) // 15, 18))
    return random.randint(max(2, base - 2), base + 3)


def delay_pre_audio(texto: str) -> int:
    """Simula gravação de áudio a partir do roteiro falado."""
    t = texto or ""
    base = max(6, min(len(t) // 12, 22))
    return random.randint(max(4, base - 2), base + 3)


def delay_escuta_pos_audio() -> int:
    return random.randint(8, 12)


def delay_entre_baloes() -> int:
    return random.randint(3, 7)


def delay_dramatico() -> int:
    """Pausa “teatral” entre blocos — faixa mais curta evita ~90s+ só em delays no Node 3."""
    return random.randint(10, 18)


# Protege URLs em sanitizar_anti_ia: inserir espaço após "." quebra https://www.instagram.com no WhatsApp.
_WP_URL_TOKEN = "__WP_HTTPS_{}__"


def _mascarar_urls_https_para_sanitizar(texto: str) -> tuple[str, list[str]]:
    """Substitui cada trecho http(s)://… por token; devolve lista na ordem para restaurar."""
    urls: list[str] = []

    def _captura(m: re.Match) -> str:
        urls.append(m.group(0))
        return _WP_URL_TOKEN.format(len(urls) - 1)

    # Trecho contíguo sem espaços (URL correta antes de sanitizar; espaços quebram preview no WhatsApp)
    s = re.sub(r"https?://[^\s<>]+", _captura, texto or "", flags=re.I)
    return s, urls


def _restaurar_urls_https_mascaradas(texto: str, urls: list[str]) -> str:
    s = texto or ""
    for i, u in enumerate(urls):
        s = s.replace(_WP_URL_TOKEN.format(i), u)
    return s


_RE_URL_HTTP_BALAO = re.compile(r"https?://\S+", re.I)


def encurtar_balao_preservando_urls(texto: str, limite: int = 170) -> str:
    """
    Encurta texto de balão sem rasgar http(s)://… (Instagram, Cakto, Kiwify, etc.).
    Cortes por último '.' na janela quebravam domínios (ex.: terminava em «.com» cortado).
    """
    t = re.sub(r"\s+", " ", str(texto or "")).strip()
    if len(t) <= limite:
        return t
    urls = _RE_URL_HTTP_BALAO.findall(t)
    if urls:
        sem_url = _RE_URL_HTTP_BALAO.sub(" ", t)
        sem_url = re.sub(r"\s+", " ", sem_url).strip()
        bloco_urls = " ".join(urls)
        sep = " " if sem_url and bloco_urls else ""
        overhead = len(sep)
        budget = limite - len(bloco_urls) - overhead
        if budget <= 0:
            return bloco_urls if len(bloco_urls) <= limite else bloco_urls[:limite]
        if len(sem_url) <= budget:
            return f"{sem_url}{sep}{bloco_urls}".strip()
        corte = sem_url[:budget]
        ult = max(corte.rfind("."), corte.rfind("?"), corte.rfind("!"))
        if ult >= min(50, budget // 3):
            corte = corte[: ult + 1]
        else:
            ws = corte.rfind(" ")
            if ws >= min(40, budget // 4):
                corte = corte[:ws].rstrip(" ,;:-")
            corte = corte.rstrip() + "..."
        return f"{corte.strip()}{sep}{bloco_urls}".strip()
    corte = t[:limite]
    ult = max(corte.rfind("."), corte.rfind("?"), corte.rfind("!"))
    if ult >= 50:
        corte = corte[: ult + 1]
    else:
        ws = corte.rfind(" ")
        if ws >= 40:
            corte = corte[:ws].rstrip(" ,;:-")
        corte = corte.rstrip() + "..."
    return corte


def compactar_url_https_monolitica(texto: str) -> str:
    """
    Se a mensagem é só um link (ou link já partido por espaços), remove espaços internos.
    Evita https://www. instagram .com no app (link não fica azul).
    """
    t = (texto or "").strip()
    if not t or "\n" in t:
        return texto or ""
    if not re.match(r"^https?://", t, re.I):
        return texto or ""
    # Heurística: não há texto humano depois do URL (evita colar "Veja" no fim)
    if re.search(r"https?://\S+\s+[A-Za-zÀ-ú]{2,}\s*$", t, re.I):
        return texto or ""
    colapsado = re.sub(r"\s+", "", t)
    if len(colapsado) >= 12 and colapsado.lower().startswith(("http://", "https://")):
        return colapsado
    return texto or ""


def normalizar_link_para_envio(raw: str, *, instagram_mode: bool = False) -> str:
    """
    Normaliza links vindos de config/.env para envio no WhatsApp.
    - Aceita texto com URL colada e extrai o primeiro http(s)://...
    - Corrige www.dominio -> https://www.dominio
    - instagram_mode: aceita @usuario e converte para https://www.instagram.com/usuario/
    - Remove pontuação de fechamento e espaços internos indevidos.
    Retorna string vazia quando não houver um link usável.
    """
    s = str(raw or "").strip().strip("\"'").strip()
    if not s:
        return ""

    # Se veio um texto com URL no meio, extrai a primeira.
    m_http = re.search(r"https?://[^\s<>]+", s, re.I)
    if m_http:
        s = m_http.group(0)
    elif re.match(r"^www\.[^\s<>]+$", s, re.I):
        s = f"https://{s}"
    elif instagram_mode:
        m_handle = re.match(r"^@?([A-Za-z0-9._]{2,30})$", s)
        if m_handle:
            s = f"https://www.instagram.com/{m_handle.group(1)}/"

    # Remove espaços internos e pontuação comum de fechamento.
    s = re.sub(r"\s+", "", s).rstrip(".,;:)]}>")
    s = compactar_url_https_monolitica(s) or s

    # Validação mínima de URL clicável.
    if re.match(r"^https?://[^\s/$.?#].[^\s]*\.[A-Za-z]{2,}([/?#].*)?$", s, re.I):
        return s
    return ""


def sanitizar_anti_ia(texto: str) -> str:
    if not texto:
        return ""
    s, urls_https = _mascarar_urls_https_para_sanitizar(texto)
    # Travessões / dash longo → reticências
    s = re.sub(r"[—–−]", "...", s)
    s = s.replace(" - ", "... ")
    # Exclamações consecutivas
    s = re.sub(r"!{2,}", "!", s)
    # Colagens comuns do modelo: falta de espaço após ponto/interrogação ou vírgula
    s = re.sub(r"([.!?])([A-Za-zÀ-ÿÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç])", r"\1 \2", s)
    s = re.sub(r"([,;])(?=[A-Za-zÀ-ÿÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç])", r"\1 ", s)
    # minúscula colada em maiúscula início de frase (ex.: "misticoEstou")
    s = re.sub(r"([a-záàâãéêíóôõúç])([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)", r"\1 \2", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Padrões chatbot
    s = re.sub(r"\bclaro\b\s*!?", "", s, flags=re.I)
    s = re.sub(r"\bcom\s+certeza\b[!.,\s]*", "", s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = _restaurar_urls_https_mascaradas(s, urls_https)
    return s


def registrar_frases_proibidas(texto: str, contexto: str = "") -> None:
    """Log estruturado; não bloqueia envio (engine já sanitizou trechos comuns)."""
    if not texto:
        return
    low = texto.lower()
    alertas = []
    for pat, _ in _FRASES_PROIBIDAS:
        if pat.search(texto):
            alertas.append(pat.pattern)
    if _RE_10_ANOS_SOZINHO.search(texto):
        alertas.append("ja_trabalho_10_anos_isolado")
    if "vó maria conga" in low or "vo maria conga" in low:
        alertas.append("vo_maria_conga")
    if re.search(r"minha\s+m[aã]e", low) and re.search(r"r\$\s*\d+|pix|dinheiro|pagar|adiant", low):
        alertas.append("minha_mae_pedido_financeiro")
    if alertas:
        logger.warning(
            "[COPY_GUARD] frase_risco_detectada context=%s padroes=%s trecho=%s",
            contexto,
            alertas,
            texto[:120].replace("\n", " "),
        )


def aplicar_substituicoes_proibidas(texto: str) -> str:
    """Substitui ocorrências conhecidas por alternativas seguras."""
    if not texto:
        return ""
    s = texto
    for pat, repl in _FRASES_PROIBIDAS:
        s = pat.sub(repl, s)
    s = _RE_10_ANOS_SOZINHO.sub("há anos cuido de casos como o seu", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return sanitizar_anti_ia(s)


def normalizar_urls_para_whatsapp(texto: str) -> str:
    """
    Melhora detecção de link no app do WhatsApp (mobile):
    remove zero-width / emoji colado antes da URL; não altera o texto sem http(s).
    Compacta mensagens que são só URL (cobre URLs já partidas antes do fix em sanitizar_anti_ia).
    """
    if not texto:
        return ""
    s = (
        (texto or "")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )
    # Emoji imediatamente antes de http(s) pode impedir tap em alguns aparelhos
    s = re.sub(r"[🔗🔒📎]\s*(?=https?://)", "", s)
    s = compactar_url_https_monolitica(s)
    return s.strip()


def preview_url_flag_para_whatsapp(texto: str) -> bool:
    """Meta Cloud API: preview_url=true ajuda o cliente a reconhecer links clicáveis."""
    return bool(re.search(r"https?://", texto or "", re.I))


def preparar_texto_envio(texto: str, contexto: str = "") -> str:
    """Pipeline único: substituições + anti-IA + URLs + log de risco."""
    raw = (texto or "").strip()
    # Mensagem só com URL: não passar por sanitizar_anti_ia (regras de espaço após "." podem degradar o link).
    if raw and re.match(r"^https?://\S+$", raw, re.I):
        x = normalizar_urls_para_whatsapp(raw)
        registrar_frases_proibidas(x, contexto)
        return x
    x = aplicar_substituicoes_proibidas(texto)
    x = normalizar_urls_para_whatsapp(x)
    registrar_frases_proibidas(x, contexto)
    return x


def linhas_balao(texto: str) -> int:
    return len([ln for ln in (texto or "").splitlines() if ln.strip()]) or (1 if texto and texto.strip() else 0)


# ── Gancho final: último balão deve convidar resposta (pergunta / CTA explícito) ──
_RE_ENCERRAMENTO_SEM_GANCHO = re.compile(
    r"(portal\s+está\s+fechado|portal\s+esta\s+fechado|fique\s+em\s+paz|que\s+a\s+luz\s+te\s+encontre|"
    r"fluxo\s+encerrado|encerramos\s+por\s+aqui|opt[-\s]?out)",
    re.I,
)


def ultimo_segmento_logico_balao(texto: str) -> str:
    """
    Último bloco antes do fatiamento por linhas (alinhado a [BALAO] / \\n\\n no engine).
    Usado para decidir se falta gancho no último balão visível.
    """
    t = (texto or "").strip()
    if not t:
        return ""
    if re.search(r"\[BALAO\]", t, re.I):
        partes = re.split(r"\[BALAO\]", t, flags=re.I)
        partes = [p.strip() for p in partes if p.strip()]
        return partes[-1] if partes else ""
    partes = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    return partes[-1] if partes else t


def texto_eh_encerramento_ou_excecao(s: str) -> bool:
    """Despedidas / opt-out: não acrescentar gancho automático."""
    low = (s or "").lower()
    if _RE_ENCERRAMENTO_SEM_GANCHO.search(low):
        return True
    if "digite encerrar" in low:
        return True
    return False


def texto_tem_gancho_conversa(s: str) -> bool:
    """
    Indica se o texto já convida resposta: pergunta, 👇, *ok*, ou CTA imperativo claro.
    """
    if not s or not s.strip():
        return False
    t = s.strip()
    if "?" in t:
        return True
    if "👇" in t or "👉" in t:
        return True
    if re.search(r"\*ok\*|'ok'|\"ok\"", t, re.I):
        return True
    if re.search(
        r"\b(manda|mande|responde|me\s+diz|diga|escreva|consegue\s+mandar|"
        r"me\s+fala|é\s+só\s+me\s+falar|pode\s+me\s+falar|fala\s+comigo|"
        r"conta\s+pra\s+mim|me\s+conta|pode\s+enviar|me\s+responde|"
        r"combinado\s*\?)",
        t,
        re.I,
    ):
        return True
    return False


def acolhimento_empatico_sem_pergunta_explicita(s: str) -> bool:
    """
    Acolhimento pós-desabafo sem "?" — não acrescentar gancho mecânico de *ok*; quebra o tom
    (coleta profunda: validar dor e seguir no próximo balão / turno com pergunta real).
    """
    u = (s or "").strip()
    if len(u) < 50 or "?" in u:
        return False
    return bool(
        re.search(
            r"\b(sinto|percebo|escuto|sinto\s+a|for[çc]a\s+dessas|"
            r"palavras\s+que\s+v[eê]m|v[eê]m\s+do\s+peito|"
            r"medo\s+que\s+tenta|energia\s+do\s+medo|"
            r"busca\s+por\s+um\s+caminho|caminho\s+mais\s+leve|"
            r"guardo\s+com\s+respeito|li\s+o\s+que\s+voc[êe]\s+mandou)\b",
            u,
            re.I,
        )
    )


def garantir_gancho_ultimo_texto_acao(conteudo: str, contexto: str = "") -> str:
    """
    Se o último segmento lógico não tiver gancho, acrescenta pergunta curta.
    Não altera mensagens de encerramento ou opt-out.
    """
    # Gancho mecânico global removido: transições/perguntas devem ser construídas
    # de forma contextual nos próprios nodes.
    raw = (conteudo or "").strip()
    return raw


def aplicar_gancho_na_lista_acoes(acoes: List[Any]) -> List[Any]:
    """
    Ajusta a última ação `text` da lista para terminar com gancho de resposta.
    Use `acao.metadata['skip_gancho_final'] = True` para preservar copy intencional.
    """
    if not acoes:
        return acoes
    for i in range(len(acoes) - 1, -1, -1):
        a = acoes[i]
        if getattr(a, "tipo", "") != "text":
            continue
        cont = (getattr(a, "conteudo", "") or "").strip()
        if not cont:
            continue
        meta = getattr(a, "metadata", None)
        if isinstance(meta, dict) and meta.get("skip_gancho_final"):
            continue
        nuevo = garantir_gancho_ultimo_texto_acao(a.conteudo, "lista_acoes")
        if nuevo != a.conteudo:
            a.conteudo = nuevo
        break
    return acoes


# Padrão compartilhado com nodes 2–5 (fim de frase “aberta” / truncada pela IA)
BALAO_IA_REGEX_CORTE_FINAL = (
    r"([,;:\-]|\b(?:a|ao|as|e|é|eh|éh|foi|o|os|se|à|em|mas|ou|um|uma|que|de|do|da|com|por|para|sem|são|tão|tbm|"
    r"também|esse|essa|isso|isto|nele|nela|nisso|nisto|meu|seu|sua|minha))\s*$"
)


def tentar_salvar_balao_ia_cortado(texto: str, regex_corte_fatal: str) -> str:
    """
    Recupera balões que a IA cortou no meio: remove vírgula inicial; corta no último .?!…/emoji
    com sentido fechado; ou fecha com reticências para passar na validação de pontuação.
    """
    t = (texto or "").strip()
    t = re.sub(r"^[,;:\s]+", "", t)
    if len(t) < 6:
        return t
    # Nunca “cortar” no último ponto de um URL — rfind('.') pegava o . de instagram.com e eliminava o path.
    if re.match(r"^https?://\S+$", t, re.I):
        return t
    low = t.lower()
    aberto = bool(re.search(regex_corte_fatal, low))
    pont_ok = bool(
        re.match(
            r".*[.\!\?…\u2600-\u26FF\u2700-\u27BF\U0001f300-\U0001faff]\s*$",
            t,
        )
    )
    if not aberto and pont_ok:
        return t

    best = -1
    for sep in (".", "?", "!", "…"):
        i = t.rfind(sep)
        if i > best:
            best = i
    for sep in ("✨", "🙏", "💫", "🔮", "👇"):
        i = t.rfind(sep)
        if i > best and i >= 12:
            best = i
    if best >= 18:
        cand = t[: best + 1].strip()
        if len(cand) >= 15 and not re.search(regex_corte_fatal, cand.lower()):
            return cand

    out = t.rstrip()
    if not re.match(
        r".*[.\!\?…\u2600-\u26FF\u2700-\u27BF\U0001f300-\U0001faff]\s*$",
        out,
    ):
        out = out + "…"
    return out


def remover_marcadores_bloco_ia_vazados(texto: str) -> str:
    """
    Remove BLOCO_N:: que vazaram para o texto do balão (IA colou marcador no meio do parágrafo).
    Rede de segurança após parse nos nodes 6/7/8.
    """
    if not texto or not texto.strip():
        return ""
    t = re.sub(r"\s*BLOCO[_\s]*\d+\s*::\s*", " ", str(texto).strip(), flags=re.I)
    return re.sub(r"\s{2,}", " ", t).strip()


def parse_blocos_leitura_ia(
    texto: str,
    *,
    max_bloco: int,
    min_len: int = 8,
) -> Dict[int, str]:
    """
    Extrai BLOCO_1:: … BLOCO_N:: (também aceita BLOCO 1::) da saída estruturada da IA — Nodes 6 e 7.

    Aceita **uma linha por bloco** (legado) ou **texto do bloco continuando nas linhas seguintes**
    até o próximo marcador BLOCO_M:: — necessário para leituras longas sem truncar o primeiro
    segmento na mesma linha.

    Quando a IA cola ``...frase. BLOCO_2::`` na mesma linha, insere quebra antes do marcador
    para não juntar dois blocos num único balão com marcador visível.
    """
    out: Dict[int, str] = {}
    if not texto or not texto.strip():
        return out
    limpo = re.sub(r"`{3}(?:json|text)?|`{3}", "", texto)
    limpo = limpo.replace("\r\n", "\n").replace("\r", "\n")
    limpo = re.sub(r"(?<=\S)\s+(?=BLOCO[_\s]*\d+\s*::)", "\n", limpo, flags=re.I)
    lines = limpo.splitlines()
    current_key: Optional[int] = None
    current_buf: List[str] = []

    def _flush() -> None:
        nonlocal current_key, current_buf
        if current_key is None or not current_buf:
            current_key = None
            current_buf = []
            return
        val = "\n".join(current_buf).strip().strip('"').strip("'")
        if 1 <= current_key <= max_bloco and len(val) >= min_len:
            out[current_key] = val
        current_key = None
        current_buf = []

    for line in lines:
        line_stripped = line.strip()
        m = re.match(r"(?i)BLOCO[_\s]*(\d+)\s*::\s*(.*)$", line_stripped)
        if m:
            _flush()
            try:
                num = int(m.group(1))
            except (ValueError, IndexError):
                continue
            rest = (m.group(2) or "").strip()
            if 1 <= num <= max_bloco:
                current_key = num
                current_buf = [rest] if rest else []
            else:
                current_key = None
                current_buf = []
        elif current_key is not None and line_stripped:
            current_buf.append(line_stripped)
    _flush()
    return out


def quebrar_por_linhas_max(texto: str, max_linhas: int = MOBILE_MAX_LINHAS_BALO) -> List[str]:
    """Fatiar por parágrafos; se um parágrafos tiver mais de `max_linhas` linhas com texto, fatia em blocos."""
    if not texto or not texto.strip():
        return []
    out: List[str] = []
    for para in re.split(r"\n\s*\n", texto.strip()):
        # Nunca fatiar no meio de uma URL (quebrava link no celular)
        if re.search(r"https?://", para, re.I):
            out.append(para.strip())
            continue
        lines = para.splitlines()
        nontrivial = [ln for ln in lines if ln.strip()]
        if len(nontrivial) <= max_linhas:
            out.append(para.strip())
            continue
        buf: List[str] = []
        count = 0
        for ln in lines:
            if ln.strip():
                count += 1
            buf.append(ln)
            if count >= max_linhas:
                out.append("\n".join(buf).strip())
                buf = []
                count = 0
        if buf:
            out.append("\n".join(buf).strip())
    return [x for x in out if x]


def fatiar_texto_ritmo_celular(
    texto: str,
    *,
    max_linhas_visuais: int = MOBILE_MAX_LINHAS_BALO,
    chars_por_linha: int = MOBILE_CHARS_POR_LINHA,
) -> List[str]:
    """
    Divide um texto longo em vários balões curtos (ritmo WhatsApp no celular).
    Estima linhas por comprimento quando não há quebras explícitas.
    """
    t = (texto or "").strip()
    if not t:
        return []
    if re.search(r"https?://", t, re.I):
        return [t]
    max_chars = max(100, int(max_linhas_visuais) * int(chars_por_linha))
    # Já cabe num balão “curto”
    linhas_reais = len([ln for ln in t.splitlines() if ln.strip()])
    if len(t) <= max_chars and linhas_reais <= max_linhas_visuais:
        return [t]
    # Normaliza quebras internas para um fluxo de frases
    flat = re.sub(r"\s+", " ", t).strip()
    frases = re.split(r"(?<=[.!?…])\s+", flat)
    frases = [f.strip() for f in frases if f.strip()]
    if not frases:
        return [t]
    out: List[str] = []
    buf: List[str] = []

    for fr in frases:
        if not buf:
            buf = [fr]
            continue
        merged = " ".join(buf + [fr])
        est_lines = max(1, (len(merged) + chars_por_linha - 1) // chars_por_linha)
        if len(merged) > max_chars or est_lines > max_linhas_visuais:
            out.append(" ".join(buf).strip())
            buf = [fr]
        else:
            buf.append(fr)
    if buf:
        out.append(" ".join(buf).strip())
    # Frase única gigante: corta na fronteira de palavra mais próxima
    out2: List[str] = []
    for chunk in out:
        if len(chunk) <= max_chars + 20:
            out2.append(chunk)
            continue
        start = 0
        while start < len(chunk):
            end = start + max_chars
            if end >= len(chunk):
                out2.append(chunk[start:].rstrip())
                break
            # Recua até o último espaço para não cortar no meio de palavra
            boundary = chunk.rfind(" ", start, end)
            if boundary > start:
                out2.append(chunk[start:boundary].rstrip())
                start = boundary + 1
            else:
                # Palavra gigante sem espaço: corta forçado
                out2.append(chunk[start:end].rstrip())
                start = end
    return [x for x in out2 if x]


def unificar_vocativos_por_genero(texto: str, genero: str, nome_fmt: str = "") -> str:
    """
    Evita misturar "meu bem" e "meu anjo" na mesma sequência: um padrão por gênero.
    nome_fmt só evita substituir dentro de nomes próprios compostos (heurística leve).
    """
    if not texto:
        return ""
    g = (genero or "").strip().lower()
    t = texto
    if g == "feminino":
        t = re.sub(r"\b[Mm]eu bem\b", "meu anjo", t)
    elif g == "masculino":
        t = re.sub(r"\b[Mm]eu anjo\b", "meu filho", t)
        t = re.sub(r"\b[Mm]eu bem\b", "meu filho", t)
    else:
        t = re.sub(r"\b[Mm]eu anjo\b", "meu bem", t)
    return t


# ── Shared node utilities (nodes 6, 7, 8) ─────────────────────────────────────

_RE_RUIDO_CURTO_HIST = re.compile(
    r"(?i)^(ok|sim|oi|opa|pronto|blz|beleza|ta|tá|show|feito|entendi|combinado|👍|🙏|👀)$"
)


def _e_somente_link(texto: str) -> bool:
    t = re.sub(r"[\s🔗🔒📎]+", "", (texto or "").strip())
    return t.startswith("http://") or t.startswith("https://")


def assinar_semantica_curta(texto: str) -> str:
    t = re.sub(r"[^a-z0-9\s]", " ", (texto or "").lower())
    toks = [w for w in t.split() if len(w) > 2]
    if not toks:
        return ""
    return " ".join(toks[:8])


def limpar_meta_textual(v: str, max_len: int = 220) -> str:
    t = " ".join((v or "").split()).strip()
    if not t:
        return ""
    if t.upper() in {"INDEFINIDO", "NONE", "NULL", "N/A"}:
        return ""
    return t[:max_len]


def historico_limpo_para_ia(ctx, *, ruido_max_palavras: int = 3, limite: int = 20) -> list:
    base = slice_historico_para_ia(ctx, limite)
    if not base:
        return []
    out = []
    for h in base:
        txt = getattr(h, "texto", None) or (h.get("texto") if isinstance(h, dict) else None) or ""
        t = str(txt).replace("|", " ").strip()
        t = re.sub(r"\s+", " ", t).strip()
        if not t:
            continue
        if len(t.split()) <= ruido_max_palavras and _RE_RUIDO_CURTO_HIST.match(t.lower()):
            continue
        rem = getattr(h, "remetente", None) if not isinstance(h, dict) else h.get("remetente")
        tip = getattr(h, "tipo", "text") if not isinstance(h, dict) else h.get("tipo", "text")
        out.append({"remetente": rem or "", "texto": t, "tipo": tip or "text"})
    return out


def extrair_blocos_fallback(
    texto: str,
    max_blocos: int,
    *,
    min_len: int = 8,
    filtrar_links: bool = False,
    strip_bullets: bool = False,
) -> list:
    t = (texto or "").strip()
    if not t:
        return []
    partes = re.split(r"\[?BAL[AÃ]O\]?", t, flags=re.I)
    out: list = []
    for p in partes:
        p = re.sub(r"`{3}(?:json|text)?|`{3}", "", p).strip()
        if not p:
            continue
        lines = p.splitlines() if "\n" in p else [p]
        for ln in lines:
            ln2 = ln.strip()
            if strip_bullets:
                ln2 = ln2.strip("-•* ").strip()
            ln2 = re.sub(r"^\s*BLOCO[_\s]*\d+\s*::\s*", "", ln2, flags=re.I).strip()
            if len(ln2) >= min_len:
                if filtrar_links and _e_somente_link(ln2):
                    continue
                out.append(ln2)
            if len(out) >= max_blocos:
                break
        if len(out) >= max_blocos:
            break
    return out[:max_blocos]
