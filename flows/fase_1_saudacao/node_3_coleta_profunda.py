"""
flows/fase_1_saudacao/node_3_coleta_profunda.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLETA PROFUNDA — v15 (alinhada ao Node 1: Esmeralda Ácassia, tom templo/leitura, PT-BR).

4 camadas: foto+desabafo → desejo por universo → aprofundamento → extração.

Integração Global Sniffer (engine): `foto_recebida` / `desabafo_recebido` podem vir antes do Node 3;
o estado `inicial` adapta a copy para não repetir pedidos.

Gate por camada (máx 3 tentativas cada; depois avança com o que houver):
  Camada 1: foto validada + desabafo com substância (≥5 palavras úteis).
  Camada 2: desejo declarado (ou bypass por tentativas).
  Camada 3: tempo + tentativas já feitas (ou bypass).
  Camada 4: extração estruturada (nome_pessoa_envolvida, tempo_exato, evento_gatilho) via IA.

Fonte de verdade do estágio: meta["node3_estado"] + ctx.estado_coleta espelhado.
Barreira de memória: node3_iniciado_em + desabafo só acumula a partir daí.
"""

import logging
import random
import re
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests
from google import genai
from google.genai import types

from schema import Acao, slice_historico_para_ia
from copy_sanitizer import (
    vocativo_cigana,
    delay_dramatico,
    genero_efetivo_para_copy,
    genero_hint_para_prompt,
    nome_lead_para_exibicao,
)
from flows.funnel_gates import (
    mensagem_user_eh_midia_visual,
    meta_node3_forcar_camada1_completa,
    nome_eh_placeholder,
    VOCATIVO_SEM_NOME,
)

logger = logging.getLogger(__name__)

_MAX_TENTATIVAS_CAMADA = 3
_MAX_CHARS_BALAO_NODE3 = 210
_MAX_CHARS_NODE3_EXPLICA = 170
_MAX_CHARS_NODE3_PERGUNTA = 120


def _historico_tem_midia_usuario(ctx) -> bool:
    """Mídia do usuário já gravada no histórico (webhook de imagem pode ter corrido antes do texto)."""
    return _historico_conta_midia_usuario(ctx) > 0


def _historico_conta_midia_usuario(ctx) -> int:
    """Quantas mensagens do user são mídia visual (tipo ou URL; alinhado ao sniffer de fase 1)."""
    n = 0
    for hm in getattr(ctx, "historico", None) or []:
        if mensagem_user_eh_midia_visual(hm):
            n += 1
    return n


_SINAIS_ENVIO_FOTO = re.compile(
    r"\b(mandei|enviei|ta ai|tá aí|foto|palma|mão|mao|imagem|olha ai|segue|pronto|mande)\b", re.IGNORECASE
)
_RE_ASSUNTO_OPERACIONAL = re.compile(
    r"\b(direita|esquerda|qual\s+m[aã]o|como\s+manda|como\s+envia|como\s+enviar|n[aã]o\s+vai\s+continuar|continua|"
    r"recebeu|minha\s+foto|chegou|link|instagram|insta|audio|áudio|v[ií]deo)\b",
    re.I,
)
_RE_PRECO_DIRETO = re.compile(r"\b(pre[cç]o|valor|quanto|custa|pix|pagamento)\b", re.I)
_RE_VALOR_AFETIVO = re.compile(
    r"\b(?:homem|mulher|parceir[oa]|relacionamento|amor)\s+de\s+valor\b|\bde\s+valor\b",
    re.I,
)
_RE_MARCADORES_DOR_OU_DESEJO = re.compile(
    r"\b(d[oó]i|pesa|aperta|trav|n[oã]o\s+consigo|medo|ansiedade|sofr|ang[uú]st|"
    r"quero|preciso|gostaria|sonho|mudar|voltar|reconcil|vender|prosper|dinheiro|relacionamento|fam[ií]lia|"
    r"paz|respeito|partilha|partilhar|crescimento|companhi[ae]|escolha|afeto|carinho|lealdade|fidelidade)\b",
    re.I,
)

_RESPOSTAS_VAZIAS = frozenset({
    "ok", "sim", "não", "nao", "ta", "tá", "beleza", "blz", "certo", "entendi",
    "uhum", "hmm", "s", "pode", "vamos", "oi", "olá", "ola", "feito",
    "ja", "já", "tudo bem", "tb", "tudo bom", "sim sim", "kk", "kkk",
    "mandei", "enviei", "pronto", "aqui", "olha", "segue",
})

_SINAIS_DESISTENCIA = re.compile(
    r"\b(não|nao|não quero|nao quero|desisto|parar|sair|deixa pra lá|esquece|mentira|golpe|charlatão|encerrar)\b",
    re.IGNORECASE,
)

_REGEX_CORTE_FATAL = r"([,;:\-]|\b(?:a|ao|as|e|é|eh|éh|foi|o|os|se|à|em|mas|ou|um|uma|que|de|do|da|com|por|para|sem|são|tão|tbm|também|esse|essa|isso|isto|nele|nela|nisso|nisto|meu|seu|sua|minha))\s*$"

_PONTUACAO_VALIDA = r".*[.\!\?…\u2600-\u26FF\u2700-\u27BF\U0001f300-\U0001faff]$"

# Palavras-chave por universo (ordem: primeira correspondência vence)
_UNIVERSO_KEYWORDS: List[Tuple[str, re.Pattern]] = [
    ("amor_de_volta", re.compile(
        r"\b(ex|voltar|volta|reconcilia|sumiu|me deixou|terminou|terminamos|volta com|amor de volta)\b", re.I
    )),
    ("encontrar_amor", re.compile(
        r"\b(solteir|ninguém|ninguem|novo amor|conhecer alguém|namorar|casar|cupido|sozinha|sozinho)\b", re.I
    )),
    ("salvar_relacionamento", re.compile(
        r"\b(casamento|marido|esposa|namorad|traição|traiu|família juntos|salvar o|nosso relacionamento)\b", re.I
    )),
    ("prosperidade", re.compile(
        r"\b(dinheiro|dívida|divida|emprego|negócio|negocio|prosper|abundância|abundancia|financeir|banco)\b", re.I
    )),
    ("familia_cura", re.compile(
        r"\b(filho|filha|mãe|mae|pai|família|familia|doença|doenca|hospital|irmão|irmao)\b", re.I
    )),
    ("superar_padrao", re.compile(
        r"\b(padrão|padrao|sempre acontece|autoestima|bloqueio|terapia|ansiedade|depressão|depressao)\b", re.I
    )),
]


