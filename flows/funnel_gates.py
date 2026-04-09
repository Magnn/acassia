"""
flows/funnel_gates.py — predicados centrais da fase 1 (nome, contato, foto, desabafo).

Objetivo: uma única fonte de verdade para regras da fase 1. Leitura (burst, pendências),
*escritas* do sniffer global (`sniffer_aplicar_*`), bypass controlado no node 3
(`meta_node3_forcar_camada1_completa`) e guardrail de contato (`sanear_lead_contato_*`).
O pré-flight (Instagram, burst longo, avanço de nó) está em `flows/fase_1_preflight.py`.

Ver também: docs/FUNIL_MATRIZ_OBRIGATORIOS.md
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Sequence

# Alinhado a copy_sanitizer.extrair_evidencias_conversa (nome_ok) e node_1.
PLACEHOLDER_NOMES = frozenset({"meu bem", "meu anjo", "minha estrela"})

# Tokens que não contam como “primeiro nome” no checklist do pré-flight (além de PLACEHOLDER_NOMES).
NOMES_LIXO_CHECKLIST_FASE1 = PLACEHOLDER_NOMES | frozenset(
    {
        "estou", "sim", "ok", "quero", "vou",
        "salvei", "pronto", "ola", "oi", "ta", "tá", "ja", "já", "blz",
    }
)

# Valor default do vocativo quando o primeiro nome ainda não foi extraído (copy).
VOCATIVO_SEM_NOME = "meu bem"


def nome_eh_placeholder(nome: str) -> bool:
    """True se ainda não há primeiro nome utilizável (vazio ou placeholder de vocativo)."""
    n = (nome or "").strip().lower()
    if not n:
        return True
    return n in PLACEHOLDER_NOMES


def nome_util_para_checklist_fase1(nome: str) -> bool:
    """
    Nome utilizável no checklist da fase 1 (pré-flight e anti-redundância alinhada ao funil).
    Exclui vazio, <2 chars, placeholders e ruído tipo «sim», «ok».
    """
    n = (nome or "").strip()
    if len(n) < 2:
        return False
    return n.lower() not in NOMES_LIXO_CHECKLIST_FASE1


def meta_tem_foto(meta: Optional[Mapping[str, Any]]) -> bool:
    return bool((meta or {}).get("foto_recebida"))


def meta_tem_desabafo(meta: Optional[Mapping[str, Any]]) -> bool:
    return bool((meta or {}).get("desabafo_recebido"))


def meta_declarou_contato_salvo(meta: Optional[Mapping[str, Any]]) -> bool:
    return bool((meta or {}).get("lead_contato_salvo_declarado"))


def meta_node2_vcard_despachado(meta: Optional[Mapping[str, Any]]) -> bool:
    """True se o ritual do node 2 já enviou o cartão (equivalente a contato tratado)."""
    return bool((meta or {}).get("node2_vcard_despachado"))


def texto_declara_contato_salvo(blob_texto_usuario: str) -> bool:
    """Delega para o mesmo detector do node 2 (evita divergência de regex)."""
    from flows.fase_1_saudacao.node_2_salvar_contato import texto_indica_contato_salvo

    return texto_indica_contato_salvo(blob_texto_usuario or "")


def contato_salvo_ou_declarado(
    meta: Optional[Mapping[str, Any]],
    blob_texto_usuario: str,
) -> bool:
    """
    Contato OK para burst / checklist: declarado em texto, flag do sniffer, ou vCard já enviado.
    Alinhado a `promover_burst_fase1_meta` e `primeiro_node_pendente_fase1`.
    """
    return (
        meta_declarou_contato_salvo(meta)
        or meta_node2_vcard_despachado(meta)
        or texto_declara_contato_salvo(blob_texto_usuario)
    )


def pode_burst_coleta_sem_node2(
    meta: Optional[Mapping[str, Any]],
    nome_lead: str,
    blob_texto_usuario: str,
) -> bool:
    """
    Espelha a regra do node 1 (burst inicial → pula node 2, vai à coleta).
    Só True quando nome + (contato declarado) + foto + desabafo já estão satisfeitos.
    """
    if nome_eh_placeholder(nome_lead):
        return False
    if not contato_salvo_ou_declarado(meta, blob_texto_usuario):
        return False
    if not meta_tem_foto(meta):
        return False
    if not meta_tem_desabafo(meta):
        return False
    return True


def pendencias_fase1(
    meta: Optional[Mapping[str, Any]],
    nome_lead: str,
    blob_texto_usuario: str,
) -> Dict[str, bool]:
    """
    Mapa explícito do que ainda falta para o burst completo (referência humana + testes).
    """
    return {
        "falta_nome": nome_eh_placeholder(nome_lead),
        "falta_contato_salvo": not contato_salvo_ou_declarado(meta, blob_texto_usuario),
        "falta_foto": not meta_tem_foto(meta),
        "falta_desabafo": not meta_tem_desabafo(meta),
    }


def snapshot_fase1_coleta(
    meta: Optional[Mapping[str, Any]],
    nome_lead: str,
    blob_texto_usuario: str,
) -> Dict[str, Any]:
    """Telemetria compacta (engine / auditoria)."""
    pend = pendencias_fase1(meta, nome_lead, blob_texto_usuario)
    return {
        "nome_util_ok": not pend["falta_nome"],
        "contato_ok": not pend["falta_contato_salvo"],
        "foto_ok": not pend["falta_foto"],
        "desabafo_ok": not pend["falta_desabafo"],
        "burst_elegivel": pode_burst_coleta_sem_node2(meta, nome_lead, blob_texto_usuario),
        "pendencias": [k for k, v in pend.items() if v],
    }


# ── Sniffer global (engine): mesma semântica que antes, centralizada ─────────

_RE_SNIFFER_INTENCAO_CONSULTA_CURTA = re.compile(
    r"(?i)\b(quero\s+saber|gostaria\s+de\s+saber|preciso\s+saber|"
    r"será\s+que|sera\s+que|vai\s+voltar|volta\s+comigo|volta\s+pra\s+mim|"
    r"minha\s+ex|meu\s+ex|ela\s+volta|ele\s+volta|me\s+ama|"
    r"namora|namorad|casamento|casar\s+com)\b"
)

# Mensagens curtas (4–14 palavras) com carga emocional explícita — o gatilho longo (>8 palavras)
# deixa passar quem manda parágrafos; aqui pegamos o “grito” de 1–2 linhas no WhatsApp.
_RE_SNIFFER_DOR_CURTA = re.compile(
    r"(?i)\b(dor(es)?|dói|doi|sofr\w*|ang[uú]st|ansiedade|desesper\w*|"
    r"chor\w*|medo|traiu|separ\w*|ajuda|urgente|n[aã]o\s+aguento|acab\w*|"
    r"destru[ií]\w*)\b"
)

_SNIFFER_GATILHOS_DESABAFO = (
    "traição",
    "traicao",
    "marido",
    "esposa",
    "ex",
    "dor",
    "sofre",
    "ajuda",
    "dinheiro",
    "urgente",
    "desespero",
    "choro",
    "angústia",
    "angustia",
    "medo",
    "traiu",
    "separou",
    "voltar",
)


def _sniffer_hist_remetente(hm: Any) -> str:
    r = getattr(hm, "remetente", None)
    if r is None and isinstance(hm, dict):
        r = hm.get("remetente")
    return str(r or "")


def _sniffer_hist_tipo(hm: Any) -> str:
    t = getattr(hm, "tipo", None)
    if t is None and isinstance(hm, dict):
        t = hm.get("tipo")
    return str(t or "").lower()


def _sniffer_hist_texto(hm: Any) -> str:
    t = getattr(hm, "texto", None)
    if t is None and isinstance(hm, dict):
        t = hm.get("texto")
    return str(t or "")


def sniffer_aplicar_foto_recebida(
    meta: MutableMapping[str, Any],
    *,
    tipo_mensagem: str,
    historico: Optional[Sequence[Any]] = None,
) -> str:
    """
    Marca `foto_recebida` se há imagem/vídeo neste turno ou já no histórico do user.
    Retorno: rótulo para log no engine ('foto_atual' | 'foto_historico' | '').
    """
    t = (tipo_mensagem or "").strip().lower()
    if t in ("image", "video") and not meta.get("foto_recebida"):
        meta["foto_recebida"] = True
        return "foto_atual"
    if not meta.get("foto_recebida"):
        for hm in historico or []:
            if _sniffer_hist_remetente(hm) != "user":
                continue
            if _sniffer_hist_tipo(hm) in ("image", "video"):
                meta["foto_recebida"] = True
                return "foto_historico"
    return ""


def sniffer_aplicar_contato_declarado(
    meta: MutableMapping[str, Any],
    *,
    texto_sniff: str,
    historico: Optional[Sequence[Any]] = None,
) -> str:
    """
    Marca `lead_contato_salvo_declarado` via o mesmo detector do node 2.
    Retorno: 'contato_atual' | 'contato_historico' | ''.
    """
    from flows.fase_1_saudacao.node_2_salvar_contato import texto_indica_contato_salvo

    if meta.get("lead_contato_salvo_declarado"):
        return ""
    if texto_indica_contato_salvo(texto_sniff):
        meta["lead_contato_salvo_declarado"] = True
        return "contato_atual"
    for hm in historico or []:
        if _sniffer_hist_remetente(hm) != "user":
            continue
        if texto_indica_contato_salvo(_sniffer_hist_texto(hm)):
            meta["lead_contato_salvo_declarado"] = True
            return "contato_historico"
    return ""


def sniffer_aplicar_desabafo_recebido(
    meta: MutableMapping[str, Any],
    *,
    texto_sniff: str,
) -> str:
    """
    Marca `desabafo_recebido` e acumula `desabafo_original` quando o texto tem volume + gatilhos.
    Retorno: 'desabafo' | ''.
    """
    if meta.get("desabafo_recebido"):
        return ""
    msg_lower = (texto_sniff or "").strip().lower()
    palavras_msg = msg_lower.split()
    marcou = len(palavras_msg) > 8 and any(g in msg_lower for g in _SNIFFER_GATILHOS_DESABAFO)
    if not marcou and len(palavras_msg) >= 4 and _RE_SNIFFER_INTENCAO_CONSULTA_CURTA.search(msg_lower):
        marcou = True
    if not marcou and 4 <= len(palavras_msg) <= 14 and _RE_SNIFFER_DOR_CURTA.search(msg_lower):
        marcou = True
    if not marcou:
        return ""
    meta["desabafo_recebido"] = True
    blob = (texto_sniff or "").strip()[:1500]
    prev = (meta.get("desabafo_original") or "").strip()
    meta["desabafo_original"] = f"{prev} {blob}".strip() if prev else blob
    return "desabafo"


def sniffer_aplicar_fase1_flags(
    meta: MutableMapping[str, Any],
    *,
    tipo_mensagem: str,
    texto_sniff: str,
    historico: Optional[Sequence[Any]] = None,
) -> List[str]:
    """
    Aplica as três escritas do sniffer (foto, contato declarado, desabafo).
    Retorna lista de rótulos com eventos disparados (para logs no engine).
    """
    out: List[str] = []
    ev = sniffer_aplicar_foto_recebida(meta, tipo_mensagem=tipo_mensagem, historico=historico)
    if ev:
        out.append(ev)
    ev = sniffer_aplicar_contato_declarado(meta, texto_sniff=texto_sniff, historico=historico)
    if ev:
        out.append(ev)
    ev = sniffer_aplicar_desabafo_recebido(meta, texto_sniff=texto_sniff)
    if ev:
        out.append(ev)
    return out


# ── Node 3: bypass de camada 1 (tentativas esgotadas) ───────────────────────


def meta_node3_forcar_camada1_completa(
    meta: MutableMapping[str, Any],
    *,
    msg_fallback: str,
    falta_foto: bool,
    falta_desabafo: bool,
) -> None:
    """
    Quando o node 3 desbloqueia o funil por limite de tentativas na camada 1.
    Centraliza escritas que antes estavam só no node.
    """
    if falta_foto:
        meta["foto_recebida"] = True
    if falta_desabafo:
        meta["desabafo_recebido"] = True
        meta["desabafo_original"] = (
            (meta.get("desabafo_original") or msg_fallback or "relato em poucas palavras").strip()
        )


# ── Guardrail: nada de `lead_contato_salvo_declarado` “mágico” sem sniffer ──


def sanear_lead_contato_sem_evento_sniffer(
    meta: MutableMapping[str, Any],
    *,
    tinha_antes: bool,
    eventos_sniffer: Sequence[str],
) -> bool:
    """
    Se `lead_contato_salvo_declarado` passou a True neste turno sem evento contato_* do sniffer,
    reverte (defesa contra regressões / NLU escrevendo metadata antes do sniffer).

    Retorna True se reverteu.
    """
    if tinha_antes:
        return False
    if meta.get("lead_contato_salvo_declarado") is not True:
        return False
    if any(e in ("contato_atual", "contato_historico") for e in eventos_sniffer):
        return False
    meta["lead_contato_salvo_declarado"] = False
    return True
