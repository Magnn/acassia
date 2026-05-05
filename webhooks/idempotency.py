"""
webhooks/idempotency.py — Idempotência multi-layer para webhooks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Previne processamento duplicado de mensagens WhatsApp (wamid).
3 camadas (defense in depth):
  1. Redis SET NX EX 24h (atômico, cross-worker) — se disponível
  2. DB UniqueConstraint (durável, sobrevive a restart)
  3. deque in-memory (fallback per-process, quick check sem I/O)

Extraído do app.py para reduzir acoplamento do monolito.
"""

from __future__ import annotations

import logging
import threading
from collections import deque

from sqlalchemy.exc import IntegrityError

from db import models
from db.database import SessionLocal
from tenant_context import get_engine_tenant_id

logger = logging.getLogger(__name__)

# Cache in-memory per-process (quick check sem I/O)
CACHE_MENSAGENS = deque(maxlen=2000)
LOCK_IDEMPOTENCIA = threading.Lock()

# Prefixo Redis para dedup de webhook
_WAMID_DEDUP_PREFIX = "meumisterio:wamid:"
_WAMID_DEDUP_TTL = 86400  # 24h — Meta não reenvia após 24h


def try_claim_wamid_redis(wamid: str) -> bool | None:
    """
    Tenta clamar wamid via Redis SET NX (atômico, cross-worker).
    Retorna True (clamou), False (duplicata), None (Redis indisponível).
    """
    try:
        from reliability.redis_inbound import _client as redis_client_fn
        r = redis_client_fn()
        if r is None:
            return None
        key = f"{_WAMID_DEDUP_PREFIX}{wamid}"
        # SET NX EX: set only if not exists, expire in 24h
        result = r.set(key, "1", nx=True, ex=_WAMID_DEDUP_TTL)
        return bool(result)
    except Exception as e:
        logger.debug("[WEBHOOK] Redis dedup indisponível (fail-open): %s", e)
        return None


def try_claim_wamid_db(wamid: str) -> bool:
    """
    True = primeira vez (seguir para a fila). False = wamid já persistido.
    Camada durável — mantém receipt pra auditoria e sobrevive a restart.
    """
    if not wamid:
        return True
    tid = get_engine_tenant_id()
    db = SessionLocal()
    try:
        db.add(
            models.WhatsAppInboundReceipt(
                tenant_id=tid,
                wamid=str(wamid)[:128],
                lead_id=None,
            )
        )
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False
    except Exception as e:
        db.rollback()
        logger.warning("⚠️ [WEBHOOK] claim wamid falhou (fail-open processa 1x): %s", e)
        return True
    finally:
        db.close()


def is_wamid_duplicate(wamid: str) -> bool:
    """
    Verifica idempotência multi-layer: Redis → DB → deque.
    Retorna True se wamid é duplicata (não processar).
    """
    if not wamid:
        return False

    # Layer 1: Redis (atômico, cross-worker)
    redis_result = try_claim_wamid_redis(wamid)
    if redis_result is False:
        return True  # Já clamado por outro worker
    # Se redis_result é True, já clamamos no Redis — prosseguir para DB

    # Layer 2: DB (durável)
    if not try_claim_wamid_db(wamid):
        return True  # Já existia no DB

    # Layer 3: deque in-memory (quick check local, sem I/O)
    with LOCK_IDEMPOTENCIA:
        if wamid in CACHE_MENSAGENS:
            return True
        CACHE_MENSAGENS.append(wamid)

    return False
