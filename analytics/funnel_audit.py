"""
Auditoria de funil — eventos agregáveis sem texto do usuário (LGPD / multi-tenant).
Usado para métricas semanais e debug de jornada por nó.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

EVENTO_NODE_TRANSITION = "funnel.node_transition"
EVENTO_SILENT_ACK = "funnel.silent_ack_user_text"


def msg_len_bucket(texto: str) -> str:
    """Faixa de tamanho da mensagem (nunca armazena o conteúdo)."""
    n = len((texto or "").strip())
    if n == 0:
        return "0"
    if n <= 50:
        return "1-50"
    if n <= 200:
        return "51-200"
    if n <= 800:
        return "201-800"
    return "800+"


def registrar_node_transition(
    db: Any,
    lead_id: int,
    node_from: str,
    node_to: str,
    *,
    intencao: Optional[str] = None,
    sentimento: Optional[str] = None,
    tipo_mensagem: str = "text",
    texto_recebido: str = "",
    origem: str = "engine",
) -> None:
    """Grava transição de nó + snapshot de intenção do turno (sem PII)."""
    if node_from == node_to:
        return
    from db.models import EventoAudit

    dados = {
        "from": (node_from or "")[:120],
        "to": (node_to or "")[:120],
        "intencao": (intencao or "")[:60],
        "sentimento": (sentimento or "")[:60],
        "tipo_mensagem": (tipo_mensagem or "text")[:30],
        "msg_len_bucket": msg_len_bucket(texto_recebido),
        "origem": origem[:40],
    }
    db.add(EventoAudit(lead_id=lead_id, evento=EVENTO_NODE_TRANSITION, dados=dados))


def registrar_silent_ack(
    db: Any,
    lead_id: int,
    node: str,
    *,
    intencao: Optional[str] = None,
    sentimento: Optional[str] = None,
    texto_recebido: str = "",
) -> None:
    """Lead escreveu em estado silencioso (ex.: aguardando_pagamento) — conta engajamento sem transição."""
    from db.models import EventoAudit

    dados = {
        "node": (node or "")[:120],
        "intencao": (intencao or "")[:60],
        "sentimento": (sentimento or "")[:60],
        "msg_len_bucket": msg_len_bucket(texto_recebido),
    }
    db.add(EventoAudit(lead_id=lead_id, evento=EVENTO_SILENT_ACK, dados=dados))