# Uma pergunta por universo: uma frase, direta, simpática. Sem travessão (—).
_PERGUNTA_DESEJO_POR_UNIVERSO: Dict[str, str] = {
    "amor_de_volta": "O que você quer ver acontecer primeiro com essa pessoa?",
    "encontrar_amor": "O que você está buscando no amor agora?",
    "salvar_relacionamento": "O que é mais importante pra você aqui: salvar o que dá, entender a dor, ou ouvir uma verdade?",
    "prosperidade": "O que mais aperta hoje: dinheiro entrando, dívida, trabalho ou outra coisa?",
    "familia_cura": "O que você mais precisa entender sobre essa situação na família?",
    "superar_padrao": "Qual padrão você quer que eu olhe nas linhas?",
    "geral": "Qual é o foco principal da leitura pra você agora?",
}

# Transição camada 1 → 2: uma linha de acolhimento (sem “?” — o normalizador corta no primeiro interrogação).
def _fechamento_camada2_presenca(universo: str) -> str:
    u = (universo or "geral").strip().lower()
    mapa = {
        "amor_de_volta": "Li o que você mandou, com carinho. Tô aqui com você.",
        "encontrar_amor": "Li o que você mandou. Vamos com calma.",
        "salvar_relacionamento": "Li o que você mandou. Conta comigo.",
        "prosperidade": "Li o que você mandou. Vamos direto ao ponto.",
        "familia_cura": "Li o que você mandou. Família pesa, eu sei.",
        "superar_padrao": "Li o que você mandou. A gente olha isso junto.",
        "geral": "Li o que você mandou, com respeito. Tô aqui.",
    }
    return mapa.get(u, mapa["geral"])


def _eh_reconhecimento_só_foto(texto: str) -> bool:
    """Lead insistindo que já enviou foto/imagem — não é desabafo nem deve consumir tentativa da camada 1."""
    limpo = (texto or "").lower().strip()
    if len(limpo.split()) > 14:
        return False
    if re.search(r"\b(foto|fotografia|imagem|palma|mão|mao|print)\b", limpo):
        return bool(
            re.search(
                r"\b(já|ja)\s+(mandei|enviei|mando)|\b(mandei|enviei|mando)\s+(a\s+)?(foto|imagem)|\b(pronto|segue|ta ai|tá aí|esta ai|está aí)\b",
                limpo,
            )
        )
    # Só "já mandei" / "mandei" (sem foto na frase) — comum no WhatsApp
    if len(limpo.split()) <= 4 and re.search(r"\b(mandei|enviei|mando)\b", limpo):
        return bool(re.match(r"^(já|ja)\s+(mandei|enviei|mando)\s*$", limpo) or limpo in ("mandei", "enviei", "mando"))
    return False


def _tem_substancia_dor(texto: str) -> bool:
    limpo = texto.lower().strip()
    if not limpo:
        return False
    palavras = limpo.split()
    if len(palavras) <= 5 and _SINAIS_ENVIO_FOTO.search(limpo):
        return False
    if limpo in _RESPOSTAS_VAZIAS or len(palavras) < 5:
        return False
    if _SINAIS_DESISTENCIA.search(limpo):
        return False
    if _RE_ASSUNTO_OPERACIONAL.search(limpo):
        return False
    if _RE_PRECO_DIRETO.search(limpo) and not _RE_VALOR_AFETIVO.search(limpo):
        return False
    if _RE_MARCADORES_DOR_OU_DESEJO.search(limpo):
        return True
    if len(palavras) >= 9:
        return True
    return True


def _tem_substancia_desejo(texto: str) -> bool:
    limpo = (texto or "").strip().lower()
    if not limpo or limpo in _RESPOSTAS_VAZIAS:
        return False
    # Lista curta e objetiva (ex.: "paz, partilhas, respeito, crescimento") já é desejo útil.
    itens = [x.strip(" .,:;|-") for x in re.split(r"\s*,\s*|\s*\|\s*", limpo) if x.strip(" .,:;|-")]
    if len(itens) >= 3 and all(len(i.split()) <= 3 for i in itens):
        return True
    palavras = limpo.split()
    if len(palavras) < 4:
        return False
    if _SINAIS_DESISTENCIA.search(limpo):
        return False
    if _SINAIS_ENVIO_FOTO.search(limpo) or _RE_ASSUNTO_OPERACIONAL.search(limpo):
        return False
    # "mulher de valor"/"homem de valor" é desejo afetivo, não objeção de preço.
    if _RE_PRECO_DIRETO.search(limpo) and not _RE_VALOR_AFETIVO.search(limpo):
        return False
    if re.search(r"\?$", limpo) and not _RE_MARCADORES_DOR_OU_DESEJO.search(limpo):
        return False
    return bool(_RE_MARCADORES_DOR_OU_DESEJO.search(limpo) or len(palavras) >= 7)


_RE_TEMPO_APROF = re.compile(
    r"\b(m[eê]s|meses|ano|anos|semana|semanas|dias|tempo|há|ha|desde|sempre|criança|crianca|"
    r"infância|infancia|vida toda|pra sempre|atrás|atras|longe|infantil|tem\s+\d+)\b",
    re.I,
)
_RE_ESFORCO_APROF = re.compile(
    r"\b(j[aá]\s+tentei|tentei|tentando|tentativa|fizemos|fiz|rez|rezei|terapia|remédio|remedio|remedios|"
    r"médico|médicos|de\s+tudo|tudo\s+nessa\s+vida|nada\s+funcionou|busquei|procurei|esforcei|hospital|"
    r"igreja|bloqueei|voltei)\b",
    re.I,
)


