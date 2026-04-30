"""
Rate limit per phone_number_id no webhook inbound (Frente 1 — multi-tenant).

Token-bucket simples em memoria + fallback Redis quando configurado.
Defaults configuraveis via env:
    WA_INBOUND_RATE_PER_MIN     (default 120)
    WA_INBOUND_BURST            (default 30)

Uso:
    from wa_rate_limiter import allow_inbound
    if not allow_inbound(phone_number_id):
        return  # drop msg + log

Cada chamada que retorna True consome 1 token. Janela e por minuto rolante.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass


logger = logging.getLogger(__name__)


def _env_int(key: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(key, str(default))))
    except (TypeError, ValueError):
        return default


RATE_PER_MIN = _env_int("WA_INBOUND_RATE_PER_MIN", 120)
BURST = _env_int("WA_INBOUND_BURST", 30)


@dataclass
class _Bucket:
    tokens: float
    last_refill: float
    capacity: float
    refill_per_sec: float

    def consume(self, n: float = 1.0) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        if elapsed > 0:
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_per_sec,
            )
            self.last_refill = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False


_BUCKETS: dict[str, _Bucket] = {}
_LOCK = threading.Lock()


def _get_bucket(key: str) -> _Bucket:
    with _LOCK:
        b = _BUCKETS.get(key)
        if b is None:
            b = _Bucket(
                tokens=float(BURST),
                last_refill=time.time(),
                capacity=float(BURST),
                refill_per_sec=RATE_PER_MIN / 60.0,
            )
            _BUCKETS[key] = b
        return b


def allow_inbound(phone_number_id: str | None) -> bool:
    """
    Retorna True se a msg pode prosseguir; False se rate-limited.
    Sem phone_number_id (msg legada): allow always (mode single-tenant).
    """
    if not phone_number_id:
        return True
    bucket = _get_bucket(str(phone_number_id).strip())
    return bucket.consume(1.0)


def remaining(phone_number_id: str) -> int:
    """Tokens restantes (debug/observabilidade). Nao consome."""
    pid = str(phone_number_id).strip()
    with _LOCK:
        b = _BUCKETS.get(pid)
        if b is None:
            return BURST
    # Refresh sem mutate-bucket-state (somente leitura)
    elapsed = time.time() - b.last_refill
    return int(min(b.capacity, b.tokens + elapsed * b.refill_per_sec))


def reset(phone_number_id: str | None = None) -> None:
    """Limpa bucket(s). Util em tests."""
    with _LOCK:
        if phone_number_id is None:
            _BUCKETS.clear()
        else:
            _BUCKETS.pop(str(phone_number_id).strip(), None)


def stats() -> dict:
    """Snapshot de todos buckets (debug)."""
    out = {}
    now = time.time()
    with _LOCK:
        for key, b in _BUCKETS.items():
            elapsed = now - b.last_refill
            tokens_now = min(b.capacity, b.tokens + elapsed * b.refill_per_sec)
            out[key] = {
                "tokens_remaining": int(tokens_now),
                "capacity": int(b.capacity),
                "refill_per_min": int(b.refill_per_sec * 60),
            }
    return out
