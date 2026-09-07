"""
utils/datetime_helpers.py — Helpers de data/hora centralizados
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Funções utilitárias usadas em múltiplos módulos. Centralizar aqui
evita cópias divergentes e bugs de inconsistência.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Garante que um datetime é timezone-aware (UTC).
    Alguns ORMs podem retornar datetimes sem tzinfo;
    essa função normaliza para comparações seguras.

    Antes: 5 cópias independentes em cron_jobs, lead_scoring,
    funnel_analytics, plans, api/admin/metrics.
    """
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def json_safe_for_api(obj: Any) -> Any:
    """
    Converte objetos para tipos JSON-serializáveis.
    Antes: 3 cópias independentes em app.py, api/routes/__init__.py, flow_platform.py.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except Exception:
            return str(obj)
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, dict):
        return {k: json_safe_for_api(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe_for_api(v) for v in obj]
    return obj


def utc_now() -> datetime:
    """Shortcut para datetime.now(timezone.utc)."""
    return datetime.now(timezone.utc)