def _normalizar_texto_acumulado_aprof(raw: str) -> str:
    """Junta mensagens fundidas na fila (`a | b`) e normaliza espaços para regex estável."""
    s = (raw or "").strip()
    s = re.sub(r"\s*\|\s*", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _aprofundamento_resposta_suficiente(texto: str) -> bool:
    """
    Aceita respostas em duas mensagens curtas (WhatsApp): junta tempo + tentativas no texto acumulado.
    """
    limpo = _normalizar_texto_acumulado_aprof(texto)
    if not limpo or limpo in _RESPOSTAS_VAZIAS:
        return False
    palavras = limpo.split()
    if len(palavras) < 2:
        return False
    if len(palavras) >= 10:
        return True
    tem_tempo = bool(_RE_TEMPO_APROF.search(limpo))
    tem_esforco = bool(_RE_ESFORCO_APROF.search(limpo))
    if tem_tempo and tem_esforco:
        return True
    if len(palavras) >= 6 and (tem_tempo or tem_esforco):
        return True
    # Frase única com sinal forte (compatível com regra antiga)
    if len(palavras) >= 4 and bool(
        re.search(
            r"\b(mês|meses|ano|anos|semana|dias|tempo|há|ha|desde|tentei|já fiz|rez|terapia|bloqueei|voltei)\b",
            limpo,
        )
    ):
        return True
    return False


def _nudge_aprofundamento_sem_duplicar(merged: str) -> str:
    """Evita repetir a mesma pergunta longa; pede só o que falta. Termina com ? (evita gancho automático de 'ok')."""
    t = _normalizar_texto_acumulado_aprof(merged)
    tem_tempo = bool(_RE_TEMPO_APROF.search(t)) if t else False
    tem_esforco = bool(_RE_ESFORCO_APROF.search(t)) if t else False
    if tem_tempo and not tem_esforco:
        return (
            "Entendi o tempo que você trouxe. Me diz com sinceridade: o que você já tentou pra aliviar isso — "
            "terapia, conversa firme, reza, médico… ou quando você sente que já tentou de tudo? "
            "Pode ser uma linha só, tá?"
        )
    if tem_esforco and not tem_tempo:
        return (
            "Entendi o que você tentou. Pra fechar o mapa: há quanto tempo isso pesa assim — meses, anos, "
            "desde criança… como você sente no peito?"
        )
    if t:
        return (
            "Vou juntando o que você manda. Num próximo texto: há quanto tempo isso pesa? "
            "e o que você já tentou (mesmo que seja 'tentei de tudo')?"
        )
    return (
        "Pra fechar o mapa com cuidado: há quanto tempo isso pesa assim? "
        "e o que você já tentou antes de chegar aqui?"
    )


def _micro_percepcoes_desejo(desejo: str, universo: str) -> List[str]:
    """Duas leituras possíveis sobre o que o lead declarou (antes da pergunta de tempo/tentativa)."""
    d = (desejo or "").lower()[:600]
    u = (universo or "geral").lower()
    a: List[str] = []
    if re.search(r"\b(deus|proteç|proteg|oraç|oração|rezar)\b", d):
        a.append(
            "Uma leitura que aparece aqui é fé pedindo trilho… pedido de proteção com o coração apertado de quem ama."
        )
    elif re.search(r"\b(mãe|mae|pai|filho|filha|família|familia|irmão|irmao)\b", d):
        a.append(
            "Nas linhas do vínculo, isso soa como amor com medo de soltar… e cansaço de quem carrega demais."
        )
    elif re.search(r"\b(amor|voltar|namor|casar|casamento)\b", d):
        a.append(
            "No peito do desejo, aparece esse pedido de pertencimento… de ser visto de verdade."
        )
    else:
        a.append(
            "O que você trouxe agora ressoa como pedido de alívio com dignidade… sem apagar o que você já viveu."
        )
    if u == "familia_cura":
        a.append(
            "Outro ângulo possível: família puxa culpa às vezes… mas a linha também pode pedir só proteção e paz."
        )
    else:
        a.append(
            "E ainda há espaço pra esperança operante… senão você não estaria abrindo o peito assim pra mim."
        )
    return a[:2]


def _append_node3_ancora(meta: dict, trecho: str) -> None:
    atual = str(meta.get("node3_percepcoes_multas") or "").strip()
    novo = " ".join(str(trecho or "").split()).strip()
    if not novo:
        return
    if not atual:
        meta["node3_percepcoes_multas"] = novo[:1200]
        return
    low_atual = atual.lower()
    low_novo = novo.lower()
    if low_novo in low_atual:
        return
    combinado = f"{atual} | {novo}".strip()
    meta["node3_percepcoes_multas"] = combinado[:1200]


def _classificar_universo_por_regex(texto: str) -> str:
    for nome, pat in _UNIVERSO_KEYWORDS:
        if pat.search(texto or ""):
            return nome
    return "geral"


def _classificar_universo(ctx, meta: dict, desabafo: str) -> str:
    u = _classificar_universo_por_regex(desabafo)
    if u != "geral":
        return u
    if ctx.personalizer:
        try:
            out = ctx.personalizer.gerar_resposta(
                system_prompt=(
                    "Classifique em UMA palavra o universo da dor do lead. "
                    "Responda APENAS uma destas, sem pontuação: "
                    "amor_de_volta encontrar_amor salvar_relacionamento prosperidade familia_cura superar_padrao geral"
                ),
                historico_lista=slice_historico_para_ia(ctx, 5),
                mensagem_lead=desabafo[:1200],
                metadata=meta,
            )
            token = (out or "").strip().lower().split()[0] if (out or "").strip() else "geral"
            valid = {
                "amor_de_volta", "encontrar_amor", "salvar_relacionamento",
                "prosperidade", "familia_cura", "superar_padrao", "geral",
            }
            if token in valid:
                return token
        except Exception as e:
            logger.warning("⚠️ [NODE3] Falha IA universo: %s", e)
    return "geral"


def _classificar_universo_rapido(desabafo: str) -> str:
    """Classificação somente por regex (sem IA) para turnos silenciosos/objetivos."""
    return _classificar_universo_por_regex(desabafo or "")


def _delay_digitacao(texto: str) -> int:
    return max(7, min(len(str(texto)) // 15, 22)) if texto else 6


def _encurtar_balao_node3(texto: str, max_chars: int = _MAX_CHARS_BALAO_NODE3) -> str:
    t = " ".join((texto or "").split()).strip()
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    partes = re.split(r"(?<=[.!?…])\s+", t)
    out: List[str] = []
    total = 0
    for p in partes:
        p = p.strip()
        if not p:
            continue
        extra = len(p) + (1 if out else 0)
        if total + extra > max_chars:
            break
        out.append(p)
        total += extra
    if out:
        return " ".join(out).strip()
    # Se não há sentença completa dentro do limite, não trunca no meio.
    # Deixa o engine fatiar depois com segurança por balões.
    return t


def _normalizar_acoes_texto_node3(acoes: List[Acao]) -> List[Acao]:
    if not acoes:
        return acoes
    idx_txt = [i for i, a in enumerate(acoes) if getattr(a, "tipo", "") == "text"]
    if not idx_txt:
        return acoes
    textos = [str(acoes[i].conteudo or "").strip() for i in idx_txt]
    processed: List[Optional[str]] = [None] * len(idx_txt)
    vistos: set[str] = set()
    for pos, tx in enumerate(textos):
        if not tx:
            continue
        if "?" in tx or "👇" in tx:
            txc = _encurtar_balao_node3(tx, _MAX_CHARS_NODE3_PERGUNTA)
        elif pos == 0:
            txc = _encurtar_balao_node3(tx, _MAX_CHARS_NODE3_EXPLICA)
        else:
            txc = _encurtar_balao_node3(tx, _MAX_CHARS_BALAO_NODE3)
        if re.search(_REGEX_CORTE_FATAL, txc.lower()):
            continue
        k = re.sub(r"\s+", " ", txc.lower()).strip(" .!?…")
        if k in vistos:
            continue
        vistos.add(k)
        processed[pos] = txc
    for pos, idx in enumerate(idx_txt):
        acoes[idx].conteudo = processed[pos] or ""
    out = [a for a in acoes if not (a.tipo == "text" and not str(a.conteudo or "").strip())]
    # Corta após a ÚLTIMA mensagem com interrogação (presença sem ? + pergunta no mesmo turno).
    idx_last_q = -1
    for i, a in enumerate(out):
        if getattr(a, "tipo", "") == "text" and "?" in str(getattr(a, "conteudo", "") or ""):
            idx_last_q = i
    if idx_last_q >= 0:
        out = out[: idx_last_q + 1]
        while out and getattr(out[-1], "tipo", "") == "delay":
            out.pop()
    if not any(getattr(a, "tipo", "") == "text" and str(getattr(a, "conteudo", "") or "").strip() for a in out):
        out.append(
            Acao(
                tipo="text",
                conteudo="Eu sigo aqui com você, no teu ritmo. Me manda em uma mensagem o ponto principal que mais pesa agora?",
            )
        )
    return out


def _mime_por_magic_bytes(data: bytes) -> str:
    if not data or len(data) < 12:
        return "image/jpeg"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _validar_foto_mao_com_gemini(ctx) -> bool:
    media_bytes = getattr(ctx, "media_bytes", None)
    if not media_bytes:
        img_url = getattr(ctx, "imagem_url", None) or (getattr(ctx, "metadata", {}) or {}).get("imagem_url")
        if img_url:
            try:
                resp = requests.get(img_url, timeout=10)
                if resp.status_code == 200:
                    media_bytes = resp.content
            except Exception as e:
                logger.warning("⚠️ [VISION] Erro URL: %s", e)

    if not media_bytes:
        logger.warning("⚠️ [VISION] Sem bytes de imagem para validação.")
        return False

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Sem API key, considera foto válida apenas se há bytes reais no turno.
            return bool(media_bytes)

        mime = _mime_por_magic_bytes(media_bytes)
        client = genai.Client(api_key=api_key)
        # Critério mais humano: mão/palma perceptível (iluminação e foco variam no WhatsApp)
        prompt = (
            "Analise esta imagem. Há uma mão humana com a palma visível (mesmo que pouco nítida, "
            "escura ou em ângulo difícil)? Responda ESTRITAMENTE com SIM ou NAO. "
            "Responda NAO apenas se não houver mão/palma identificável ou for só objeto/outra parte do corpo."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=media_bytes, mime_type=mime),
            ],
        )
        txt = (response.text or "").upper()
        if "SIM" in txt:
            return True
        # Segunda checagem mais permissiva (evita falso NAO em fotos reais de palma)
        response2 = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "É uma foto de mão humana (palma ou dorso) em contexto doméstico? Responda só SIM ou NAO.",
                types.Part.from_bytes(data=media_bytes, mime_type=mime),
            ],
        )
        t2 = (response2.text or "").upper()
        return "SIM" in t2
    except Exception as e:
        logger.error("🚨 [VISION] Gemini: %s", e)
        # Em erro transitório da IA, não aprova sem evidência visual mínima.
        return bool(media_bytes)


