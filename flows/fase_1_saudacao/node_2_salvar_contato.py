"""
flows/fase_1_saudacao/node_2_salvar_contato.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
O PACTO DE RESSONÂNCIA — MASTER SUPREMA v15 (alinhado ao Node 1)

PAPEL DESTE NODE NO FUNIL:
  Receber a confirmação do lead, garantir a higiene da identidade e o VCard.
  Transforma um passo técnico num ritual de "Permissão Energética".

🔥 v15 (alinhado ao Node 1):
  - Mesma voz: Esmeralda Ácassia, tom templo/leitura (sem telemarketing).
  - Gênero injetado no prompt da IA; rota rápida em PT-BR (celular, consulta inicial).
"""

import logging
import random
import re
import time
from typing import List, Tuple
from schema import Acao, slice_historico_para_ia
from copy_sanitizer import (
    genero_efetivo_para_copy,
    genero_hint_para_prompt,
    limpar_colagem_primeira_msg_whatsapp_em_texto,
)
from conversation_policy import lead_reportou_problema_entrega
from flows.funnel_gates import (
    VOCATIVO_SEM_NOME,
    nome_eh_placeholder,
    meta_tem_foto,
    meta_tem_desabafo,
    nome_util_para_checklist_fase1,
)

logger = logging.getLogger(__name__)

# Gatilhos de "Bagagem" (Dores ou Objeções repetidas)
_GATILHOS_DINAMICOS = [
    "valor", "preço", "preco", "custa", "ajuda", "desesperad", "medo",
    "marido", "ex", "mulher", "traição", "urgente", "golpe", "dor",
]

# ── PROMPT (mesma linha editorial do Node 1: leitura, templo, calma) ──
_SYSTEM_VCARD_DINAMICO = """Você é Esmeralda Ácassia (Meu Mistério Esmeralda), a mesma voz calorosa do primeiro passo da conversa.
ESTÁGIO: PACTO_DE_RESSONÂNCIA (salvar contato antes de seguir a leitura)

IMPORTANTE: Não escreva tags técnicas, [ESTÁGIO], nem texto entre colchetes na resposta.
⚠️ BALÕES: cada [BALAO] só depois de frase completa com . ! ou ?
⚠️ No ÚLTIMO balão desta resposta, NÃO faça pergunta (o cartão de contato vem na mensagem seguinte, automático).

GÊNERO PARA CONCORDÂNCIA: {genero_hint}
- masculino: dele, alinhado a quem se apresenta como homem.
- feminino: dela.
- indefinido: use "você" e "suas linhas", sem forçar.

CONTEXTO: O lead ({nome}) escreveu algo agora — acolha de verdade (medo, pressa, dúvida); não fale para um "lead" genérico.

SUA MISSÃO:
1. Uma frase de validação com o nome quando couber.
2. Explicar com naturalidade: salvar seu número na agenda permite que você envie os áudios e continue a consulta inicial olhando as linhas com calma.
3. Dizer que o contato aparece logo abaixo neste chat (sem pergunta no fim).

{bloco_salvo}

REGRAS:
- PROIBIDO travessão (—). Use vírgulas ou reticências.
- Tom: presença de verdade, como no templo — nada de tom de call center ou promo gritada.
- Divida em 2 ou 3 balões com [BALAO].
- TAMANHO: balão de explicação até 160 chars, confirmação até 120 chars e pergunta final até 110 chars.
- Não repita bloco longo do "instituto de luz Meu Mistério"; pode dizer "daqui" ou "por aqui" se precisar de ancoragem.
{bloco_preco}
"""

# 🚨 FIX APLICADO: Regex sincronizado com o Node 1
_REGEX_CORTE_FATAL = r"([,;:\-]|\b(?:a|ao|as|e|é|eh|éh|foi|o|os|se|à|em|mas|ou|um|uma|que|de|do|da|com|por|para|sem|são|tão|tbm|também|esse|essa|isso|isto|nele|nela|nisso|nisto))\s*$"

