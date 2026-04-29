"""
flows/fase_1_saudacao/node_1_apresentacao.py — Node 1 (apresentação / AcassIA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A CHEGADA DA AUTORIDADE — Lead primeiro, funil em segundo; menos fallback por truncamento.

Contrato: JSON hierárquico (personalizer) + pipeline anti-corte; fallback estável sem IA.
Guardrails: `scripts/teste_node1_guardrails.py` (≤4 balões, ≤210 chars, prox 2 ou 3).
"""

import logging
import random
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from copy_sanitizer import preparar_texto_envio, tentar_salvar_balao_ia_cortado, BALAO_IA_REGEX_CORTE_FINAL
from schema import Acao, slice_historico_para_ia
from flows.funnel_gates import (
    nome_eh_placeholder,
    pode_burst_coleta_sem_node2,
    VOCATIVO_SEM_NOME,
)
from analytics.dare_copy_engine import (
    classificar_desejo_tipo,
    hook_abertura_para_prompt,
    _DESIRE_MAP,
)

logger = logging.getLogger(__name__)

# ── CONFIGURAÇÕES E REGEX DE SEGURANÇA ──
# Não use "ana" isolado: casa dentro de "cigana" e força IA em toda saudação ao bot.
_GATILHOS_DINAMICOS = ["valor", "preço", "preco", "custa", "pago", "ajuda", "desesperad", "dor"]
_RUIDO_INICIAL = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]

# 🛡️ PONTUAÇÃO OBRIGATÓRIA: Garante conclusão mística com pontuação ou emoji
_PONTUACAO_VALIDA = r".*[.\!\?…\u2600-\u26FF\u2700-\u27BF\U0001f300-\U0001faff]\s*$"
_MAX_CHARS_BALAO_NODE1 = 210
_MAX_CHARS_BALAO_A = 180
_MAX_CHARS_BALAO_B = 170
_MAX_CHARS_BALAO_CTA = 140
_MAX_BALOES_NODE1 = 4

# Sinais emocionais: espelhar em D/extra só se aparecerem na mensagem do lead
_RE_DOR_OU_SOFRIMENTO = re.compile(
    r"\b(dor(es)?|dói|doi|sofr\w*|ang[uú]stia|ansiedade|desesper\w*|destru[ií]\w*|"
    r"choro|triste|medo|n[aã]o\s+aguento|acab\w*|cansad\w*|vazio|solid[aã]o)\b",
    re.IGNORECASE,
)

# ── PROMPT NODE 1: JSON hierárquico + briefing comportamental ──
_SYSTEM_NODE1_JSON = """Você é Esmeralda Ácassia (Cigana Esmeralda), atendimento por WhatsApp no nosso instituto de luz chamado Meu Mistério.

TOM DE OURO (imitar este ritmo, sem copiar palavra por palavra se o briefing pedir outra coisa):
- A_saudacao: saudação do período + prazer em receber no instituto de luz chamado Meu Mistério + bem-vindo + ✨
- B_apresentacao: "Me chamo Esmeralda Ácassia, sou cigana e te atendo por aqui nesse templo com calma, respeito e presença de verdade." (variação leve permitida; sem travessão —; sem tom de telemarketing)
- Se vaga ativa: um balão acolhedor sobre última vaga da consulta inicial e linhas, calma (como conversa, não como anúncio)
- C_nome (se sem nome): "Me diz como você se chama, meu bem? Assim eu te falo direito."
- D: transição humana; se C já pediu o nome, D pode ser curto ou integrar o convite sem repetir vaga

HIERARQUIA FIXA (ordem dos campos = ordem dos balões). Siga o BRIEFING no final da mensagem do usuário.

ANTI-REPETIÇÃO (obrigatório):
- O nome do lugar é um só: instituto de luz chamado Meu Mistério (não use mais "Templo de Luz" nem "Instituto" separado como segundo lugar). Esse bloco institucional pode aparecer no MÁXIMO em UM balão entre extra, A_saudacao e B_apresentacao (uma vez no turno).
- Se A_saudacao já deu as boas-vindas ao instituto, B_apresentacao NÃO repete: fale só de você (Esmeralda), seu jeito de conduzir, leitura das linhas, calma.
- extra (se existir) acolhe tema do lead (amor, preço, medo, vaga) em 1–2 frases; NÃO copie o mesmo parágrafo de boas-vindas de A.

- extra: string ou null.
  * Preencha se houver dúvida (preço, amor, medo) OU se o lead trouxe dor/sofrimento explícito: 1–2 frases que RETOMEM as palavras DELE.
  * Pode mencionar a última vaga gratuita aqui se o briefing pedir (em vez de repetir instituição).
  * Se for só saudação e nome, pode ser null.

- A_saudacao: obrigatório. Saudação calorosa + UMA vez a boas-vindas ao espaço (ex.: prazer em te receber no nosso instituto de luz chamado Meu Mistério), neste balão só.
  * Duas frases curtas OU um parágrafo fluido (até ~45 palavras). Use o nome se souber.

- B_apresentacao: obrigatório. Quem você é: Esmeralda Ácassia, cigana, tom e como acompanha o lead — SEM repetir o instituto nem o nome Meu Mistério (já ditos em A ou extra).
  * Uma ou duas frases completas (até ~45 palavras). Frase inteira, sem cortar.

- C_nome: null se o primeiro nome já veio; senão pergunta humana pelo nome (ex.: "Me diz como você se chama, meu bem? Assim eu te falo direito.").

- D_confirmacao: null se C_nome já fechou com pergunta pelo nome; senão transição curta com cara de leitura (não anúncio duplicado).
  * Se extra, A ou B já falaram de vaga gratuita, consulta inicial ou "última vaga", D NÃO pode repetir isso: só convite curto ao próximo passo da leitura (ex.: seguir com calma, um sim).
  * Se o BRIEFING disser que há dor/sofrimento, a transição DEVE ecoar isso com as palavras do lead (sem repetir pitch de vaga se já foi dito).
  * Se o BRIEFING disser que NÃO há dor, não mencione dor.
  * Varie o convite conforme o contexto (preço, amor, neutro). Pode usar 👇.

CONSULTA INICIAL: ver as linhas da mão é gratuita. Não invente outros preços nem links.

GÊNERO: se o nome ou a mensagem do lead indicar claramente masculino ou feminino, concorde adjetivos e pronomes (ele/ela). Se estiver ambíguo, use "você" e evite "meu anjo" até ter certeza.

{instrucao_vaga}

PROIBIDO: travessão — ; inventar dor que o lead não disse; texto raso de uma linha só em A ou B; repetir o bloco institucional em mais de um campo.

CONTEXTO LOCAL: período no Brasil = {periodo}.
"""


