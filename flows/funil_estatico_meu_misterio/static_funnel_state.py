"""
Estado único do funil estático Meu Mistério — chaves, merge e transições de entrega.

Centraliza convenções:
  - Nó: static_meumisterio_b1 .. b7
  - Metadata base: static_mm_b1 .. (prefixo static_mm_)

Evita divergência entre engine (fila de envio), processar_mensagem (nós) e persistência.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Set

# ── Convenções de nomenclatura ───────────────────────────────────────────────
NODE_PREFIX = "static_meumisterio_b"


def parse_iso_utc(raw: str) -> Optional[datetime]:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def static_mm_base_from_source(source: str) -> Optional[str]:
    """
    `source` em ações: static_meumisterio_b3 -> static_mm_b3
    """
    src = str(source or "").strip().lower()
    if not src.startswith("static_meumisterio_b"):
        return None
    return src.replace("static_meumisterio_", "static_mm_")


def static_mm_base_from_node(node_atual: str) -> Optional[str]:
    """
    node_atual: static_meumisterio_b3 -> static_mm_b3
    """
    n = str(node_atual or "").strip().lower()
    if not n.startswith(NODE_PREFIX):
        return None
    return n.replace("static_meumisterio_", "static_mm_")


def dispatch_em_andamento_recente(meta: dict, base_meta: str, janela_s: int = 900) -> bool:
    """
    True se há dispatch_started_at recente para esse bloco (lead falou no meio do envio).
    base_meta: ex. "static_mm_b4".
    """
    try:
        started = parse_iso_utc((meta or {}).get(f"{base_meta}_dispatch_started_at"))
        if not started:
            return False
        delta = (datetime.now(timezone.utc) - started).total_seconds()
        return 0 <= delta <= max(30, int(janela_s or 900))
    except Exception:
        return False


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def apply_dispatch_started(meta: Dict[str, Any], planned_sources: Iterable[str]) -> Dict[str, Any]:
    """
    Antes de enviar ações do bloco: marca início de dispatch e zera entregue até concluir o lote.
    """
    out = dict(meta or {})
    ts = now_iso_utc()
    for src in planned_sources:
        base = static_mm_base_from_source(src)
        if not base:
            continue
        out[f"{base}_dispatch_started_at"] = ts
        out[f"{base}_entregue"] = False
    return out


def apply_delivered(meta: Dict[str, Any], delivered_sources: Iterable[str]) -> Dict[str, Any]:
    """
    Após envio bem-sucedido de pelo menos uma ação daquele source: entregue=True, last_sent_at, limpa dispatch.
    """
    out = dict(meta or {})
    ts = now_iso_utc()
    for src in delivered_sources:
        base = static_mm_base_from_source(src)
        if not base:
            continue
        out[f"{base}_entregue"] = True
        out[f"{base}_last_sent_at"] = ts
        out.pop(f"{base}_dispatch_started_at", None)
    return out


def merge_metadata_for_persist(existente: Dict[str, Any], ctx_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge defensivo ao salvar após o turno do motor: não sobrescreve entregue/dispatch
    vindos da thread de envio com valores mais antigos em ctx.
    """
    ex = dict(existente or {})
    ctx_m = dict(ctx_metadata or {})
    combinado = dict(ex)
    combinado.update(ctx_m)
    for k, v in ex.items():
        ks = str(k)
        if ks.endswith("_entregue") and bool(v):
            combinado[k] = True
        elif ks.endswith("_last_sent_at") and v and not combinado.get(k):
            combinado[k] = v
        elif ks.endswith("_dispatch_started_at") and v and not combinado.get(k):
            combinado[k] = v
    return combinado


def collect_static_sources_from_acoes(acoes: list) -> Set[str]:
    """Fontes static_meumisterio_b* presentes na lista de ações."""
    out: Set[str] = set()
    for acao in acoes or []:
        meta_acao = getattr(acao, "metadata", None) or {}
        src = str(meta_acao.get("source") or "").strip().lower()
        if src.startswith("static_meumisterio_b"):
            out.add(src)
    return out