_SYSTEM_COLETA_DINAMICA = """Você é Esmeralda Ácassia (Cigana Esmeralda): mesma voz dos passos anteriores — quiromancia com presença, como conversa no terreiro ou à beira da mesa, nunca como script de call center nem questionário.

ESTÁGIO: COLETA_DADOS_DIAGNOSTICO (nesta etapa só existem duas peças: foto da mão + desabafo com corpo; peça SOMENTE o que ainda faltar).

GÊNERO PARA CONCORDÂNCIA: {genero_hint}
(masculino / feminino / indefinido — se indefinido, use "você" e "tuas linhas", sem forçar.)

HIERARQUIA (obrigatória):
- Um foco por mensagem. Não empilhe dois pedidos diferentes no mesmo fôlego (ex.: não misture "o que dói no peito" com "o que você quer saber da vida" — a segunda pergunta NÃO existe nesta etapa).
- Se falta só a foto: acolha em 1 balão (presença breve) e convide a palma; não exija novo desabafo.
- Se falta só o desabafo: reconheça a foto com respeito e peça a verdade com peso humano (sem frieza nem interrogatório).
- Se falta os dois: explique com calma as duas necessidades, em no máximo 2 balões, sem soar burocrático.

MENTALISMO LEVE (sem inventar fato):
- Você pode espelhar tom, intensidade ou uma palavra que o lead já usou; não invente nome de gente, data ou situação que não apareceu no histórico/mensagem.
- Uma frase de "eu tô aqui contigo" vale mais que três adjetivos místicos vazios.

WHATSAPP:
- Frases curtas, voz de quem digita com cuidado; ritmo humano, pausas implícitas.
- Use [BALAO] entre frases completas; cada balão termina com . ! ou ?
- Sem travessão. No máximo 1 emoji no fim do último balão (💜 🔮 🙏 🖐️ ✋ 💔 🕯️ ✨ 😔).

PROIBIDO nesta etapa: "o que você quer saber sobre sua vida", "mapa da vida", segunda grande pergunta existencial, ou qualquer coisa que pule a fila antes de foto+desabafo estarem completos.
"""

_SYSTEM_GRACEFUL_EXIT = """Você é Esmeralda Ácassia (Cigana Esmeralda). O lead quer desistir ou está com muito medo.
Acolha com respeito. Se fizer sentido, lembre que pode digitar ENCERRAR para parar de verdade.
Tom: leitura, curta, sem culpa. Sem travessão.
"""

