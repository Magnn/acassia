"""
flows/fase_1_saudacao/node_4_instagram.py — v15 (alinhado ao Node 1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A ANTECÂMARA — Prova social (Instagram) antes da leitura profunda (Node 5).

Mantém: pontuação obrigatória por balão, regex anti-corte, injeção do link + gancho.
🔥 v15: voz Esmeralda Ácassia, tom templo/leitura, PT-BR, gênero no prompt (genero_hint).
"""

import logging
import random
import re
from typing import List, Tuple

from schema import Acao, slice_historico_para_ia
from copy_sanitizer import (
    contexto_lead_para_nodes,
    genero_efetivo_para_copy,
    genero_hint_para_prompt,
    encurtar_balao_preservando_urls,
    limpar_colagem_primeira_msg_whatsapp_em_texto,
    normalizar_link_para_envio,
    preparar_texto_envio,
    sufixo_ancoras_node3_para_prompt,
    tentar_salvar_balao_ia_cortado,
)
from conversation_policy import lead_reportou_problema_entrega
from flows.funnel_gates import nome_eh_placeholder
import flows.fase_2_leitura.node_5_processa_leitura as maestro

logger = logging.getLogger(__name__)

# ── CONFIGURAÇÕES E REGEX DE SEGURANÇA ──
_CONFIRMACOES = {"ok", "pronto", "vi", "visto", "já vi", "ja vi", "beleza", "tá", "ta"}

# Regex que caça terminações abertas (cortes de IA)
_REGEX_CORTE_FATAL = r"([,;:\-]|\b(?:a|ao|as|e|é|eh|éh|foi|o|os|se|à|em|mas|ou|um|uma|que|de|do|da|com|por|para|sem|são|tão|tbm|também|esse|essa|isso|isto|nele|nela|nisso|nisto|meu|seu|sua|minha))\s*$"

# Valida se termina em pontuação ou emoji (Garante conclusão do pensamento)
_PONTUACAO_VALIDA = r".*[.\!\?…\u2600-\u26FF\u2700-\u27BF\U0001f300-\U0001faff]$"
_RE_LINK_VALIDO = re.compile(r"^https?://[^\s/$.?#].[^\s]*\.[A-Za-z]{2,}([/?#].*)?$", re.I)
_RE_LINK_INSTAGRAM_ESTRITO = re.compile(r"^https?://(?:www\.)?instagram\.com/[A-Za-z0-9._\-]+/?$", re.I)
# Lead diz que URL não abre (antes do handoff Node 5): acolher + alternativa (@ ou nome do perfil)
_RE_TEXTO_LINK_IG_QUEBRADO = re.compile(
    r"(?i)(link\s+(quebrad|errad|invalido|inválido)|"
    r"n[aã]o\s+(abre|funciona|entra|carrega)|"
    r"instagram.*(quebrad|errad|n[aã]o\s+abre)|"
    r"\b404\b|p[aá]gina\s+n[aã]o\s+exist)",
)
_RE_PROBLEMA_ENTREGA = re.compile(
    r"(?i)(mensagem\s+cortad|t[aá]\s+atropel|n[aã]o\s+deu\s+tempo|"
    r"n[aã]o\s+deu\s+pra\s+ver|card|cart[aã]o\s+de\s+contato)"
)
_IG_CANONICO_MEU_MISTERIO = "https://www.instagram.com/meumisterio_oficial/"


def _handle_instagram_para_fallback(link_ig: str) -> str:
    """Extrai @usuario de URL instagram.com/usuario (evita segmentos genéricos tipo /reel/)."""
    raw = (link_ig or "").strip()
    if not raw:
        return ""
    m = re.search(r"instagram\.com/([^/?#\s]+)", raw, re.I)
    if not m:
        return ""
    seg = m.group(1).strip().rstrip("/")
    if seg.lower() in ("p", "reel", "reels", "stories", "explore", "accounts", "direct"):
        return ""
    return f"@{seg}"

