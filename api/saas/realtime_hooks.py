"""
api/saas/realtime_hooks.py — Hooks de evento para integração com o SSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Funções helper para publicar eventos SSE de qualquer ponto do código.
São fire-and-forget (nunca bloqueiam, nunca falham silenciosamente).

Uso (em qualquer módulo que salva/processa mensagens):
    from api.saas.realtime_hooks import notify_message_created, notify_lead_updated

    # Após salvar mensagem no banco
    notify_message_created(tenant_id, lead_id, msg_id, texto, remetente)

    # Após atualizar status do lead
    notify_lead_updated(tenant_id, lead_id, changes={"bot_pausado": True})
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


def _fire_and_forget(fn):
    """Decorator que executa em thread para não bloquear o caller."""
    def wrapper(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            logger.debug("[REALTIME] Evento falhou (ignorado): %s", exc)
    return wrapper


@_fire_and_forget
def notify_message_created(
    tenant_id: str,
    lead_id: int,
    message_id: int | None = None,
    texto: str = "",
    remetente: str = "system",
) -> None:
    """Publica evento de nova mensagem para todos os browsers conectados."""
    from api.saas.realtime import publish_inbox_event
    publish_inbox_event(tenant_id, "message_created", {
        "lead_id": lead_id,
        "message_id": message_id,
        "texto": (texto or "")[:120],  # preview
        "remetente": remetente,
    })


@_fire_and_forget
def notify_lead_updated(
    tenant_id: str,
    lead_id: int,
    changes: dict | None = None,
) -> None:
    """Publica evento de atualização de lead (status, score, etc.)."""
    from api.saas.realtime import publish_inbox_event
    publish_inbox_event(tenant_id, "lead_updated", {
        "lead_id": lead_id,
        "changes": changes or {},
    })


@_fire_and_forget
def notify_typing(
    tenant_id: str,
    lead_id: int,
) -> None:
    """Publica evento de typing indicator (lead digitando)."""
    from api.saas.realtime import publish_inbox_event
    publish_inbox_event(tenant_id, "typing", {
        "lead_id": lead_id,
    })