_SYSTEM_EXTRACAO_RICA = """Do texto do lead abaixo, extraia (use INDEFINIDO se não houver):
NOME_PESSOA::nome da outra pessoa ou INDEFINIDO
TEMPO_EXATO::há quanto tempo pesa ou INDEFINIDO
EVENTO_GATILHO::momento ou fatos que pioraram ou INDEFINIDO
Só estas três linhas, formato exato."""


def _graceful_exit(ctx, nome_fmt: str, msg_lead: str) -> List[Acao]:
    if ctx.personalizer:
        try:
            resp_ia = ctx.personalizer.gerar_resposta(
                system_prompt=_SYSTEM_GRACEFUL_EXIT,
                historico_lista=slice_historico_para_ia(ctx, 10),
                mensagem_lead=f"Interação: '{msg_lead}'",
                metadata=ctx.metadata,
            )
            baloes = _tratar_frases_ia(resp_ia)
            ac: List[Acao] = []
            for i, b in enumerate(baloes):
                d = _delay_digitacao(b) if i > 0 else random.randint(6, 12)
                ac.append(Acao(tipo="delay", segundos=d))
                ac.append(Acao(tipo="text", conteudo=b))
            if ac:
                return ac
        except Exception as e:
            logger.error("Erro Graceful Exit: %s", e)
    return [
        Acao(tipo="delay", segundos=8),
        Acao(
            tipo="text",
            conteudo=f"Sinto seu receio daqui, {nome_fmt}… o medo às vezes aperta mesmo. 😔",
        ),
        Acao(tipo="delay", segundos=12),
        Acao(
            tipo="text",
            conteudo="Estou aqui se quiser continuar. Se preferir encerrar, digite ENCERRAR.",
        ),
    ]


def _tratar_frases_ia(texto: str) -> List[str]:
    partes = re.split(r"\[?BAL[AÃ]O\]?", texto, flags=re.IGNORECASE)
    frases_ok: List[str] = []
    for frase in partes:
        c = re.sub(r"\[.*?\]", "", frase).strip()
        c = re.sub(r"[-–—*•]+", "", c).strip()
        if len(c) < 5:
            continue
        if re.search(_REGEX_CORTE_FATAL, c.lower()):
            continue
        if not re.match(_PONTUACAO_VALIDA, c):
            continue
        frases_ok.append(c)
    return frases_ok


def _parse_extracao_rica(texto: str) -> Dict[str, str]:
    out = {"nome_pessoa_envolvida": "", "tempo_exato": "", "evento_gatilho": ""}
    if not texto:
        return out
    for linha in texto.split("\n"):
        if "::" not in linha:
            continue
        k, _, v = linha.partition("::")
        key = k.strip().upper()
        val = v.strip().strip('"').strip("'")
        if key == "NOME_PESSOA":
            out["nome_pessoa_envolvida"] = val
        elif key == "TEMPO_EXATO":
            out["tempo_exato"] = val
        elif key == "EVENTO_GATILHO":
            out["evento_gatilho"] = val
    return out