# ── PROMPT (mesma linha editorial do Node 1: leitura, calma, sem telemarketing) ──
_SYSTEM_ANTECAMARA = """Você é Esmeralda Ácassia (Meu Mistério Esmeralda), a mesma voz dos passos anteriores: quiromancia com presença, como no templo.

ESTÁGIO: ANTECAMARA_PROVA_SOCIAL (acolher o relato, preparar a leitura; o link do perfil vem na mensagem SEGUINTE, automática — não cite URL, @ nem "Instagram")

GÊNERO PARA CONCORDÂNCIA: {genero_hint}

NOME DO LEAD (use com naturalidade se couber): {nome}

CONTEXTO DO DESABAFO (reconheça com respeito; não repita tudo se for longo): {desabafo}

SUA MISSÃO:
1. VALIDAÇÃO: Uma frase curta que mostre que você ouviu a dor dele/dela, sem soar genérica.
2. PREPARO: Diga que vai fechar os olhos e se concentrar nas linhas da palma. Use espaços entre palavras normais (ex.: "cruzando as", nunca "cruzandoas").

FORMATO OBRIGATÓRIO:
- Exatamente 2 balões com [BALAO].
- Cada balão: no máximo 220 caracteres, uma ou duas frases completas, termina com . ou ?
- Sem travessão (—). Sem "—". Máximo 1 emoji no último balão, opcional.
- Não prometa o que vai aparecer nas linhas antes da leitura de verdade.

EXEMPLO:
❌ ERRADO: "Vou focar nas suas linhas, [BALAO] enquanto isso veja isso."
✅ CERTO: "Sinto o peso do que você trouxe, {nome}. [BALAO] Vou me concentrar nas suas linhas agora, com calma."
"""

