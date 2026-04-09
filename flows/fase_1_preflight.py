"""
Pré-nó da fase 1 (nodes 1→5) — Instagram, burst textual, avanço de checklist.

Chamado pelo `engine` após `sniffer_aplicar_fase1_flags` (escritas em `funnel_gates`).
Toda a lógica de pré-node ficou aqui; `sniffer_fase1.py` só reexporta para compatibilidade.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple

from flows.funnel_gates import nome_util_para_checklist_fase1

logger = logging.getLogger(__name__)

FASE1_ORDEM: Tuple[str, ...] = (
    "1_apresentacao",
    "2_salvar_contato",
    "3_coleta_profunda",
    "4_instagram",
    "5_processa_leitura",
)

_RE_VISITA_INSTA = re.compile(
    r"(?i)\b("
    r"já\s+vi|ja\s+vi|visitei|acessei|entrei\s+no|olhei\s+o|passo\s+no|"
    r"segui|seguido|seguindo|instagram|insta\b|instag|"
    r"perfil\s+do|vi\s+o\s+perfil|vi\s+seu\s+perfil|vi\s+teu\s+perfil|"
    r"reels|stories|publicaç|publiquei|curti\s+as?\s+fotos"
    r")\b"
)
_RE_BURST_DESEJO_DOR = re.compile(
    r"(?i)\b("
    r"quero\s+saber|gostaria|preciso|volta|voltar|ex|amor|namor|casamento|"
    r"trai|traiu|separ|dinheiro|dívida|divida|família|familia|filho|filha|mãe|mae|"
    r"medo|ansiedade|desespero|dor|sofre|ajuda|sinto|peito|perdi|falei|coração|coraçao"
    r")\b"
)
_RE_TENTATIVA = re.compile(r"(?i)\b(j[aá]\s+tentei|tentei|fiz\s+de\s+tudo|ja\s+fiz\s+de\s+tudo)\b")
_RE_TEMPO = re.compile(
    r"(?i)\b(h[aá]\s*\d{1,2}\s*(?:anos?|mes(?:es)?|semanas?|dias?)|\d{1,2}\s*(?:anos?|mes(?:es)?|semanas?|dias?)\b)"
)
_RE_GATILHO = re.compile(r"(?i)\b(desde que|depois que|quando)\b")
_RE_DESEJO = re.compile(r"(?i)\b(quero|gostaria|desejo|busco|sonho)\b")


def concat_texto_usuario(ctx: Any, texto_atual: str) -> str:
    partes: List[str] = []
    seen: set[str] = set()
    cur = (texto_atual or "").strip()
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


def nome_valido_checklist_fase1(lead: Any, meta: Dict[str, Any]) -> bool:
    """True se há nome utilizável (DB ou metadata) — mesma regra que `nome_util_para_checklist_fase1`."""
    for cand in ((getattr(lead, "nome", None) or "").strip(), (meta.get("nome_lead") or "").strip()):
        if nome_util_para_checklist_fase1(cand):
            return True
    return False


def primeiro_node_pendente_fase1(meta: Dict[str, Any], lead: Any) -> str:
    """Primeiro passo da fase 1 ainda não satisfeito (ordem fixa)."""
    if not nome_valido_checklist_fase1(lead, meta):
        return "1_apresentacao"
    if not (meta.get("lead_contato_salvo_declarado") or meta.get("node2_vcard_despachado")):
        return "2_salvar_contato"
    if (meta.get("node3_estado") or "").strip() != "coleta_completa":
        return "3_coleta_profunda"
    if not (meta.get("insta_enviado") or meta.get("lead_declarou_visita_insta")):
        return "4_instagram"
    return "5_processa_leitura"


def idx_fase1_ordem(node: str) -> int:
    try:
        return FASE1_ORDEM.index(node)
    except ValueError:
        return -1


def sniffer_instagram_meta(meta: Dict[str, Any], texto_full: str, lead_id: int) -> None:
    if not (texto_full or "").strip():
        return
    if _RE_VISITA_INSTA.search(texto_full) and not meta.get("lead_declarou_visita_insta"):
        meta["lead_declarou_visita_insta"] = True
        logger.info("📸 [SNIFFER] lead_declarou_visita_insta (lead=%s)", lead_id)


def promover_burst_fase1_meta(meta: Dict[str, Any], texto_full: str, lead_id: int, lead: Any) -> None:
    if meta.get("node3_estado") == "coleta_completa":
        if meta.get("lead_declarou_visita_insta") and not meta.get("insta_enviado"):
            meta["insta_enviado"] = True
            meta["node5_ignorar_ruido_um_turno"] = True
            logger.info("📸 [SNIFFER] insta_enviado pós-coleta por visita declarada (lead=%s)", lead_id)
        return
    if not nome_valido_checklist_fase1(lead, meta):
        return
    palavras = len((texto_full or "").split())
    if palavras < 45:
        return
    if not (meta.get("foto_recebida") and meta.get("desabafo_recebido")):
        return
    if not (meta.get("lead_contato_salvo_declarado") or meta.get("node2_vcard_despachado")):
        return
    if not _RE_BURST_DESEJO_DOR.search(texto_full or ""):
        return
    blob = (texto_full or "").strip()
    meta["node3_estado"] = "coleta_completa"
    meta["desabafo_original"] = (meta.get("desabafo_original") or blob[:2000]).strip()[:2000]
    meta["desejo_declarado"] = (meta.get("desejo_declarado") or blob[:900]).strip()[:2000]
    meta["aprofundamento_texto"] = (meta.get("aprofundamento_texto") or blob[:2000]).strip()[:2000]
    if not (meta.get("universo_desejo") or "").strip():
        meta["universo_desejo"] = "geral"
    if _RE_VISITA_INSTA.search(texto_full):
        meta["lead_declarou_visita_insta"] = True
        meta["insta_enviado"] = True
        meta["node5_ignorar_ruido_um_turno"] = True
        logger.info("⚡ [SNIFFER] Burst → coleta_completa + insta (lead=%s, ~%s palavras)", lead_id, palavras)
    else:
        logger.info("⚡ [SNIFFER] Burst → coleta_completa (lead=%s, ~%s palavras)", lead_id, palavras)


def enriquecer_dados_node3_precoce(meta: Dict[str, Any], texto_full: str, lead_id: int) -> None:
    """
    Extrai sinais de coleta profunda já no início da conversa para o node3 aproveitar.
    Não marca coleta completa sozinho; apenas preenche campos úteis.
    """
    texto = (texto_full or "").strip()
    if not texto:
        return
    low = texto.lower()

    if _RE_DESEJO.search(low) and not (meta.get("desejo_declarado") or "").strip():
        meta["desejo_declarado"] = texto[:900]
        logger.info("🧩 [PREFLIGHT] desejo_declarado precoce (lead=%s)", lead_id)

    if (_RE_TEMPO.search(low) or _RE_TENTATIVA.search(low) or _RE_GATILHO.search(low)) and not (
        meta.get("aprofundamento_texto") or ""
    ).strip():
        meta["aprofundamento_texto"] = texto[:2000]
        logger.info("🧩 [PREFLIGHT] aprofundamento_texto precoce (lead=%s)", lead_id)

    if _RE_TEMPO.search(low) and not (meta.get("tempo_exato") or "").strip():
        m = _RE_TEMPO.search(texto)
        if m:
            meta["tempo_exato"] = m.group(0)[:120]

    if _RE_GATILHO.search(low) and not (meta.get("evento_gatilho") or "").strip():
        m = _RE_GATILHO.search(texto)
        if m:
            idx = m.start()
            trecho = texto[idx : idx + 220].strip()
            if trecho:
                meta["evento_gatilho"] = trecho


def resolver_avanco_node_fase1(lead: Any, ctx: Any, meta: Dict[str, Any]) -> None:
    cur = (getattr(lead, "node_atual", "") or "").strip()
    if cur not in FASE1_ORDEM:
        return
    # Regra de ouro: node1 precisa executar ao menos uma vez antes de qualquer avanço automático.
    # Evita pular saudação/apresentação/vaga/pergunta de nome quando o sniffer já trouxe nome no primeiro batch.
    if cur == "1_apresentacao" and not bool(meta.get("node1_contrato_enviado")):
        return
    ideal = primeiro_node_pendente_fase1(meta, lead)
    i_cur, i_ideal = idx_fase1_ordem(cur), idx_fase1_ordem(ideal)
    if i_ideal < 0 or i_cur < 0:
        return
    # Checklist pede um passo *antes* do nó atual (ex.: metadata resetada): não retrocede automaticamente.
    if i_ideal < i_cur:
        logger.warning(
            "⚠️ [FUNNEL] Descompasso: checklist indica %s (idx=%s) mas node_atual=%s (idx=%s) lead=%s — não retrocede",
            ideal,
            i_ideal,
            cur,
            i_cur,
            getattr(lead, "id", "?"),
        )
        return
    if i_ideal <= i_cur:
        return
    lead.node_atual = ideal
    ctx.node_atual = ideal
    meta["funnel_resolvido_para"] = ideal
    logger.info("🧭 [FUNNEL] Avanço %s → %s (lead=%s)", cur, ideal, getattr(lead, "id", "?"))