def _extrair_dados_ricos_ia(ctx, meta: dict) -> None:
    if not ctx.personalizer:
        return
    blob = " | ".join(
        filter(
            None,
            [
                meta.get("desabafo_original", ""),
                meta.get("desejo_declarado", ""),
                meta.get("aprofundamento_texto", ""),
            ],
        )
    )[:2500]
    try:
        raw = ctx.personalizer.gerar_resposta(
            system_prompt=_SYSTEM_EXTRACAO_RICA,
            historico_lista=slice_historico_para_ia(ctx, 16),
            mensagem_lead=blob,
            metadata=meta,
        )
        parsed = _parse_extracao_rica(raw or "")
        for k, v in parsed.items():
            if v and v.upper() != "INDEFINIDO":
                meta[k] = v
        meta["node3_extracao_feita"] = True
        logger.info("event=node3_extracao_ok lead_fields=%s", list(parsed.keys()))
    except Exception as e:
        logger.error("🚨 [NODE3] Extração rica: %s", e)


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    meta = getattr(ctx, "metadata", {}) or {}

    nome_db = (ctx.nome_lead or meta.get("nome_lead") or "").strip() or VOCATIVO_SEM_NOME
    lixo_names = {"estou", "sim", "ok", "quero", "vou", "salvei", "pronto", "ola", "oi", "ta", "tá", "ja", "já", "blz"}
    if nome_db.lower() in lixo_names or nome_eh_placeholder(nome_db):
        nome_db = VOCATIVO_SEM_NOME

    nome_fmt = nome_lead_para_exibicao(nome_db)
    msg_lead = str(ctx.texto_recebido or "").strip()
    msg_lower = msg_lead.lower()
    genero = genero_efetivo_para_copy(
        ctx.nome_lead or nome_db or "", meta, texto_discurso=msg_lead or None
    )
    meta["genero_lead"] = genero
    genero_hint = genero_hint_para_prompt(meta)

    estado = meta.get("node3_estado", "inicial")
    tipo_msg = getattr(ctx, "tipo_mensagem", "text")

    proximo_node = "3_coleta_profunda"

    # Leads antigos (DB) ou resquício: o pré-flight costuma pular para o 4 antes; se o 3 ainda rodar,
    # não devolve lista vazia (evita turno “mudo” se o encadeamento falhar).
    if estado == "coleta_completa":
        ctx.metadata = meta
        acoes_handoff = [
            Acao(tipo="delay", segundos=2),
            Acao(
                tipo="text",
                conteudo="Vou te levar pro próximo passo da leitura, no teu ritmo. ✨",
                metadata={"skip_gancho_final": True},
            ),
        ]
        return _normalizar_acoes_texto_node3(acoes_handoff), "4_instagram"

    # ── inicial (God-Mode + Sniffer: ramifica copy; funil 2–4 preservado) ──
    # Nota: não saltar para 4_instagram com coleta_completa aqui — faltariam desejo,
    # aprofundamento e extração rica (Node 4/5 dependem desse contexto enriquecido).
    if estado == "inicial":
        meta["node3_iniciado_em"] = datetime.now(timezone.utc).isoformat()
        meta["node3_contrato_enviado"] = True
        meta["node3_tentativas_c1"] = 0
        meta["node3_tentativas_c2"] = 0
        meta["node3_tentativas_c3"] = 0

        meta["node3_estado"] = "aguardando_dados"
        tem_foto = bool(meta.get("foto_recebida"))
        tem_dor = bool(meta.get("desabafo_recebido"))

        acoes_iniciais: List[Acao] = []
        if meta.get("node1_pulou_para_coleta") and not meta.get("node2_vcard_despachado"):
            cfg = meta.get("__config__") or {}
            num_wa = cfg.get("numero_whatsapp") or "+55 92 8497-9419"
            acoes_iniciais.extend(
                [
                    Acao(tipo="delay", segundos=6),
                    Acao(
                        tipo="text",
                        conteudo="Antes de mergulhar nas linhas: segue meu cartão aqui embaixo pra você ter meu número certinho na agenda.",
                    ),
                    Acao(tipo="delay", segundos=random.randint(5, 8)),
                    Acao(tipo="vcard", conteudo=num_wa),
                ]
            )
            meta["node2_vcard_despachado"] = True

        if meta.get("node2_contato_ja_reconhecido"):
            primeiro_balao = f"{nome_fmt}, que bom te ver aqui comigo. ✨"
        elif meta.get("node2_vcard_despachado"):
            # Se o Node2 já verbalizou o contexto do cartão no turno imediatamente anterior,
            # não repetir a mesma âncora para evitar sensação de eco.
            if meta.get("node2_contexto_card_enviado"):
                primeiro_balao = f"{nome_fmt}, seguimos com calma daqui. ✨"
            else:
                # Node2 novo padrão pode enviar card sem confirmação explícita.
                # Aqui não afirmamos "você salvou" para não gerar incoerência.
                primeiro_balao = f"{nome_fmt}, deixei meu cartão aqui no chat. Seguimos com calma. ✨"
        else:
            primeiro_balao = f"Que bom que você salvou meu contato, {nome_fmt}. ✨"
        acoes_iniciais.extend(
            [
                Acao(tipo="delay", segundos=8),
                Acao(tipo="text", conteudo=primeiro_balao),
            ]
        )

        # Foto + desabafo (Sniffer): fast-track à camada 2 — mesma máquina de estados, sem repetir pedidos
        if tem_foto and tem_dor:
            desabafo = (meta.get("desabafo_original") or msg_lead or "").strip()
            if desabafo:
                meta["desabafo_original"] = desabafo[:2000]
            meta["universo_desejo"] = _classificar_universo(ctx, meta, meta.get("desabafo_original", ""))
            desejo_precoce = (meta.get("desejo_declarado") or "").strip()
            aprofundamento_precoce = (meta.get("aprofundamento_texto") or "").strip()
            logger.info(
                "⚡ [NODE 3] Fast-track (foto+dor via Sniffer). Lead=%s universo=%s desejo_precoce=%s aprofundamento_precoce=%s",
                nome_fmt,
                meta.get("universo_desejo"),
                bool(desejo_precoce),
                bool(aprofundamento_precoce),
            )

            if desejo_precoce and _tem_substancia_desejo(desejo_precoce):
                if aprofundamento_precoce and _aprofundamento_resposta_suficiente(aprofundamento_precoce):
                    _append_node3_ancora(meta, desejo_precoce[:240])
                    _append_node3_ancora(meta, aprofundamento_precoce[:260])
                    _extrair_dados_ricos_ia(ctx, meta)
                    meta["node3_estado"] = "coleta_completa"
                    ctx.estado_coleta = "node3_camada4_extracao_ok"
                    acoes_iniciais.extend(
                        [
                            Acao(tipo="delay", segundos=random.randint(9, 14)),
                            Acao(tipo="text", conteudo="Perfeito. Você já me trouxe os pontos principais e eu guardei tudo com atenção."),
                            Acao(tipo="delay", segundos=random.randint(8, 12)),
                            Acao(tipo="text", conteudo="Agora vou te mostrar meu Instagram rapidinho e seguimos."),
                        ]
                    )
                    ctx.metadata = meta
                    return _normalizar_acoes_texto_node3(acoes_iniciais), "4_instagram"

                meta["node3_estado"] = "aguardando_aprofundamento"
                meta["node3_aprofundamento_acumulado"] = ""
                ctx.estado_coleta = "node3_camada3_tempo_tentativas"
                _append_node3_ancora(meta, desejo_precoce[:240])
                acoes_iniciais.extend(
                    [
                        Acao(tipo="delay", segundos=random.randint(8, 12)),
                        Acao(tipo="text", conteudo="Você foi bem claro no que deseja, isso ajuda muito."),
                        Acao(tipo="delay", segundos=random.randint(8, 14)),
                        Acao(
                            tipo="text",
                            conteudo="Pra fechar o mapa com cuidado: há quanto tempo isso pesa assim? E o que você já tentou antes de chegar aqui?",
                        ),
                    ]
                )
                ctx.metadata = meta
                return _normalizar_acoes_texto_node3(acoes_iniciais), proximo_node

            meta["node3_estado"] = "aguardando_desejo"
            ctx.estado_coleta = "node3_camada2_desejo"
            _u_ft = meta.get("universo_desejo", "geral")
            _p_ft = _fechamento_camada2_presenca(_u_ft)
            _q_ft = _PERGUNTA_DESEJO_POR_UNIVERSO.get(_u_ft, _PERGUNTA_DESEJO_POR_UNIVERSO["geral"])
            _append_node3_ancora(meta, f"{_p_ft} {_q_ft}"[:1200].strip())
            # Duas bolhas: acolhimento + uma pergunta (evita repetir pedido no meio).
            ft_blocos: List[Acao] = [
                Acao(tipo="delay", segundos=random.randint(10, 16)),
                Acao(tipo="text", conteudo=_p_ft),
                Acao(tipo="delay", segundos=random.randint(8, 14)),
                Acao(tipo="text", conteudo=_q_ft),
            ]
            acoes_iniciais.extend(ft_blocos)
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(acoes_iniciais), proximo_node

        ctx.estado_coleta = "node3_camada1_foto_desabafo"

        if tem_foto and not tem_dor:
            acoes_iniciais.extend(
                [
                    Acao(tipo="delay", segundos=10),
                    Acao(
                        tipo="text",
                        conteudo="Já guardei a foto da sua mão comigo. Pra eu cruzar com o que as linhas querem dizer…",
                    ),
                    Acao(tipo="delay", segundos=8),
                    Acao(
                        tipo="text",
                        conteudo="Agora me conta com a boca do peito: o que mais aperta aí hoje? 👇",
                    ),
                ]
            )
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(acoes_iniciais), proximo_node

        if not tem_foto and tem_dor:
            acoes_iniciais.extend(
                [
                    Acao(tipo="delay", segundos=10),
                    Acao(
                        tipo="text",
                        conteudo=f"Me manda uma foto da sua mão aqui pra eu seguir com a leitura, {nome_fmt}? 🖐️",
                    ),
                ]
            )
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(acoes_iniciais), proximo_node

        acoes_iniciais.extend(
            [
                Acao(tipo="delay", segundos=12),
                Acao(
                    tipo="text",
                    conteudo="Pra eu ler as linhas com fundamento, preciso de duas coisas no teu ritmo, sem pressa…",
                ),
                Acao(tipo="delay", segundos=10),
                Acao(
                    tipo="text",
                    conteudo="A foto da mão aqui no chat. Depois, numa mensagem, o que tá pesando de verdade — pode ser feio, pode ser misturado. 👇",
                ),
            ]
        )
        ctx.metadata = meta
        return _normalizar_acoes_texto_node3(acoes_iniciais), proximo_node

    # ── camada 1 ──
    if estado == "aguardando_dados":
        ctx.estado_coleta = "node3_camada1_foto_desabafo"

        # Reforço: 2+ mídias no fio (ex.: mão no node 1 + nova tentativa no 3) — mantém `foto_recebida`
        # se um envio falhar na validação Gemini. Não usar com 1 só (evita marcar foto após única imagem ruim + texto depois).
        if _historico_conta_midia_usuario(ctx) >= 2:
            meta["foto_recebida"] = True

        if "encerrar" in msg_lower:
            meta["opt_out"] = True
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3([Acao(tipo="text", conteudo="O nosso portal está fechado. Fique em paz. ✨")]), "99_opt_out"

        if _SINAIS_DESISTENCIA.search(msg_lower):
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(_graceful_exit(ctx, nome_fmt, msg_lead)), proximo_node

        if tipo_msg in ("image", "video"):
            img_u = str((meta.get("imagem_url") or getattr(ctx, "imagem_url", None) or "")).strip()
            if img_u and meta.get("node3_foto_validacao_ok_url") == img_u:
                meta["foto_recebida"] = True
            elif not _validar_foto_mao_com_gemini(ctx):
                # Só zera `foto_recebida` quando esta é a única mídia no fio (primeira tentativa falhou).
                # Se já houve foto antes (ex.: node 1), não apagar a prova do sniffer — pede outra imagem sem “esquecer” a primeira.
                if _historico_conta_midia_usuario(ctx) <= 1:
                    meta["foto_recebida"] = False
                voc = vocativo_cigana(nome_db, genero, meta)
                ctx.metadata = meta
                return [
                    Acao(tipo="delay", segundos=6),
                    Acao(tipo="text", conteudo=f"{voc}, ainda não consegui identificar uma mão nessa imagem. 😔"),
                    Acao(tipo="delay", segundos=8),
                    Acao(tipo="text", conteudo="Me envia outra foto mostrando a mão, que eu sigo com a leitura na hora. ✋"),
                ], proximo_node
            else:
                meta["foto_recebida"] = True
                if img_u:
                    meta["node3_foto_validacao_ok_url"] = img_u

        if _tem_substancia_dor(msg_lead):
            meta["desabafo_recebido"] = True
            acum = meta.get("desabafo_original", "")
            meta["desabafo_original"] = f"{acum} {msg_lead[:1500]}".strip()

        if _historico_tem_midia_usuario(ctx):
            meta["foto_recebida"] = True

        tem_foto = bool(meta.get("foto_recebida"))
        tem_dor = bool(meta.get("desabafo_recebido"))
        if not (tem_foto and tem_dor):
            pular_tentativa = bool(
                tem_dor
                and not tem_foto
                and msg_lead
                and _eh_reconhecimento_só_foto(msg_lead)
            )
            if not pular_tentativa:
                meta["node3_tentativas_c1"] = int(meta.get("node3_tentativas_c1", 0) or 0) + 1
            t1 = int(meta.get("node3_tentativas_c1", 0) or 0)
            if t1 >= _MAX_TENTATIVAS_CAMADA:
                logger.info(
                    "event=node3_camada1_bypass tentativas=%s (avanço automático; desbloqueio de funil)",
                    t1,
                )
                meta_node3_forcar_camada1_completa(
                    meta,
                    msg_fallback=msg_lead,
                    falta_foto=not tem_foto,
                    falta_desabafo=not tem_dor,
                )

        if meta.get("foto_recebida") and meta.get("desabafo_recebido"):
            desabafo = meta.get("desabafo_original", "")
            # Fast-path: em turno de mídia/silencioso, evita chamada IA cara só para classificar universo.
            if not (msg_lead or "").strip() and bool(meta.get("universo_desejo")):
                universo = str(meta.get("universo_desejo") or "geral")
            elif not (msg_lead or "").strip():
                universo = _classificar_universo_rapido(desabafo)
            else:
                universo = _classificar_universo(ctx, meta, desabafo)
            meta["universo_desejo"] = universo
            meta["node3_estado"] = "aguardando_desejo"
            ctx.estado_coleta = "node3_camada2_desejo"
            _u_c2 = meta.get("universo_desejo", "geral")
            _p_c2 = _fechamento_camada2_presenca(_u_c2)
            _q_c2 = _PERGUNTA_DESEJO_POR_UNIVERSO.get(_u_c2, _PERGUNTA_DESEJO_POR_UNIVERSO["geral"])
            _append_node3_ancora(meta, f"{_p_c2} {_q_c2}"[:1200].strip())
            acoes_c2: List[Acao] = [
                Acao(tipo="delay", segundos=random.randint(6, 10)),
                Acao(tipo="text", conteudo=_p_c2),
                Acao(tipo="delay", segundos=random.randint(6, 10)),
                Acao(tipo="text", conteudo=_q_c2),
            ]
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(acoes_c2), proximo_node

        acoes: List[Acao] = []
        if ctx.personalizer:
            try:
                resp_ia = ctx.personalizer.gerar_resposta(
                    system_prompt=_SYSTEM_COLETA_DINAMICA.format(genero_hint=genero_hint),
                    historico_lista=slice_historico_para_ia(ctx, 10),
                    mensagem_lead=(
                        f"SITUAÇÃO (lead {nome_fmt}): foto da mão = {bool(meta.get('foto_recebida'))}; "
                        f"desabafo com substância = {bool(meta.get('desabafo_recebido'))}. "
                        "Gere só o próximo passo desta etapa: presença breve + um único pedido do que falta. "
                        "Não antecipe camada 2: sem pergunta sobre 'vida toda', 'mapa geral' ou direção da leitura."
                    ),
                    metadata=meta,
                )
                baloes_limpos = _tratar_frases_ia(resp_ia)
                if baloes_limpos:
                    tot = " ".join(baloes_limpos)
                    if "?" not in tot and "👇" not in tot:
                        if not meta.get("foto_recebida") and not _historico_tem_midia_usuario(ctx):
                            baloes_limpos.append("Consegue mandar a foto da palma direita agora? ✋")
                        elif not meta.get("desabafo_recebido"):
                            baloes_limpos.append(
                                "Me conta com a boca do peito: o que tá mais pesado aí agora, sem filtro?"
                            )
                    acoes.append(Acao(tipo="delay", segundos=max(6, min(len(msg_lead) // 22, 12))))
                    for i, b in enumerate(baloes_limpos):
                        acoes.append(Acao(tipo="delay", segundos=_delay_digitacao(b) if i > 0 else random.randint(6, 12)))
                        acoes.append(Acao(tipo="text", conteudo=b))
                    ctx.metadata = meta
                    return _normalizar_acoes_texto_node3(acoes), proximo_node
            except Exception as e:
                logger.error("🚨 [NODE3] IA camada1: %s", e)

        ctx.metadata = meta
        return [
            Acao(
                tipo="text",
                conteudo=(
                    "Quando puder, manda a palma aqui no chat e, na sequência, solta o que tá pesando de verdade. "
                    "Eu fico aqui, no teu ritmo. ✋"
                ),
            )
        ], proximo_node

    # ── camada 2: desejo ──
    if estado == "aguardando_desejo":
        ctx.estado_coleta = "node3_camada2_desejo"
        if _tem_substancia_desejo(msg_lead):
            meta["desejo_declarado"] = msg_lead[:2000]
        else:
            meta["node3_tentativas_c2"] = int(meta.get("node3_tentativas_c2", 0) or 0) + 1
            if meta["node3_tentativas_c2"] >= _MAX_TENTATIVAS_CAMADA:
                meta["desejo_declarado"] = meta.get("desejo_declarado") or msg_lead or "desejo ainda em silêncio"

        if meta.get("desejo_declarado"):
            meta["node3_estado"] = "aguardando_aprofundamento"
            meta["node3_aprofundamento_acumulado"] = ""
            ctx.estado_coleta = "node3_camada3_tempo_tentativas"
            percs_d = _micro_percepcoes_desejo(
                meta.get("desejo_declarado", ""),
                meta.get("universo_desejo", "geral"),
            )
            acoes_c3: List[Acao] = [Acao(tipo="delay", segundos=delay_dramatico())]
            for ptxt in percs_d:
                _append_node3_ancora(meta, ptxt)
                acoes_c3.extend(
                    [
                        Acao(tipo="delay", segundos=random.randint(8, 15)),
                        Acao(tipo="text", conteudo=ptxt),
                    ]
                )
            acoes_c3.extend(
                [
                    Acao(tipo="delay", segundos=random.randint(8, 14)),
                    Acao(tipo="text", conteudo="O que você me disse agora eu guardei com respeito. 🙏"),
                    Acao(tipo="delay", segundos=random.randint(10, 18)),
                    Acao(
                        tipo="text",
                        conteudo="Pra fechar o mapa com cuidado: há quanto tempo isso pesa assim? E o que você já tentou antes de chegar aqui?",
                    ),
                ]
            )
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(acoes_c3), proximo_node

        ctx.metadata = meta
        u = meta.get("universo_desejo", "geral")
        # Duas bolhas: acolhimento alinhado ao universo + uma pergunta (sem terceira bolha que repete o pedido).
        return [
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(tipo="text", conteudo=_fechamento_camada2_presenca(u)),
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(tipo="text", conteudo=_PERGUNTA_DESEJO_POR_UNIVERSO.get(u, _PERGUNTA_DESEJO_POR_UNIVERSO["geral"])),
        ], proximo_node

    # ── camada 3 + 4 ──
    if estado == "aguardando_aprofundamento":
        ctx.estado_coleta = "node3_camada3_tempo_tentativas"
        prev_ap = (meta.get("node3_aprofundamento_acumulado") or "").strip()
        cur_ap = (msg_lead or "").strip()
        if cur_ap:
            merged_ap = f"{prev_ap} {cur_ap}".strip() if prev_ap else cur_ap
        else:
            merged_ap = prev_ap
        merged_ap = re.sub(r"\s*\|\s*", " ", merged_ap).strip()
        meta["node3_aprofundamento_acumulado"] = merged_ap[:2500]

        if _aprofundamento_resposta_suficiente(merged_ap):
            meta["aprofundamento_texto"] = merged_ap[:2000]
        else:
            meta["node3_tentativas_c3"] = int(meta.get("node3_tentativas_c3", 0) or 0) + 1
            if meta["node3_tentativas_c3"] >= _MAX_TENTATIVAS_CAMADA:
                meta["aprofundamento_texto"] = (merged_ap.strip() or cur_ap or "detalhe breve")[:2000]

        if meta.get("aprofundamento_texto"):
            meta.pop("node3_aprofundamento_acumulado", None)
            _append_node3_ancora(meta, str(meta.get("aprofundamento_texto") or "")[:260])
            _extrair_dados_ricos_ia(ctx, meta)
            meta["node3_estado"] = "coleta_completa"
            ctx.estado_coleta = "node3_camada4_extracao_ok"
            fechar = [
                Acao(tipo="delay", segundos=delay_dramatico()),
                Acao(
                    tipo="text",
                    conteudo=(
                        f"{nome_fmt}, o que você trouxe fecha com o que as linhas já sussurravam. "
                        "Antes de eu abrir o Instagram pra você ver o terreno onde trabalho: "
                        "qual é a pergunta principal que você quer que eu olhe nas linhas agora?"
                    ),
                ),
            ]
            ctx.metadata = meta
            return _normalizar_acoes_texto_node3(fechar), "4_instagram"

        ctx.metadata = meta
        return [
            Acao(tipo="delay", segundos=random.randint(8, 14)),
            Acao(
                tipo="text",
                conteudo=_nudge_aprofundamento_sem_duplicar(merged_ap),
                metadata={"skip_gancho_final": True},
            ),
        ], proximo_node

    ctx.metadata = meta
    ctx.estado_coleta = "node3_fallback_instagram"
    return _normalizar_acoes_texto_node3([]), "4_instagram"