def _delay_digitacao(texto: str) -> int:
    """Simula o tempo de digitação místico."""
    return max(7, min(len(str(texto)) // 15, 25)) if texto else 5


def _normalizar_link_ig(link_raw: str) -> str:
    """
    Só o que veio do .env (config). Não troca por URL genérica de outro perfil se a regex estrita falhar.
    """
    link = normalizar_link_para_envio(link_raw, instagram_mode=True)
    link = preparar_texto_envio(link, "node4_link_ig").strip()
    if not link:
        return _IG_CANONICO_MEU_MISTERIO
    if _RE_LINK_VALIDO.match(link):
        # Preferir perfil (não reel/página interna) para manter URL estável.
        if _RE_LINK_INSTAGRAM_ESTRITO.match(link):
            return link
        m_perfil = re.search(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._\-]+)/?", link, re.I)
        if m_perfil:
            return f"https://www.instagram.com/{m_perfil.group(1)}/"
        return link
    if re.match(r"^https?://\S{10,}", link, re.I):
        return link.split()[0].rstrip(".,;)")
    # Fallback: tenta extrair um @usuario perdido no texto.
    m_handle = re.search(r"@([A-Za-z0-9._]+)", link_raw or "")
    if m_handle:
        return f"https://www.instagram.com/{m_handle.group(1)}/"
    logger.warning("[NODE 4] link_prova_social inválido no .env. Usando canônico do Meu Mistério.")
    return _IG_CANONICO_MEU_MISTERIO


def _encurtar_balao_node4(texto: str, limite: int = 170) -> str:
    return encurtar_balao_preservando_urls(texto, limite)


def _acoes_texto_e_url_instagram(link_ig: str, imagem_perfil_ig: str = "") -> List[Acao]:
    """Ponte verbal + URL isolada, ou aviso se .env não tiver LINK_INSTAGRAM."""
    if not (link_ig or "").strip():
        logger.warning(
            "[NODE 4] link_prova_social vazio — defina LINK_INSTAGRAM ou CLIENTE_LINK_PROVA_SOCIAL no .env"
        )
        return [
            Acao(tipo="delay", segundos=random.randint(6, 10)),
            Acao(
                tipo="text",
                conteudo=(
                    "O link direto do perfil ainda não está configurado no sistema. "
                    "Busca a gente pelo @ do Instagram que você já viu na conversa, ou me pede o link aqui que eu te mando."
                ),
                metadata={"skip_gancho_final": True},
            ),
        ]
    out = [Acao(tipo="delay", segundos=random.randint(4, 7))]
    if (imagem_perfil_ig or "").strip():
        out.extend(
            [
                Acao(tipo="image", url=imagem_perfil_ig.strip()),
                Acao(tipo="delay", segundos=random.randint(4, 7)),
            ]
        )
    else:
        logger.debug(
            "[NODE 4] imagem_perfil_instagram vazio — só texto+link (CLIENTE_IMAGEM_PERFIL_INSTAGRAM / IMAGEM_PERFIL_INSTAGRAM_URL no .env)."
        )
    out.extend([
        Acao(
            tipo="text",
            conteudo=(
                "Esse é o perfil do templo, com depoimentos e o trabalho. Acesso direto:"
            ),
            metadata={"skip_gancho_final": True},
        ),
        Acao(
            tipo="text",
            conteudo=link_ig.strip(),
            metadata={"skip_gancho_final": True},
        ),
    ])
    return out


def _texto_relevante_para_node5(texto: str) -> bool:
    t = (texto or "").strip().lower()
    if not t:
        return False
    if t in _CONFIRMACOES:
        return False
    if len(t.split()) <= 1:
        return False
    if _RE_TEXTO_LINK_IG_QUEBRADO.search(t):
        return False
    if _RE_PROBLEMA_ENTREGA.search(t):
        return False
    return True

def executar_v2(ctx) -> Tuple[List[Acao], str]:
    """Executa o nó de antecâmara e prova social."""
    meta = getattr(ctx, "metadata", {}) or {}
    _seg = contexto_lead_para_nodes(ctx.nome_lead or "", meta, dor_max_len=90, desabafo_max_len=1200)
    nome_fmt = _seg["nome_fmt"]
    texto_puro = str(ctx.texto_recebido or "").strip()
    genero = genero_efetivo_para_copy(ctx.nome_lead or "", meta, texto_discurso=texto_puro or None)
    meta["genero_lead"] = genero

    config = meta.get("__config__", {})
    link_ig = _normalizar_link_ig(str(config.get("link_prova_social") or ""))
    imagem_perfil_ig = str(config.get("imagem_perfil_instagram") or "").strip()
    if _texto_relevante_para_node5(texto_puro):
        meta["contexto_extra_final"] = texto_puro

    # 1) Reparo explícito quando lead relata entrega ruim/cortada.
    if lead_reportou_problema_entrega(texto_puro):
        meta["node4_contrato_enviado"] = True
        acoes_reparo = [
            Acao(tipo="delay", segundos=random.randint(3, 5)),
            Acao(
                tipo="text",
                conteudo=f"Obrigada por avisar, {nome_fmt}. Eu vi aqui e vou no ritmo certo pra você acompanhar.",
                metadata={"skip_gancho_final": True},
            ),
            Acao(tipo="delay", segundos=random.randint(2, 4)),
            Acao(
                tipo="text",
                conteudo="Me manda um *ok* e eu continuo com calma daqui.",
                metadata={"skip_gancho_final": True},
            ),
        ]
        ctx.estado_coleta = "node4_reparo_entrega"
        ctx.metadata = meta
        return acoes_reparo, "4_instagram"

    # 2) Se o lead já confirmou/bateu no insta, só fazemos reparo se link quebrou; caso contrário, handoff direto.
    if bool(meta.get("lead_declarou_visita_insta") or meta.get("insta_enviado")):
        meta["node4_contrato_enviado"] = True
        acoes_pre: List[Acao] = []
        if _RE_TEXTO_LINK_IG_QUEBRADO.search(texto_puro):
            handle = _handle_instagram_para_fallback(link_ig)
            voc = nome_fmt if nome_fmt and not nome_eh_placeholder(str(nome_fmt)) else "você"
            if handle:
                linha = (
                    f"{voc}, às vezes o app torce o link. Abre com calma de novo, "
                    f"ou busca no Instagram pelo perfil {handle}, é o mesmo lugar."
                )
            else:
                exib = ((config.get("perfil_negocio") or {}).get("nome_exibicao") or "Meu Mistério Esmeralda")
                linha = (
                    f"{voc}, às vezes o WhatsApp corta o link. Busca pelo nome {exib} no Instagram "
                    "ou me diz aqui que te ajudo a achar."
                )
            acoes_pre = [
                Acao(tipo="delay", segundos=random.randint(4, 7)),
                Acao(tipo="text", conteudo=linha, metadata={"skip_gancho_final": True}),
            ]
        meta["insta_enviado"] = True
        meta["node4_bypass_insta_confirmado"] = True
        ctx.estado_coleta = "node4_handoff_para_node5"
        ctx.metadata = meta
        return acoes_pre, "5_processa_leitura"

    # 3) Padrão fixo: envia perfil sem perguntar e avança para leitura.
    acoes_instagram = _acoes_texto_e_url_instagram(link_ig, imagem_perfil_ig)
    meta["node4_contrato_enviado"] = True
    meta["insta_enviado"] = True
    meta["node5_ignorar_ruido_um_turno"] = True
    ctx.estado_coleta = "node4_envio_insta_sem_pergunta"
    ctx.metadata = meta
    return acoes_instagram, "5_processa_leitura"

def _balao_node4_aceito(c: str) -> bool:
    if len(c) < 5:
        return False
    # Rejeita terminação em reticência com palavra final curta (ex.: "cl...", "sen...")
    if re.search(r"\b[A-Za-zÀ-ÿ]{1,3}\.{3}\s*$", c):
        return False
    if re.search(_REGEX_CORTE_FATAL, c.lower()):
        return False
    if not re.match(_PONTUACAO_VALIDA, c):
        return False
    return True


def _tratar_frases_ia(texto: str) -> List[str]:
    """🛡️ STRICT PUNCTUATION SHIELD + recuperação de truncamento da IA 🛡️"""
    partes = re.split(r'\[?BAL[AÃ]O\]?', texto, flags=re.IGNORECASE)
    frases_ok = []

    for frase in partes:
        c = re.sub(r"\[.*?\]", "", frase).strip()
        c = re.sub(r"[-–—*•]+", "", c).strip()

        if len(c) < 5:
            continue

        if _balao_node4_aceito(c):
            frases_ok.append(limpar_colagem_primeira_msg_whatsapp_em_texto(c))
            continue

        c2 = tentar_salvar_balao_ia_cortado(c, _REGEX_CORTE_FATAL)
        if _balao_node4_aceito(c2):
            frases_ok.append(limpar_colagem_primeira_msg_whatsapp_em_texto(c2))
            continue

        logger.warning("⚠️ [NODE 4] Balão rejeitado após recuperação: '%s'", c[:200])
    return frases_ok


def _baloes_node4_de_paragrafos(texto_bruto: str) -> List[str]:
    """
    Se a IA não usou [BALAO], tenta 2 parágrafos separados por linha em branco (mesmo critério de pontuação).
    """
    raw = re.sub(r"`{3}(?:json|text)?|`{3}", "", texto_bruto or "")
    raw = re.sub(r"\[?BAL[AÃ]O\]?", "\n\n", raw, flags=re.I)
    out: List[str] = []
    for bloco in re.split(r"\n\s*\n", raw.strip()):
        c = re.sub(r"\[.*?\]", "", bloco).strip()
        c = re.sub(r"[-–—*•]+", "", c).strip()
        if len(c) < 25:
            continue
        if _balao_node4_aceito(c):
            out.append(limpar_colagem_primeira_msg_whatsapp_em_texto(c))
        else:
            c2 = tentar_salvar_balao_ia_cortado(c, _REGEX_CORTE_FATAL)
            if _balao_node4_aceito(c2):
                out.append(limpar_colagem_primeira_msg_whatsapp_em_texto(c2))
        if len(out) >= 2:
            break
    return out[:2]