def _node1_vaga_settings(metadata: Optional[dict]) -> Dict[str, object]:
    """Lê CLIENTE_NODE1_VAGA_GRATIS / COPY injetados em metadata['__config__']."""
    default: Dict[str, object] = {"ativo": True, "texto_override": ""}
    if not isinstance(metadata, dict):
        return default
    cfg = metadata.get("__config__")
    if not isinstance(cfg, dict):
        return default
    ng = cfg.get("node1_vaga_gratis")
    if not isinstance(ng, dict):
        return default
    return {
        "ativo": bool(ng.get("ativo", True)),
        "texto_override": (ng.get("texto_override") or "").strip(),
    }


def _montar_instrucao_vaga_system(metadata: Optional[dict]) -> str:
    """Parágrafo para o system prompt (liga/desliga vaga gratuita)."""
    vs = _node1_vaga_settings(metadata)
    if not vs.get("ativo", True):
        return (
            "VAGA GRATUITA: desativada na configuração. "
            "NÃO mencione última vaga, escassez de vaga nem promoção de vaga neste turno."
        )
    override = (vs.get("texto_override") or "").strip()
    if override:
        return (
            "VAGA GRATUITA (use com naturalidade, no máximo uma vez no texto todo): "
            f"{override} "
            "Pode encaixar em A_saudacao, extra ou D_confirmacao; não repita a mesma ideia em todos os campos."
        )
    return (
        "VAGA GRATUITA: com acolhimento, diga que o lead conseguiu garantir a última vaga gratuita "
        "para a consulta inicial (leitura das linhas da mão). "
        "Tom humano, sem parecer propaganda agressiva. "
        "Prefira encaixar em extra ou D_confirmacao; se usar em A, não repita o bloco do instituto no mesmo balão da vaga (evite duplicado)."
    )


def _linha_briefing_vaga(metadata: Optional[dict]) -> str:
    """Uma linha no briefing para o modelo obedecer."""
    vs = _node1_vaga_settings(metadata)
    if not vs.get("ativo", True):
        return "[VAGA] Não mencionar vaga gratuita / última vaga (desligado na config)."
    override = (vs.get("texto_override") or "").strip()
    if override:
        return f"[VAGA GRATUITA] {override}"
    return (
        "[VAGA GRATUITA] A ideia da vaga/consulta inicial gratuita aparece no MÁXIMO uma vez no turno (extra OU A OU B; se já foi dita, D só pede um sim, sem falar de vaga de novo). "
        "Não empilhe com o mesmo texto de boas-vindas institucional de A (sem repetir o instituto de luz Meu Mistério)."
    )


def _frase_vaga_curta_fallback(metadata: Optional[dict]) -> str:
    """Balão extra no fallback quando a IA falha e a vaga está ativa."""
    vs = _node1_vaga_settings(metadata)
    if not vs.get("ativo", True):
        return ""
    override = (vs.get("texto_override") or "").strip()
    if override:
        return override if len(override) < 400 else override[:397] + "..."
    return (
        "Você conseguiu garantir a última vaga gratuita pra consulta inicial, pra gente ver as tuas linhas."
    )


def _trecho_espelhar(msg_raw: str, msg_low: str) -> str:
    """Trecho curto da fala do lead para referência (dor, etc.)."""
    raw = (msg_raw or "").strip()
    if len(raw) <= 160:
        return raw
    m = _RE_DOR_OU_SOFRIMENTO.search(msg_low)
    if m:
        start = max(0, m.start() - 35)
        end = min(len(raw), m.end() + 55)
        trecho = raw[start:end].strip()
        if len(trecho) > 140:
            trecho = trecho[:137].rsplit(" ", 1)[0] + "..."
        return trecho
    return raw[:120].rsplit(" ", 1)[0] + "..." if len(raw) > 120 else raw


