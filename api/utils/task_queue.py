"""
api/utils/task_queue.py — Fila de tarefas durável baseada em Redis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Substitui threading.Thread para broadcasts e sequências.
Garante que tarefas sobrevivem a restarts do servidor.

Arquitetura:
  - Producer: enqueue_campaign_send() → RPUSH em redis key 'acassia:tasks:broadcast'
  - Consumer: campaign_worker_loop() → BLPOP + chama _send_campaign_worker
  - Fallback: se Redis indisponível, cai para threading.Thread local
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_BROADCAST_QUEUE = "acassia:tasks:broadcast"
_SEQUENCE_QUEUE = "acassia:tasks:sequence"


def _get_redis():
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as redis_lib
        return redis_lib.Redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
    except Exception:
        return None


def _redis_available() -> bool:
    r = _get_redis()
    if not r:
        return False
    try:
        return r.ping()
    except Exception:
        return False


def enqueue_campaign_send(campaign_id: int, tenant_id: str) -> bool:
    """Enfileira campanha de broadcast. Retorna True se enfileirou no Redis."""
    r = _get_redis()
    if r:
        try:
            payload = json.dumps({"campaign_id": campaign_id, "tenant_id": tenant_id})
            r.rpush(_BROADCAST_QUEUE, payload)
            logger.info("[TASK_QUEUE] Broadcast campaign=%d enfileirada no Redis", campaign_id)
            return True
        except Exception as exc:
            logger.warning("[TASK_QUEUE] Redis indisponível, fallback thread: %s", exc)

    # Fallback: thread local
    from api.saas.broadcast import _send_campaign_worker
    t = threading.Thread(
        target=_send_campaign_worker,
        args=(campaign_id, tenant_id),
        daemon=True,
        name=f"broadcast-fallback-{campaign_id}",
    )
    t.start()
    logger.info("[TASK_QUEUE] Broadcast campaign=%d via thread fallback", campaign_id)
    return False


def enqueue_sequence_process(tenant_id: Optional[str] = None) -> bool:
    """Enfileira processamento de sequências devidas."""
    r = _get_redis()
    if r:
        try:
            payload = json.dumps({"tenant_id": tenant_id})
            r.rpush(_SEQUENCE_QUEUE, payload)
            return True
        except Exception as exc:
            logger.warning("[TASK_QUEUE] Redis indisponível para sequence: %s", exc)

    # Fallback: execução direta
    from api.saas.sequences import process_due_sequence_steps
    try:
        process_due_sequence_steps(tenant_id=tenant_id)
    except Exception as exc:
        logger.exception("[TASK_QUEUE] Falha no fallback de sequence: %s", exc)
    return False


def campaign_worker_loop():
    """Consumer loop — roda como daemon thread. Faz BLPOP no Redis."""
    logger.info("[TASK_QUEUE] Broadcast worker loop iniciado")
    while True:
        try:
            r = _get_redis()
            if not r:
                time.sleep(10)
                continue

            result = r.blpop(_BROADCAST_QUEUE, timeout=30)
            if not result:
                continue

            _, raw = result
            task = json.loads(raw)
            campaign_id = task["campaign_id"]
            tenant_id = task["tenant_id"]

            logger.info("[TASK_QUEUE] Processando broadcast campaign=%d", campaign_id)
            from api.saas.broadcast import _send_campaign_worker
            _send_campaign_worker(campaign_id, tenant_id)

        except Exception as exc:
            logger.exception("[TASK_QUEUE] Erro no worker loop: %s", exc)
            time.sleep(5)


def sequence_worker_loop():
    """Consumer loop para sequências."""
    logger.info("[TASK_QUEUE] Sequence worker loop iniciado")
    while True:
        try:
            r = _get_redis()
            if not r:
                time.sleep(10)
                continue

            result = r.blpop(_SEQUENCE_QUEUE, timeout=30)
            if not result:
                continue

            _, raw = result
            task = json.loads(raw)
            tenant_id = task.get("tenant_id")

            from api.saas.sequences import process_due_sequence_steps
            count = process_due_sequence_steps(tenant_id=tenant_id)
            logger.info("[TASK_QUEUE] Sequências processadas: %d", count)

        except Exception as exc:
            logger.exception("[TASK_QUEUE] Erro no sequence worker: %s", exc)
            time.sleep(5)


def start_workers():
    """Inicia os worker loops como daemon threads. Chamado no startup do app."""
    if not _redis_available():
        logger.warning("[TASK_QUEUE] Redis indisponível — workers não iniciados (fallback ativo)")
        return

    threading.Thread(
        target=campaign_worker_loop,
        daemon=True,
        name="TaskQueue-Broadcast",
    ).start()

    threading.Thread(
        target=sequence_worker_loop,
        daemon=True,
        name="TaskQueue-Sequence",
    ).start()

    logger.info("[TASK_QUEUE] Workers de broadcast e sequência iniciados")
