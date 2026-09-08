"""Reliable Redis queue with leases, retries and a dead-letter queue."""
from __future__ import annotations

import contextlib
import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)
_PREFIX = "acassia:tasks"
_KINDS = ("broadcast", "sequence")
_LEASE_SECONDS = int(os.getenv("TASK_QUEUE_LEASE_SECONDS", "300"))
_MAX_ATTEMPTS = int(os.getenv("TASK_QUEUE_MAX_ATTEMPTS", "5"))


def _key(kind: str, suffix: str) -> str:
    return f"{_PREFIX}:{kind}:{suffix}"


def _get_redis():
    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as redis_lib
        return redis_lib.Redis.from_url(url, decode_responses=True, socket_connect_timeout=3)
    except Exception:
        return None


def _redis_available() -> bool:
    r = _get_redis()
    try:
        return bool(r and r.ping())
    except Exception:
        return False


def _enqueue(kind: str, payload: dict) -> bool:
    r = _get_redis()
    if not r:
        logger.error("[TASK_QUEUE] Redis unavailable; %s job rejected", kind)
        return False
    job_id = str(uuid.uuid4())
    job = {"id": job_id, "kind": kind, "payload": payload, "attempts": 0,
           "created_at": datetime.now(timezone.utc).isoformat()}
    try:
        pipe = r.pipeline(transaction=True)
        pipe.hset(_key(kind, "jobs"), job_id, json.dumps(job))
        pipe.rpush(_key(kind, "ready"), job_id)
        pipe.execute()
        logger.info("[TASK_QUEUE] job=%s kind=%s queued", job_id, kind)
        return True
    except Exception as exc:
        logger.exception("[TASK_QUEUE] Failed to enqueue %s: %s", kind, exc)
        return False


def enqueue_campaign_send(campaign_id: int, tenant_id: str) -> bool:
    return _enqueue("broadcast", {"campaign_id": campaign_id, "tenant_id": tenant_id})


def enqueue_sequence_process(tenant_id: Optional[str] = None) -> bool:
    return _enqueue("sequence", {"tenant_id": tenant_id})


_RESERVE_SCRIPT = """
local id = redis.call('LPOP', KEYS[1])
if not id then return nil end
local payload = redis.call('HGET', KEYS[2], id)
if not payload then return nil end
redis.call('ZADD', KEYS[3], ARGV[1], id)
return payload
"""
_PROMOTE_SCRIPT = """
local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, 100)
for _, id in ipairs(ids) do
  if redis.call('ZREM', KEYS[1], id) == 1 then redis.call('RPUSH', KEYS[2], id) end
end
return #ids
"""


def _promote_and_recover(r, kind: str, now: float) -> None:
    r.eval(_PROMOTE_SCRIPT, 2, _key(kind, "delayed"), _key(kind, "ready"), now)
    r.eval(_PROMOTE_SCRIPT, 2, _key(kind, "processing"), _key(kind, "ready"), now)


def _reserve(r, kind: str) -> Optional[dict]:
    now = time.time()
    _promote_and_recover(r, kind, now)
    raw = r.eval(_RESERVE_SCRIPT, 3, _key(kind, "ready"), _key(kind, "jobs"),
                 _key(kind, "processing"), now + _LEASE_SECONDS)
    return json.loads(raw) if raw else None


def _ack(r, job: dict) -> None:
    kind, job_id = job["kind"], job["id"]
    pipe = r.pipeline(transaction=True)
    pipe.zrem(_key(kind, "processing"), job_id)
    pipe.hdel(_key(kind, "jobs"), job_id)
    pipe.execute()