_MAX_CHARS_BALAO_NODE2 = 210
_MAX_CHARS_NODE2_EXPLICA = 160
_MAX_CHARS_NODE2_CONFIRMA = 120
_MAX_CHARS_NODE2_PERGUNTA = 110
_RE_PROBLEMA_ENTREGA = re.compile(
    r"\b(cortad[ao]|incomplet[ao]|atropel|card|cart[aã]o\s+de\s+contato|"
    r"n[aã]o\s+deu\s+tempo|n[aã]o\s+deu\s+pra\s+ver)\b",
    re.I,
)
_RE_OBJECAO_CARD = re.compile(
    r"(?i)(n[aã]o\s+achei|n[aã]o\s+encontrei|cad[eê]\s+seu\s+contato|"
    r"n[aã]o\s+veio\s+o\s+card|n[aã]o\s+apareceu\s+o\s+contato|"
    r"sumiu\s+o\s+contato|n[aã]o\s+salvou)"
)
_RE_CONFIRMACAO_CURTA = re.compile(
    r"(?i)\b(ok|pronto|feito|sim|show|blz|beleza|confirm|salvei|salvo)\b"
)


def _nome_valido_guardado(n: str) -> bool:
    s = (n or "").strip()
    return bool(s) and not nome_eh_placeholder(s)


def _nome_ja_conhecido(meta: dict, ctx) -> str:
    """Prioriza metadata, depois ctx.nome_lead (coluna lead.nome no engine). Nunca usa a mensagem atual aqui."""
    for cand in ((meta.get("nome_lead") or "").strip(), (getattr(ctx, "nome_lead", None) or "").strip()):
        if _nome_valido_guardado(cand):
            return cand
    return ""