def _briefing_comportamental(
    msg_raw: str, msg_lead: str, nome: str, metadata: Optional[dict] = None,
) -> str:
    """Regras explícitas: o que espelhar, o que não inventar."""
    low = (msg_lead or "").lower()
    tem_dor = bool(_RE_DOR_OU_SOFRIMENTO.search(low))
    trecho = _trecho_espelhar(msg_raw, low) if tem_dor else ""

    tem_preco = any(
        x in low for x in ("preço", "preco", "valor", "custa", "quanto", "pix", "pagar", "gratis", "grátis")
    )
    tem_amor = any(
        x in low
        for x in (
            "amor",
            "namor",
            "arrumar",
            "casal",
            "relacio",
            "voltar",
            "ex",
            "trai",
            "sumiu",
            "solid",
        )
    )

    linhas: List[str] = [
        "=== BRIEFING COMPORTAMENTAL (obedeça à letra) ===",
    ]
    if tem_dor:
        linhas.append(
            f"[DOR/SOFRIMENTO] O lead expressou dor ou sofrimento. "
            f"Referência das palavras dele: «{trecho}». "
            "Em extra e/ou D_confirmacao, faça ponte com esse tema (sem inventar fatos novos)."
        )
    else:
        linhas.append(
            "[DOR] O lead NÃO falou de dor ou sofrimento explícito. "
            "NÃO use 'sei que você sofre', 'sua dor', nem angústia em A, B, extra nem D."
        )

    if tem_preco:
        linhas.append(
            "[VALOR] Há menção a preço/valor. Deixe claro: consulta inicial para ver as linhas é gratuita; "
            "não invente outros valores nem link."
        )
    if tem_amor:
        linhas.append(
            "[AMOR] Há tema afetivo. Acolha sem prometer milagre; leitura vem nas etapas seguintes. Ecoar leve em D se couber."
        )

    if nome_eh_placeholder(nome):
        linhas.append(
            "[NOME] Nome desconhecido: C_nome deve ser pergunta calorosa (não null), "
            "ex.: «Me diz como você se chama, meu bem? Assim eu te falo direito.»; D_confirmacao = null."
        )
    else:
        linhas.append(
            f"[NOME] Primeiro nome: {nome}. C_nome = null. Use o nome em A e D."
        )

    linhas.append(
        "[RICO] A_saudacao e B_apresentacao devem ter corpo (não seja telegráfica); combine acolhimento e clareza."
    )
    linhas.append(
        "[ANTI-REPETIÇÃO] No máximo um balão (A ou extra) pode citar o instituto de luz chamado Meu Mistério. "
        "Em B_apresentacao, apresente a Esmeralda sem repetir esse bloco nem o parágrafo de boas-vindas de A."
    )
    linhas.append(_linha_briefing_vaga(metadata))
    linhas.append(
        "[ANTI-DUPLICAÇÃO VAGA] Se o texto de vaga/consulta inicial já existir em extra, A ou B, D_confirmacao é só transição humana (próximo passo da leitura), sem repetir 'última vaga', 'essa leva' nem 'consulta inicial' outra vez."
    )

    # ── DARE: Hook de abertura por quebra de padrão (Schwartz nível 1-2) ──
    if tem_dor or tem_amor:
        _meta_tmp = metadata or {}
        desejo_tipo = classificar_desejo_tipo(_meta_tmp, msg_raw)
        dados_desejo = _DESIRE_MAP.get(desejo_tipo, _DESIRE_MAP["amor"])
        hook = dados_desejo["hook_frio"]
        linhas.append(
            f"[DARE HOOK] Lead chegou com contexto emocional claro. "
            f"Se usar o campo 'extra', priorize este hook de abertura como referência de tom "
            f"(adapte ao contexto real, não copie igual): \"{hook}\" — "
            "objetivo: fazer o lead sentir que Esmeralda JÁ viu algo, antes de qualquer saudação genérica. "
            "Isso é Schwartz nível 1-2: o lead não sabe que existe saída — mostre que existe, antes de pedir o nome."
        )

    return "\n".join(linhas)


