"""Métricas e auditoria de funil (sem PII em eventos estruturados)."""

from analytics.funnel_audit import (
    EVENTO_NODE_TRANSITION,
    EVENTO_SILENT_ACK,
    registrar_node_transition,
    registrar_silent_ack,
    msg_len_bucket,
)

__all__ = [
    "EVENTO_NODE_TRANSITION",
    "EVENTO_SILENT_ACK",
    "registrar_node_transition",
    "registrar_silent_ack",
    "msg_len_bucket",
]