def _limpar_nome(texto: str) -> str:
    """Extrai nome apenas com apresentação explícita; caso contrário, mantém vocativo neutro."""
    if not texto:
        return VOCATIVO_SEM_NOME

    texto_limpo = re.sub(r"[^\w\s]", "", texto)
    entrada_original = texto.strip()

    palavras_lixo = {
        "oi", "olá", "ola", "bom", "dia", "boa", "tarde", "noite", "tudo", "bem",
        "esmeralda", "meumisterio", "amém", "me", "chamo", "nome", "é", "e", "sou",
        "estou", "sim", "quero", "vou", "salvar", "salvei", "pronto", "ok", "ta", "tá",
        "ja", "já", "ah", "aham", "uhum", "nem", "tipo",
        "mandei", "enviei", "mando", "manda", "segue", "foto", "fotos", "imagem", "video", "vídeo",
        "disse", "falei", "falou", "diz", "dizer", "também", "tbm", "pode",
        "aqui", "então", "entao", "porque", "por", "que", "uma", "uns", "pelo", "pela",
        "preciso", "precisa", "quero", "gostaria", "obrigado", "obrigada", "valeu",
    }

    padroes = [
        r"(?:me chamo|meu nome é|meu nome e|sou o|sou a|aqui é|aqui e)\s+([A-ZÀ-Ú][a-zà-ú]+)",
        r"(?:eu sou|prazer)\s+([A-ZÀ-Ú][a-zà-ú]+)",
    ]

    for p in padroes:
        match = re.search(p, entrada_original, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()

    # "Me Teixerão" / "Me João" (WhatsApp: apresentação coloquial sem "chamo")
    tokens_me = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", entrada_original)
    if len(tokens_me) == 2 and tokens_me[0].lower() == "me":
        cand_me = tokens_me[1].strip()
        cl = cand_me.lower()
        if (
            2 <= len(cand_me) <= 24
            and cl not in palavras_lixo
            and not nome_eh_placeholder(cl)
        ):
            return cand_me.capitalize()

    # Aceita nome "solto" (resposta direta do tipo "Juliana"), com guardrails.
    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", entrada_original)
    if 1 <= len(tokens) <= 2:
        cand = tokens[0].strip()
        cand_l = cand.lower()
        if (
            2 <= len(cand) <= 24
            and cand_l not in palavras_lixo
            and not nome_eh_placeholder(cand_l)
        ):
            return cand.capitalize()

    # Sem padrão explícito de apresentação, não tenta adivinhar nome.
    return VOCATIVO_SEM_NOME

def _delay_digitacao(texto: str) -> int:
    """Simula o tempo de digitação humana."""
    if not texto: return 8
    return max(9, min(len(str(texto)) // 16, 26))


def _encurtar_balao_node2(texto: str, max_chars: int = _MAX_CHARS_BALAO_NODE2) -> str:
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
    # Se não houver frase completa no limite, não corta no meio.
    # O engine faz fatiamento seguro posteriormente.
    return t


def _sanear_textos_node2(textos: List[str]) -> List[str]:
    out: List[str] = []
    vistos: set[str] = set()
    for tx in textos or []:
        t = limpar_colagem_primeira_msg_whatsapp_em_texto(str(tx or "")).strip()
        t = _encurtar_balao_node2(t, _MAX_CHARS_BALAO_NODE2)
        if len(t) < 3:
            continue
        chave = re.sub(r"\s+", " ", t.lower()).strip(" .!?…")
        if chave in vistos:
            continue
        vistos.add(chave)
        out.append(t)
    return out[:4]


def _aplicar_cap_hierarquico_node2(textos: List[str]) -> List[str]:
    out: List[str] = []
    for i, tx in enumerate(textos or []):
        t = str(tx or "").strip()
        if not t:
            continue
        if "?" in t or "👇" in t:
            t = _encurtar_balao_node2(t, _MAX_CHARS_NODE2_PERGUNTA)
        elif i == 0:
            t = _encurtar_balao_node2(t, _MAX_CHARS_NODE2_EXPLICA)
        else:
            t = _encurtar_balao_node2(t, _MAX_CHARS_NODE2_CONFIRMA)
        out.append(t)
    return out[:4]


def _normalizar_acoes_texto_node2(acoes: List[Acao]) -> List[Acao]:
    idx_txt = [i for i, a in enumerate(acoes or []) if getattr(a, "tipo", "") == "text"]
    if not idx_txt:
        return acoes
    textos = [acoes[i].conteudo for i in idx_txt]
    textos = _sanear_textos_node2(textos)
    textos = _aplicar_cap_hierarquico_node2(textos)
    # Regra de 1 pergunta por turno: apenas último texto pode manter '?'
    for i in range(len(textos) - 1):
        textos[i] = re.sub(r"\?+", ".", textos[i]).strip()
    for pos, idx in enumerate(idx_txt):
        if pos < len(textos):
            acoes[idx].conteudo = textos[pos]
        else:
            acoes[idx].conteudo = ""
    out = [a for a in acoes if not (a.tipo == "text" and not str(a.conteudo or "").strip())]
    # Se houver pergunta, ela deve encerrar o turno (aguardar resposta do lead).
    idx_q = -1
    for i, a in enumerate(out):
        if getattr(a, "tipo", "") == "text" and "?" in str(getattr(a, "conteudo", "") or ""):
            idx_q = i
            break
    if idx_q >= 0:
        out = out[: idx_q + 1]
        while out and getattr(out[-1], "tipo", "") == "delay":
            out.pop()
    # Guarda de segurança: evita turno vazio quando filtros removem tudo.
    if not any(getattr(a, "tipo", "") == "text" and str(getattr(a, "conteudo", "") or "").strip() for a in out):
        out.append(
            Acao(
                tipo="text",
                conteudo="Vou te guiar com calma por aqui. Assim que salvar meu contato, eu sigo contigo no próximo passo.",
            )
        )
    return out


_RE_CONTATO_SALVO_USER = re.compile(
    r"(?i)\b(já|ja)\s+(salvei|salbei|guardei|adicionei|botei)\b|"
    r"\b(salvei|salbei|guardei)\s+(o\s+)?(seu\s+)?(contato|número|numero|telefone)\b|"
    r"\b(contato|número|numero)\s+(salvo|guardado|já\s+está|ja\s+esta)\b|"
    r"\b(salvei|salbei)\s+ddu\b|"
    r"\bpronto[,]?\s*(já|ja)\s+salvei\b|"
    r"\bjá\s+deixei\s+seu\s+número\b|"
    r"\b(salvei|salbei)\s+(teu|seu|o)\s+contato\b"
)


def texto_indica_contato_salvo(texto: str) -> bool:
    """Lead disse que já salvou o número (evita repetir ritual do node 2)."""
    if not (texto or "").strip():
        return False
    return bool(_RE_CONTATO_SALVO_USER.search(texto))


def blob_sessao_usuario(ctx, msg_atual: str) -> str:
    """Mensagem atual + falas recentes do user (ex.: 'pode sim' após 'já salvei')."""
    partes: List[str] = []
    seen: set[str] = set()
    cur = (msg_atual or "").strip()
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


def _lead_pergunta_preco(ctx, msg_lead: str) -> bool:
    if str(getattr(ctx, "intencao", "") or "").strip().lower() == "preco":
        return True
    low = (msg_lead or "").lower()
    return any(
        x in low
        for x in (
            "preço",
            "preco",
            "valor",
            "custa",
            "quanto",
            "pix",
            "pagar",
            "gratis",
            "grátis",
            "cobr",
        )
    )


def _bloco_sistema_salvo(meta: dict) -> str:
    if meta.get("lead_contato_salvo_declarado"):
        return (
            "\n⚠️ O lead JÁ DISSE que salvou seu contato na agenda — NÃO peça para salvar, "
            "NÃO repita o ritual de 'salva meu número'. Acolha o que ele trouxe; fale só de continuidade "
            "(áudios, linhas, calma) sem pedir salvar de novo."
        )
    return ""


def _executar_fast_track_para_coleta(
    ctx, meta: dict, nome: str, numero_whatsapp: str, msg_lead: str
) -> Tuple[List[Acao], str]:
    """Lead já declarou contato salvo + mensagem curta — pula o sermão de 'salvar' e vai à coleta."""
    meta["lead_contato_salvo_declarado"] = True
    meta["node2_contato_ja_reconhecido"] = True
    meta["node2_fast_track_usado"] = True
    voc = nome if _nome_valido_guardado(nome) else VOCATIVO_SEM_NOME
    acoes: List[Acao] = []
    linha_extra = ""
    if _lead_pergunta_preco(ctx, msg_lead):
        linha_extra = (
            " A consulta inicial é gratuita; valores completos eu te explico depois, com calma."
        )
    if not meta.get("node2_vcard_despachado"):
        acoes.extend(
            [
                Acao(tipo="delay", segundos=random.randint(6, 10)),
                Acao(
                    tipo="text",
                    conteudo=(
                        f"{voc}, vi que você já deixou meu número guardado aí — obrigada pela confiança.{linha_extra} "
                        "Segue meu cartão só pra conferir na agenda."
                    ),
                ),
                Acao(tipo="delay", segundos=random.randint(5, 8)),
                Acao(tipo="vcard", conteudo=numero_whatsapp),
            ]
        )
        meta["node2_vcard_despachado"] = True
    else:
        acoes.extend(
            [
                Acao(tipo="delay", segundos=random.randint(4, 8)),
                Acao(
                    tipo="text",
                    conteudo=f"{voc}, então vamos direto ao que importa: tuas linhas.{linha_extra}",
                ),
            ]
        )
    ctx.estado_coleta = "node2_fast_track_ok"
    ctx.metadata = meta
    logger.info("⚡ [NODE 2] Fast-track (contato já salvo declarado) → coleta.")
    return acoes, "3_coleta_profunda"


def _bot_repetiu_termo_recente(ctx, termo: str, janela_msgs: int = 6) -> bool:
    termo_l = (termo or "").strip().lower()
    if not termo_l:
        return False
    hist = list(getattr(ctx, "historico", None) or [])
    if not hist:
        return False
    candidatos = hist[-janela_msgs:]
    for h in candidatos:
        rem = getattr(h, "remetente", None)
        if rem is None and isinstance(h, dict):
            rem = h.get("remetente")
        if rem != "bot":
            continue
        txt = getattr(h, "texto", None) or (h.get("texto") if isinstance(h, dict) else None) or ""
        if termo_l in str(txt).lower():
            return True
    return False


def _acoes_vcard_sem_pergunta(ctx, numero_whatsapp: str) -> List[Acao]:
    """
    Novo padrão do Node 2:
    envia card com contexto afirmativo (sem perguntar confirmação).
    """
    return [
        Acao(tipo="delay", segundos=random.randint(5, 8)),
        Acao(
            tipo="text",
            conteudo=(
                "Perfeito, deixei meu cartão aqui embaixo para você conferir na agenda "
                + (
                    "e seguimos na leitura."
                    if _bot_repetiu_termo_recente(ctx, "calma")
                    else "e seguimos com calma na leitura."
                )
            ),
        ),
        Acao(tipo="delay", segundos=random.randint(4, 7)),
        Acao(tipo="vcard", conteudo=numero_whatsapp),
    ]


def executar_v2(ctx) -> Tuple[List[Acao], str]:
    """Executa o nó de salvamento de contato."""
    t0_node = time.time()
    meta = getattr(ctx, "metadata", {}) or {}
    if not ctx.metadata:
        ctx.metadata = meta
    # Regra de ouro (fase 1): marca que o Node 2 executou ao menos uma vez
    # para permitir avanços automáticos subsequentes do preflight sem pular o contrato.
    meta["node2_contrato_enviado"] = True

    msg_lead = str(ctx.texto_recebido or "").strip()
    msg_lower = msg_lead.lower()

    if lead_reportou_problema_entrega(msg_lead):
        nome_curto = (ctx.nome_lead or meta.get("nome_lead") or VOCATIVO_SEM_NOME).strip() or VOCATIVO_SEM_NOME
        acoes_reparo = [
            Acao(tipo="delay", segundos=random.randint(3, 5)),
            Acao(
                tipo="text",
                conteudo=f"Obrigada por avisar, {nome_curto}. Vou seguir mais devagar pra você acompanhar certinho.",
                metadata={"skip_gancho_final": True},
            ),
            Acao(tipo="delay", segundos=random.randint(2, 4)),
            Acao(
                tipo="text",
                conteudo="Quando estiver tudo visível aí, me manda um *ok* que eu continuo.",
                metadata={"skip_gancho_final": True},
            ),
        ]
        ctx.estado_coleta = "node2_reparo_entrega"
        ctx.metadata = meta
        elapsed = time.time() - t0_node
        if elapsed > 3.5:
            logger.warning("⏱️ [NODE 2] Reparo de entrega lento: %.2fs", elapsed)
        return acoes_reparo, "2_salvar_contato"
    if _RE_OBJECAO_CARD.search(msg_lead):
        nome_curto = (ctx.nome_lead or meta.get("nome_lead") or VOCATIVO_SEM_NOME).strip() or VOCATIVO_SEM_NOME
        acoes_card = [
            Acao(tipo="delay", segundos=random.randint(3, 5)),
            Acao(
                tipo="text",
                conteudo=f"Perfeito, {nome_curto}. Vou te mandar de novo aqui para ficar fácil de salvar.",
                metadata={"skip_gancho_final": True},
            ),
            Acao(tipo="delay", segundos=random.randint(2, 4)),
            Acao(tipo="vcard", conteudo=(meta.get("__config__", {}) or {}).get("numero_whatsapp") or "+55 92 8497-9419"),
            Acao(tipo="delay", segundos=random.randint(3, 6)),
            Acao(
                tipo="text",
                conteudo="Quando aparecer aí, me manda *ok* que eu sigo contigo.",
                metadata={"skip_gancho_final": True},
            ),
        ]
        ctx.estado_coleta = "node2_reenvio_card"
        ctx.metadata = meta
        elapsed = time.time() - t0_node
        if elapsed > 3.5:
            logger.warning("⏱️ [NODE 2] Reenvio de card lento: %.2fs", elapsed)
        return _normalizar_acoes_texto_node2(acoes_card), "2_salvar_contato"

    # ── 1. NAME LOCK (O CADEADO DE MEMÓRIA) ──
    # Inclui ctx.nome_lead (vindo de lead.nome no engine) — não confundir mensagem curta com nome novo.
    nome_base = _nome_ja_conhecido(meta, ctx)
    if nome_base:
        match = re.search(r"(?:me chamo|sou o|sou a|meu nome [eé])\s+([a-zà-ú]+)", msg_lower)
        if match:
            nome = match.group(1).capitalize()
        else:
            nome = nome_base
    else:
        nome = _limpar_nome(msg_lead)

    ctx.nome_lead = nome
    meta["nome_lead"] = nome
    meta["genero_lead"] = genero_efetivo_para_copy(nome, meta, texto_discurso=msg_lead or None)
    genero_hint = genero_hint_para_prompt(meta)

    config = meta.get("__config__", {})
    numero_whatsapp = config.get("numero_whatsapp") or "+55 92 8497-9419"

    blob_sessao = blob_sessao_usuario(ctx, msg_lead)
    contato_salvo_confirmado = bool(
        meta.get("lead_contato_salvo_declarado") or texto_indica_contato_salvo(blob_sessao)
    )
    if contato_salvo_confirmado:
        meta["lead_contato_salvo_declarado"] = True

    # ── NOVO PADRÃO NODE2 (sem pergunta "salvou?") ──
    # 1) Se já confirmou contato salvo: não dispara textos no node2, vai direto ao node3.
    # 2) Se não confirmou: envia vcard em contexto afirmativo e segue ao node3.
    if contato_salvo_confirmado:
        meta["node2_contato_ja_reconhecido"] = True
        ctx.estado_coleta = "node2_bypass_contato_confirmado"
        ctx.metadata = meta
        return [], "3_coleta_profunda"
    acoes_padrao = _acoes_vcard_sem_pergunta(ctx, numero_whatsapp)
    meta["node2_vcard_despachado"] = True
    meta["node2_contexto_card_enviado"] = True
    ctx.estado_coleta = "node2_vcard_sem_pergunta"
    ctx.metadata = meta
    return _normalizar_acoes_texto_node2(acoes_padrao), "3_coleta_profunda"