def _extrair_primeiro_nome(msg_lead: str) -> Optional[str]:
    """Extrai primeiro nome comum em apresentações; evita capturar 'a'/'o' de 'eu sou a Maria'."""
    m = re.search(
        r"(?:me chamo|chamo[- ]me|sou\s+o|sou\s+a|meu nome\s+[eé])\s+([a-zà-ú]{2,24})\b",
        msg_lead,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).capitalize()
    m = re.search(r"eu sou\s+(?:a|o)\s+([a-zà-ú]{2,24})\b", msg_lead, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    m = re.search(r"eu sou\s+([a-zà-ú]{2,24})\b", msg_lead, re.IGNORECASE)
    if m:
        tok = m.group(1).lower()
        if tok in ("a", "o", "um", "uma", "de", "do", "da", "em", "no", "na"):
            return None
        return m.group(1).capitalize()
    m = re.search(r"\bmeu\s+nome\s+[eé]\s+([a-zà-ú]{2,24})\b", msg_lead, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    m = re.search(r"\bnome\s+[eé]\s+([a-zà-ú]{2,24})\b", msg_lead, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    m = re.search(r"\bnome\s+([a-zà-ú]{2,24})\b", msg_lead, re.IGNORECASE)
    if m:
        tok = m.group(1).lower()
        if tok not in ("é", "e", "meu", "seu", "dele", "dela"):
            return m.group(1).capitalize()
    return None


def _pode_ir_direto_coleta_sem_node2(ctx, nome: str, blob_ctx: str) -> bool:
    """
    Burst inicial já trouxe foto + desabafo/intenção + nome + 'salvei contato' —
    evita repetir o ritual do node 2 na mesma entrada.
    (Regra canónica: `flows.funnel_gates.pode_burst_coleta_sem_node2`.)
    """
    meta = getattr(ctx, "metadata", {}) or {}
    return pode_burst_coleta_sem_node2(meta, nome, blob_ctx)


def _blob_user_para_extrair_nome(ctx, msg_raw: str) -> str:
    """
    Mensagem atual + falas recentes do user no histórico.
    Nome/preço podem vir em outro balão quando a inbox funde tarde demais.
    """
    partes: List[str] = []
    seen: set[str] = set()
    cur = (msg_raw or "").strip()
    if cur:
        partes.append(cur)
        seen.add(cur.lower())
    for h in getattr(ctx, "historico", None) or []:
        rem = getattr(h, "remetente", None)
        if rem is None and isinstance(h, dict):
            rem = h.get("remetente")
        if rem != "user":
            continue
        t = getattr(h, "texto", None) or (h.get("texto") if isinstance(h, dict) else None) or ""
        t = str(t).strip()
        if not t or t.lower() in seen:
            continue
        seen.add(t.lower())
        partes.append(t)
    return " | ".join(partes)


_BLOCO_APRESENTACAO_PADRAO = (
    "Me chamo Esmeralda Ácassia, sou cigana e te atendo por aqui nesse templo com calma, "
    "respeito e presença de verdade."
)


def _garantir_pontuacao_final(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return s
    if re.match(_PONTUACAO_VALIDA, s):
        return s
    return s + "."


def _encurtar_balao_node1(texto: str, max_chars: int = _MAX_CHARS_BALAO_NODE1) -> str:
    """
    Evita balão longo/cortado no começo do funil.
    Preserva frases completas e corta com segurança se exceder muito.
    """
    t = " ".join((texto or "").split()).strip()
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    frases = re.split(r"(?<=[.!?…])\s+", t)
    out: List[str] = []
    total = 0
    for f in frases:
        f = (f or "").strip()
        if not f:
            continue
        extra = len(f) + (1 if out else 0)
        if total + extra > max_chars:
            break
        out.append(f)
        total += extra
    if out:
        return " ".join(out).strip()
    # Se não houver frase completa dentro do limite, não corta no meio.
    # O engine fatiará com segurança na camada de envio.
    return t


def _sanear_baloes_saida_node1(baloes: List[str]) -> List[str]:
    """
    Pipeline final anti-regressão: limpa, encurta, força pontuação, dedup e limite.
    """
    out: List[str] = []
    vistos: set[str] = set()
    for b in baloes or []:
        t = preparar_texto_envio(str(b or ""), "node1_saida_final").strip()
        if not t:
            continue
        t = tentar_salvar_balao_ia_cortado(t, BALAO_IA_REGEX_CORTE_FINAL).strip()
        # Se o texto ainda parece um vocativo/nome truncado (ex.: "Seu nome, Mag…"),
        # descarta para não vazar mensagem quebrada no primeiro contato.
        if re.search(r"(?i)\b(seu\s+nome|meu\s+nome|me\s+chamo)\b[^?!.…]{0,90}…\s*$", t):
            continue
        if re.search(r",\s*[A-Za-zÀ-ÿ]{1,4}…\s*$", t):
            continue
        t = _encurtar_balao_node1(t, _MAX_CHARS_BALAO_NODE1)
        t = _garantir_pontuacao_final(t)
        chave = re.sub(r"\s+", " ", t.lower()).strip(" .!?…")
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(t)
    return out[:_MAX_BALOES_NODE1]


def _aplicar_cap_hierarquico_node1(
    baloes: List[str], nome: str
) -> List[str]:
    """
    Caps por tipo/posição para ritmo de celular:
    - A (saudação): até 180
    - B (apresentação): até 170
    - C/D (CTA/pergunta): até 140
    """
    out: List[str] = []
    for i, b in enumerate(baloes or []):
        t = str(b or "").strip()
        if not t:
            continue
        if i == 0:
            t = _encurtar_balao_node1(t, _MAX_CHARS_BALAO_A)
        elif i == 1:
            t = _encurtar_balao_node1(t, _MAX_CHARS_BALAO_B)
        else:
            t = _encurtar_balao_node1(t, _MAX_CHARS_BALAO_CTA)
        out.append(_garantir_pontuacao_final(t))
    return out[:_MAX_BALOES_NODE1]


def _parece_eco_semantico(a: str, b: str) -> bool:
    ta = set(re.findall(r"[a-zà-ú]{4,}", (a or "").lower()))
    tb = set(re.findall(r"[a-zà-ú]{4,}", (b or "").lower()))
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    base = max(1, min(len(ta), len(tb)))
    return (inter / base) >= 0.6


def _ajustar_abertura_curta_node1(baloes: List[str], nome: str) -> List[str]:
    """
    Entrada muito curta ("oi", "olá"): reduz verbosidade para manter resposta ágil.
    Preserva: saudação + apresentação + pergunta de avanço/nome.
    """
    base = [str(b or "").strip() for b in (baloes or []) if str(b or "").strip()]
    if not base:
        return base
    # Mantém até 3 balões no topo para não parecer textão na primeira resposta.
    out = base[:3]
    if out:
        t0 = out[0].lower()
        if "preço" in t0 or "preco" in t0 or "valor" in t0:
            out[0] = "Entendo sua dúvida de valor. Vou te explicar com clareza e sem enrolação."
        elif any(k in t0 for k in ("amor", "ex", "relacion", "separ", "saudade")):
            out[0] = "Entendi o que você trouxe. Vamos tratar isso com calma e firmeza desde o início."
    texto_total = " ".join(out)
    if "?" not in texto_total and "👇" not in texto_total:
        if not nome_eh_placeholder(nome):
            out.append(f"{nome}, posso te guiar no próximo passo? 👇")
        else:
            out.append("Me diz como você se chama, meu bem? Assim eu te falo direito.")
    out = _sanear_baloes_saida_node1(out)
    out = _aplicar_cap_hierarquico_node1(out, nome)
    return out[:_MAX_BALOES_NODE1]


def _parece_truncado_apresentacao(s: str) -> bool:
    """Detecta cortes tipo 'Eu sou Esmer' ou frase sem fim."""
    t = (s or "").strip()
    if not t:
        return True
    if re.match(r"^eu\s+sou\s+esm\w{0,12}$", t, re.IGNORECASE):
        return True
    if len(t) < 80 and not re.match(_PONTUACAO_VALIDA, t):
        return True
    return False


_RE_MENCAO_VAGA_OU_CONSULTA = re.compile(
    r"(última\s+vaga|vaga\s+gratuita|vaga\s+grátis|consulta\s+inicial|"
    r"garantir\s+a|essa\s+leva|começar\s+a\s+(tua\s+)?consulta|ver\s+as\s+tuas\s+linhas)",
    re.IGNORECASE,
)


def _ja_mencionou_vaga_ou_consulta(texto: str) -> bool:
    """True se algum balão anterior já trouxe pitch de vaga/consulta/linhas nesse turno."""
    return bool(_RE_MENCAO_VAGA_OU_CONSULTA.search(texto or ""))


def _fallback_d_confirmacao(
    nome: str,
    msg_raw: str,
    msg_lead: str,
    metadata: Optional[dict] = None,
    *,
    ja_mencionou_vaga_no_turno: bool = False,
) -> str:
    """Confirmação de transição alinhada ao que o lead disse (dor, preço, neutro, vaga)."""
    low = (msg_lead or "").lower()
    tem_dor = bool(_RE_DOR_OU_SOFRIMENTO.search(low))
    tem_preco = any(
        x in low for x in ("preço", "preco", "valor", "custa", "quanto", "pix", "pagar", "gratis", "grátis")
    )
    vs = _node1_vaga_settings(metadata)
    vaga_on = bool(vs.get("ativo", True))

    if nome_eh_placeholder(nome):
        return "Quando me disser teu nome, eu te puxo pro próximo passo com calma. Como você prefere que eu te chame? 👇"

    # Tom de leitura: não repetir vaga/consulta se já foi dita em extra/A/B (evita "ridículo" duplicado).
    if ja_mencionou_vaga_no_turno:
        if tem_dor:
            return (
                f"{nome}, posso te puxar pro próximo passo com calma, a partir do que você trouxe? "
                f"Posso seguir? 👇"
            )
        if tem_preco:
            return (
                f"{nome}, quando você quiser eu te guio no próximo passo da leitura, com calma. Posso seguir? 👇"
            )
        return (
            f"{nome}, quando você estiver pronto a gente segue com calma na leitura. Posso continuar? 👇"
        )

    if tem_dor:
        if vaga_on:
            override = (vs.get("texto_override") or "").strip()
            if override:
                return (
                    f"{nome}, {override} Posso te levar pro próximo passo com calma? 👇"
                )
            return (
                f"{nome}, você garantiu a última vaga gratuita pra gente começar a consulta inicial com calma, "
                f"olhando o que você trouxe. Posso seguir? 👇"
            )
        return (
            f"{nome}, posso te levar pro próximo passo pra gente começar com calma "
            f"a olhar o que você trouxe nessa conversa? 👇"
        )
    if tem_preco:
        if vaga_on:
            override = (vs.get("texto_override") or "").strip()
            if override:
                return (
                    f"{nome}, {override} Posso te guiar no próximo passo? 👇"
                )
            return (
                f"{nome}, a consulta inicial pra ver as tuas linhas é gratuita — posso te puxar pro próximo passo? "
                f"👇"
            )
        return (
            f"{nome}, a consulta inicial pra ver tuas linhas é gratuita. "
            f"Posso te guiar no próximo passo? 👇"
        )
    if vaga_on:
        override = (vs.get("texto_override") or "").strip()
        if override:
            return f"{nome}, {override} Posso seguir contigo agora? 👇"
        return (
            f"{nome}, você garantiu a última vaga gratuita pra gente começar a tua consulta inicial. "
            f"Posso te guiar no próximo passo? 👇"
        )
    return (
        f"{nome}, posso te guiar no próximo passo agora? 👇"
    )


def _montar_baloes_do_json(
    data: Dict[str, object],
    nome: str,
    periodo: str,
    msg_raw: str = "",
    msg_lead: str = "",
    metadata: Optional[dict] = None,
) -> List[str]:
    """Monta balões na ordem: extra → A → B → C? → D (hierarquia fixa)."""
    if not data:
        return []

    extra = data.get("extra")
    if extra is not None and str(extra).strip().lower() in ("", "null", "none"):
        extra = None
    elif extra is not None:
        extra = str(extra).strip()
        if not extra:
            extra = None

    a = str(data.get("A_saudacao") or "").strip()
    b = str(data.get("B_apresentacao") or "").strip()
    c_raw = data.get("C_nome")
    d = str(data.get("D_confirmacao") or "").strip()

    if _parece_truncado_apresentacao(b) or len(b) < 20:
        b = _BLOCO_APRESENTACAO_PADRAO
    if _parece_truncado_apresentacao(a) or len(a) < 18:
        a = (
            f"{periodo}! É um prazer te receber no nosso instituto de luz chamado Meu Mistério. "
            f"Seja muito bem-vindo. ✨"
        )

    blocos: List[str] = []
    if extra:
        blocos.append(_garantir_pontuacao_final(extra))
    blocos.append(_garantir_pontuacao_final(a))
    blocos.append(_garantir_pontuacao_final(b))

    if nome_eh_placeholder(nome):
        c_txt = ""
        if c_raw is not None and str(c_raw).strip().lower() not in ("null", "none", ""):
            c_txt = str(c_raw).strip()
        if not c_txt or _parece_truncado_apresentacao(c_txt):
            c_txt = "Me diz como você se chama, meu bem? Assim eu te falo direito."
        blocos.append(_garantir_pontuacao_final(c_txt))
        # Sem D: o exemplo aprovado termina no pedido do nome (não empilhar "me responde um sim" em seguida).
        # Evita eco semântico de "extra" com A/B em entradas curtas.
        if len(blocos) >= 3 and _parece_eco_semantico(blocos[0], blocos[1]):
            blocos = blocos[1:]
        out = _sanear_baloes_saida_node1(blocos[:5])
        out = _aplicar_cap_hierarquico_node1(out, nome)
        return _deduplicar_baloes_node1(out)[:_MAX_BALOES_NODE1]

    texto_antes_d = " ".join(blocos)
    ja_vaga = _ja_mencionou_vaga_ou_consulta(texto_antes_d)

    if d and not _parece_truncado_apresentacao(d):
        if ja_vaga and _ja_mencionou_vaga_ou_consulta(d):
            d = _fallback_d_confirmacao(
                nome, msg_raw, msg_lead, metadata, ja_mencionou_vaga_no_turno=True
            )
        blocos.append(_garantir_pontuacao_final(d))
    else:
        blocos.append(
            _garantir_pontuacao_final(
                _fallback_d_confirmacao(
                    nome,
                    msg_raw,
                    msg_lead,
                    metadata,
                    ja_mencionou_vaga_no_turno=ja_vaga,
                )
            )
        )

    if len(blocos) >= 3 and _parece_eco_semantico(blocos[0], blocos[1]):
        blocos = blocos[1:]
    out = _sanear_baloes_saida_node1(blocos[:5])
    out = _aplicar_cap_hierarquico_node1(out, nome)
    return _deduplicar_baloes_node1(out)[:_MAX_BALOES_NODE1]


def _deduplicar_baloes_node1(baloes: List[str]) -> List[str]:
    """
    Reduz overload no começo do funil:
    - mantém só 1 saudação institucional;
    - mantém só 1 apresentação da Esmeralda;
    - mantém só 1 menção de vaga/consulta inicial.
    """
    out: List[str] = []
    viu_saudacao = False
    viu_apresentacao = False
    viu_vaga = False

    re_saudacao = re.compile(r"\b(bom dia|boa tarde|boa noite|prazer te receber|instituto)\b", re.I)
    re_apresentacao = re.compile(r"\b(me chamo esmeralda|sou cigana|templo)\b", re.I)
    re_vaga = re.compile(r"\b(última vaga|vaga gratuita|consulta inicial)\b", re.I)

    for b in baloes:
        low = (b or "").strip().lower()
        if not low:
            continue
        if re_saudacao.search(low):
            if viu_saudacao:
                continue
            viu_saudacao = True
        if re_apresentacao.search(low):
            if viu_apresentacao:
                continue
            viu_apresentacao = True
        if re_vaga.search(low):
            if viu_vaga:
                continue
            viu_vaga = True
        out.append(b)

    return out[:_MAX_BALOES_NODE1]


def _delay_digitacao(texto: str) -> int:
    """Simula digitação humana sem deixar abertura lenta demais."""
    if not texto:
        return 7
    t = str(texto)
    n = len(t)
    if n <= 80:
        return max(6, min(n // 14, 10))
    return max(8, min(n // 16, 20))

def _gerar_fallback(
    periodo: str,
    nome: str,
    msg_raw: str = "",
    msg_lead: str = "",
    metadata: Optional[dict] = None,
) -> List[Acao]:
    """Rede de segurança: mesma cadência do exemplo aprovado (A → B → vaga → C ou D)."""
    acoes: List[Acao] = [
        Acao(tipo="delay", segundos=random.randint(3, 6)),
        Acao(
            tipo="text",
            conteudo=(
                f"{periodo}! É um prazer te receber no nosso instituto de luz chamado Meu Mistério. "
                f"Seja muito bem-vindo. ✨"
            ),
        ),
        Acao(tipo="delay", segundos=random.randint(6, 10)),
        Acao(
            tipo="text",
            conteudo=(
                "Me chamo Esmeralda Ácassia, sou cigana e te atendo por aqui nesse templo com calma, "
                "respeito e presença de verdade."
            ),
        ),
    ]
    vaga_txt = _frase_vaga_curta_fallback(metadata)
    if vaga_txt:
        acoes.append(Acao(tipo="delay", segundos=random.randint(4, 8)))
        acoes.append(Acao(tipo="text", conteudo=vaga_txt))
    if nome_eh_placeholder(nome):
        acoes.append(Acao(tipo="delay", segundos=random.randint(6, 10)))
        acoes.append(
            Acao(
                tipo="text",
                conteudo="Me diz como você se chama, meu bem? Assim eu te falo direito.",
            )
        )
    # Sanitiza textos do fallback para manter o mesmo contrato da saída IA.
    textos = [a.conteudo for a in acoes if a.tipo == "text"]
    textos = _sanear_baloes_saida_node1(textos)
    if textos:
        novas: List[Acao] = [Acao(tipo="delay", segundos=random.randint(3, 6))]
        for t in textos:
            novas.append(Acao(tipo="delay", segundos=_delay_digitacao(t)))
            novas.append(Acao(tipo="text", conteudo=t))
        return novas
    return acoes


def _montar_baloes_contrato_node1(
    periodo: str,
    nome: str,
    metadata: Optional[dict],
    msg_raw: str = "",
    msg_lead: str = "",
) -> List[str]:
    """
    Contrato fixo do node1:
    1) saudação
    2) apresentação
    3) última consulta grátis
    4) pergunta de nome (somente se nome ausente)
    """
    low = (msg_lead or "").lower()
    tem_dor = bool(_RE_DOR_OU_SOFRIMENTO.search(low))
    tem_preco = any(x in low for x in ("preço", "preco", "valor", "custa", "quanto", "pix", "pagar", "gratis", "grátis"))
    tem_amor = any(x in low for x in ("amor", "namor", "relacio", "voltar", "ex", "saudade", "trai"))

    baloes: List[str] = [
        (
            f"{periodo}! É um prazer te receber no nosso instituto de luz chamado Meu Mistério. "
            "Seja muito bem-vindo. ✨"
        ),
        (
            "Me chamo Esmeralda Ácassia, sou cigana e te atendo por aqui nesse templo com calma, "
            "respeito e presença de verdade."
        ),
    ]
    vaga_txt = _frase_vaga_curta_fallback(metadata) or (
        "Você conseguiu garantir a última vaga gratuita pra consulta inicial, pra gente ver as tuas linhas."
    )
    if tem_preco:
        vaga_txt = "Sobre valor, fica em paz: você garantiu a última vaga gratuita pra consulta inicial."
    elif tem_dor or tem_amor:
        vaga_txt = (
            "Você garantiu a última vaga gratuita pra consulta inicial, e eu vou conduzir com calma e verdade no teu caso."
        )
    if not nome_eh_placeholder(nome):
        baloes.append(f"{nome}, {vaga_txt[:1].lower() + vaga_txt[1:]}" if len(vaga_txt) > 1 else f"{nome}, {vaga_txt}")
    else:
        baloes.append(vaga_txt)

    if nome_eh_placeholder(nome):
        baloes.append("Pra iniciarmos com calma, me diz como você se chama?")
    else:
        # Fechamento fixo do contrato (sem repetir nome no último balão).
        baloes.append("podemos iniciar?")
    out = _sanear_baloes_saida_node1(baloes)
    out = _aplicar_cap_hierarquico_node1(out, nome)
    return _deduplicar_baloes_node1(out)[:_MAX_BALOES_NODE1]


def _ponte_duvida_breve_node1(msg_raw: str) -> str:
    """
    Se o lead abriu com dúvida/pergunta, acolhe em 1 frase curta
    e volta para o checklist fixo do node1 (sem quebrar o roteiro).
    """
    t = (msg_raw or "").strip().lower()
    if not t:
        return ""
    if "?" in t or any(k in t for k in ("como", "funciona", "duvida", "dúvida", "explica", "explicar")):
        return "Eu te explico direitinho, sem enrolar. Primeiro eu te guio no comecinho pra ficar tudo certo."
    if any(k in t for k in ("preço", "preco", "valor", "quanto", "custa", "pix", "pagar")):
        return "A consulta inicial pra ver as linhas é gratuita. Já te explico os próximos passos com calma."
    return ""


def _deve_tentar_adaptive_node1(ctx, msg_raw: str, msg_lead: str) -> bool:
    """
    Decide se tenta a trilha IA JSON do Node 1.
    - safe: nunca
    - adaptive: sempre (se houver personalizer)
    - auto: só quando há contexto mínimo (evita custo em "oi" curto)
    """
    meta = getattr(ctx, "metadata", {}) or {}
    cfg = (meta.get("__config__") or {}) if isinstance(meta, dict) else {}
    modo = str(cfg.get("node1_modo_abertura") or "auto").strip().lower()
    if modo not in {"safe", "adaptive", "auto"}:
        modo = "auto"
    p = getattr(ctx, "personalizer", None)
    if not p:
        return False
    if hasattr(p, "em_cooldown_quota") and p.em_cooldown_quota():
        return False
    if modo == "safe":
        return False
    if modo == "adaptive":
        return True
    min_chars = int(cfg.get("node1_adaptive_min_chars") or 10)
    texto = (msg_raw or "").strip()
    if len(texto) >= min_chars:
        return True
    low = (msg_lead or "").lower()
    if any(g in low for g in _GATILHOS_DINAMICOS):
        return True
    if _RE_DOR_OU_SOFRIMENTO.search(low):
        return True
    # Em saudações muito curtas, mantém contrato determinístico (mais rápido e previsível).
    return False


def _garantir_fechamento_checklist_node1(
    baloes: List[str],
    nome: str,
    msg_raw: str,
    msg_lead: str,
    metadata: Optional[dict],
) -> List[str]:
    """
    Garante o fechamento mínimo do Node 1:
    - sem nome: terminar pedindo nome;
    - com nome: terminar com convite de avanço (não ficar só institucional).
    """
    out = [str(b or "").strip() for b in (baloes or []) if str(b or "").strip()]
    if nome_eh_placeholder(nome):
        pergunta_nome = "Pra iniciarmos com calma, me diz como você se chama?"
        joined = " ".join(out).lower()
        if "como você se chama" not in joined and "me diz como você se chama" not in joined:
            if len(out) >= _MAX_BALOES_NODE1:
                out[-1] = pergunta_nome
            else:
                out.append(pergunta_nome)
    else:
        convites = ("podemos iniciar", "posso seguir", "posso continuar", "próximo passo", "proximo passo")
        joined = " ".join(out).lower()
        if not any(c in joined for c in convites):
            convite = "podemos iniciar?"
            if len(out) >= _MAX_BALOES_NODE1:
                out[-1] = convite
            else:
                out.append(convite)
    out = _sanear_baloes_saida_node1(out)
    out = _aplicar_cap_hierarquico_node1(out, nome)
    return _deduplicar_baloes_node1(out)[:_MAX_BALOES_NODE1]


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    """Executa o nó de apresentação blindado contra cortes."""
    t0_node = time.time()
    # ── 1. Contexto ──
    agora = datetime.now(timezone.utc) - timedelta(hours=3)
    periodo = "Bom dia" if 5 <= agora.hour < 12 else "Boa tarde" if 12 <= agora.hour < 18 else "Boa noite"
    msg_raw = str(ctx.texto_recebido or "").strip()
    blob_ctx = _blob_user_para_extrair_nome(ctx, msg_raw)
    msg_lead = blob_ctx.lower()
    msg_limpa = re.sub(r"[^\w\s]", "", msg_lead)

    # ── 2. Name Lock ──
    nome = VOCATIVO_SEM_NOME
    nome_extraido = _extrair_primeiro_nome(blob_ctx)
    nome_ctx = str(getattr(ctx, "nome_lead", "") or "").strip()
    nome_confirmado_chat = bool((getattr(ctx, "metadata", {}) or {}).get("nome_confirmado_chat"))
    if nome_extraido:
        nome = nome_extraido
        if not hasattr(ctx, "metadata") or ctx.metadata is None:
            ctx.metadata = {}
        ctx.metadata["nome_confirmado_chat"] = True
    elif nome_confirmado_chat and nome_ctx and not nome_eh_placeholder(nome_ctx):
        # Só reutiliza nome de contexto se ele já foi confirmado em conversa.
        nome = nome_ctx.split()[0].capitalize()
    if nome != VOCATIVO_SEM_NOME:
        if not hasattr(ctx, "metadata") or ctx.metadata is None:
            ctx.metadata = {}
        ctx.metadata["nome_lead"] = nome
        ctx.nome_lead = nome

    # ── 2b. DARE: classificar desejo_tipo cedo para downstream (nodes 3, 7, 8) ──
    if not hasattr(ctx, "metadata") or ctx.metadata is None:
        ctx.metadata = {}
    if not ctx.metadata.get("desejo_tipo"):
        _desejo_tipo_node1 = classificar_desejo_tipo(ctx.metadata, blob_ctx)
        if _desejo_tipo_node1 != "amor" or any(
            kw in blob_ctx.lower()
            for kw in _DESIRE_MAP.get(_desejo_tipo_node1, {}).get("keywords", [])
        ):
            ctx.metadata["desejo_tipo"] = _desejo_tipo_node1

    # ── 3. Abertura: adaptive JSON (quando possível) -> contrato determinístico (fallback seguro) ──
    if not hasattr(ctx, "metadata") or ctx.metadata is None:
        ctx.metadata = {}
    textos_node1: List[str] = _montar_baloes_contrato_node1(
        periodo,
        nome,
        ctx.metadata,
        msg_raw=msg_raw,
        msg_lead=msg_lead,
    )
    modo_usado = "safe_contract"
    if not textos_node1:
        textos_node1 = [f"{periodo}! É bom te receber por aqui. ✨"]
        if nome_eh_placeholder(nome):
            textos_node1.append("Me diz como você se chama, meu bem? Assim eu te falo direito.")
    # Contrato rígido do node1: não comprimir para 3 balões em "oi".
    # Mantemos a sequência completa (saudação, apresentação, vaga, nome/início),
    # que foi a regra validada do funil.
    textos_node1 = _garantir_fechamento_checklist_node1(
        textos_node1,
        nome,
        msg_raw,
        msg_lead,
        ctx.metadata,
    )
    acoes_fb: List[Acao] = [Acao(tipo="delay", segundos=random.randint(2, 4))]
    for t in textos_node1:
        acoes_fb.append(Acao(tipo="delay", segundos=max(3, _delay_digitacao(t) - 1)))
        acoes_fb.append(
            Acao(
                tipo="text",
                conteudo=t,
                metadata={"skip_gancho_final": True},
            )
        )
    ctx.estado_coleta = "node1_recepcao_contrato"
    ctx.metadata["node1_baloes_enviados"] = int(len(textos_node1))
    ctx.metadata["node1_modo_abertura_usado"] = modo_usado
    ctx.metadata["node1_contrato_enviado"] = True
    if _pode_ir_direto_coleta_sem_node2(ctx, nome, blob_ctx):
        ctx.metadata["node1_pulou_para_coleta"] = True
        ctx.metadata["node2_contato_ja_reconhecido"] = True
        logger.info("⚡ [NODE 1] Contrato: burst completo → coleta (pula node 2).")
        return acoes_fb, "3_coleta_profunda"
    elapsed = time.time() - t0_node
    _cfg_fb = (ctx.metadata or {}).get("__config__") or {}
    _sla_fb = float(_cfg_fb.get("node_exec_sla_warn_seconds") or 6.0)
    if elapsed > _sla_fb:
        logger.warning(
            "⏱️ [NODE 1] Tempo fallback alto: %.2fs (sla_warn=%.2fs)",
            elapsed,
            _sla_fb,
        )
    return acoes_fb, "2_salvar_contato"