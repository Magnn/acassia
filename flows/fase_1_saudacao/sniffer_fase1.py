"""
Pré-nó da fase 1 (nodes 1→5) — chamado pelo engine logo após o GLOBAL SNIFFER.

Junta texto atual + histórico do user, marca visita ao Instagram no metadata,
promove coleta quando o burst já trouxe volume/sinais, e adianta lead.node_atual
só para frente (primeiro checklist pendente).

Novas regras desse tipo entram aqui, não em um segundo motor paralelo.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from flows.funnel_gates import PLACEHOLDER_NOMES

logger = logging.getLogger(__name__)

_FASE1_ORDEM = (
    "1_apresentacao",
    "2_salvar_contato",
    "3_coleta_profunda",
    "4_instagram",
    "5_processa_leitura",
)
_NOMES_CHECKLIST_LIXO = PLACEHOLDER_NOMES | frozenset(
    {
        "estou", "sim", "ok", "quero", "vou",
        "salvei", "pronto", "ola", "oi", "ta", "tá", "ja", "já", "blz",
    }
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
    r"medo|ansiedade|desespero|dor|sofre|ajuda"
    r")\b"
)


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


def _nome_valido_checklist(lead: Any, meta: Dict[str, Any]) -> bool:
    for cand in ((getattr(lead, "nome", None) or "").strip(), (meta.get("nome_lead") or "").strip()):
        if not cand or cand.lower() in _NOMES_CHECKLIST_LIXO:
            continue
        if len(cand) >= 2:
            return True
    return False


def _primeiro_node_pendente(meta: Dict[str, Any], lead: Any) -> str:
    if not _nome_valido_checklist(lead, meta):
        return "1_apresentacao"
    if not (meta.get("lead_contato_salvo_declarado") or meta.get("node2_vcard_despachado")):
        return "2_salvar_contato"
    if (meta.get("node3_estado") or "").strip() != "coleta_completa":
        return "3_coleta_profunda"
    if not (meta.get("insta_enviado") or meta.get("lead_declarou_visita_insta")):
        return "4_instagram"
    return "5_processa_leitura"


def _idx_fase1(node: str) -> int:
    try:
        return _FASE1_ORDEM.index(node)
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
    if not _nome_valido_checklist(lead, meta):
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


def resolver_avanco_node_fase1(lead: Any, ctx: Any, meta: Dict[str, Any]) -> None:
    cur = (getattr(lead, "node_atual", "") or "").strip()
    if cur not in _FASE1_ORDEM:
        return
    ideal = _primeiro_node_pendente(meta, lead)
    i_cur, i_ideal = _idx_fase1(cur), _idx_fase1(ideal)
    if i_ideal < 0 or i_cur < 0 or i_ideal <= i_cur:
        return
    lead.node_atual = ideal
    ctx.node_atual = ideal
    meta["funnel_resolvido_para"] = ideal
    logger.info("🧭 [FUNNEL] Avanço %s → %s (lead=%s)", cur, ideal, getattr(lead, "id", "?"))
