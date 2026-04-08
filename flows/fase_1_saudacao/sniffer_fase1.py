"""
Compatibilidade: reexporta o pré-flight da fase 1.

Implementação viva: `flows/fase_1_preflight.py` (Instagram, burst, avanço de nó).
"""

from flows.fase_1_preflight import (  # noqa: F401
    FASE1_ORDEM,
    concat_texto_usuario,
    idx_fase1_ordem,
    nome_valido_checklist_fase1,
    primeiro_node_pendente_fase1,
    promover_burst_fase1_meta,
    resolver_avanco_node_fase1,
    sniffer_instagram_meta,
)