def _retry(r, job: dict, exc: Exception) -> None:
    kind, job_id = job["kind"], job["id"]
    job["attempts"] = int(job.get("attempts", 0)) + 1
    job["last_error"] = str(exc)[:500]
    serialized = json.dumps(job)
    pipe = r.pipeline(transaction=True)
    pipe.zrem(_key(kind, "processing"), job_id)
    if job["attempts"] >= _MAX_ATTEMPTS:
        pipe.rpush(_key(kind, "dead"), serialized)
        pipe.hdel(_key(kind, "jobs"), job_id)
        logger.error("[TASK_QUEUE] job=%s exhausted retries and entered DLQ", job_id)
    else:
        delay = min(300, 2 ** job["attempts"])
        pipe.hset(_key(kind, "jobs"), job_id, serialized)
        pipe.zadd(_key(kind, "delayed"), {job_id: time.time() + delay})
        logger.warning("[TASK_QUEUE] job=%s retry=%d in %ds", job_id, job["attempts"], delay)
    pipe.execute()


@contextlib.contextmanager
def _lease_heartbeat(r, kind: str, job_id: str, interval: float = 30.0, lease_seconds: int = _LEASE_SECONDS):
    """Renova periodicamente o lease do job no sorted set processing para jobs longos."""
    stop_event = threading.Event()

    def _heartbeat():
        while not stop_event.wait(interval):
            try:
                now = time.time()
                r.zadd(_key(kind, "processing"), {job_id: now + lease_seconds})
                logger.debug("[TASK_QUEUE] Lease renewed for %s:%s until %s", kind, job_id, now + lease_seconds)
            except Exception as exc:
                logger.warning("[TASK_QUEUE] Failed to renew lease for %s:%s: %s", kind, job_id, exc)

    t = threading.Thread(target=_heartbeat, daemon=True, name=f"lease-heartbeat-{kind}-{job_id[:8]}")
    t.start()
    try:
        yield
    finally:
        stop_event.set()
        t.join(timeout=1.0)


def _execute(job: dict) -> None:
    payload = job["payload"]
    if job["kind"] == "broadcast":
        from api.saas.broadcast import _send_campaign_worker
        _send_campaign_worker(payload["campaign_id"], payload["tenant_id"])
    elif job["kind"] == "sequence":
        from api.saas.sequences import process_due_sequence_steps
        process_due_sequence_steps(tenant_id=payload.get("tenant_id"))
    else:
        raise ValueError(f"Unsupported task kind: {job['kind']}")


def worker_loop(kind: str) -> None:
    if kind not in _KINDS:
        raise ValueError(f"Unsupported worker kind: {kind}")
    logger.info("[TASK_QUEUE] %s worker started", kind)
    while True:
        r = _get_redis()
        if not r:
            time.sleep(5)
            continue
        try:
            job = _reserve(r, kind)
            if not job:
                time.sleep(1)
                continue
            try:
                with _lease_heartbeat(r, kind, job["id"]):
                    _execute(job)
            except Exception as exc:
                logger.exception("[TASK_QUEUE] job=%s failed", job.get("id"))
                _retry(r, job, exc)
            else:
                _ack(r, job)
        except Exception as exc:
            logger.exception("[TASK_QUEUE] %s worker connection error: %s", kind, exc)
            time.sleep(5)


def campaign_worker_loop():
    worker_loop("broadcast")


def sequence_worker_loop():
    worker_loop("sequence")


def start_workers() -> bool:
    """Start embedded workers only when explicitly enabled for local development."""
    if os.getenv("TASK_WORKERS_IN_WEB", "0").lower() not in ("1", "true", "yes"):
        logger.info("[TASK_QUEUE] Embedded workers disabled; run task_worker.py")
        return False
    if not _redis_available():
        logger.error("[TASK_QUEUE] Redis unavailable; workers not started")
        return False
    for kind in _KINDS:
        threading.Thread(target=worker_loop, args=(kind,), daemon=True,
                         name=f"TaskQueue-{kind}").start()
    return True


def run_workers() -> None:
    """Run both consumers as a dedicated long-lived process."""
    threads = [threading.Thread(target=worker_loop, args=(kind,), name=f"TaskQueue-{kind}")
               for kind in _KINDS]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
