"""
Telemetria de produto — emite eventos estruturados em JSON log que podem
ser ingeridos depois por PostHog / Mixpanel / Amplitude server-side.

Por enquanto só loga (formato JSON-line tagged ``[ANALYTICS]``). Quando
quisermos pipeline real, basta plugar um forwarder no logger handler
ou um POST para ingestão server-side.

Eventos canônicos (Sprint 1):
- ``signup_completed``         — usuário concluiu signup
- ``onboarding_step_completed`` — finalizou um step do wizard
- ``first_message_sent``        — primeira msg outbound do tenant

Uso::

    from analytics_telemetry import track
    track("signup_completed", tenant_id="abc", user_id=123, email="x@y.com")
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger("analytics")


def track(
    event: str,
    *,
    tenant_id: Optional[str] = None,
    user_id: Optional[int] = None,
    distinct_id: Optional[str] = None,
    **props: Any,
) -> None:
    """
    Registra um evento de produto. Dedupe / idempotência são responsabilidade
    do caller (ex.: ``first_message_sent`` deve ser disparado uma única vez
    por tenant — checar antes de chamar).

    ``distinct_id`` é o identificador do "ator" pra PostHog/Mixpanel. Default:
    ``tenant_id`` (1 user = 1 tenant nessa fase).
    """
    payload = {
        "ts": int(time.time() * 1000),
        "event": event,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "distinct_id": distinct_id or tenant_id or (str(user_id) if user_id else None),
        "props": _sanitize_props(props),
    }
    try:
        logger.info("[ANALYTICS] %s", json.dumps(payload, ensure_ascii=False, default=str))
    except Exception as exc:  # nunca quebra fluxo principal
        logger.warning("[ANALYTICS] falha serializando evento %s: %s", event, exc)


def _sanitize_props(props: dict) -> dict:
    """Remove valores None e trunca strings muito grandes (proteção PII / log spam)."""
    out: dict = {}
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, str) and len(v) > 500:
            v = v[:500] + "…"
        out[k] = v
    return out
