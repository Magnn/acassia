"""
reliability/distributed_lock.py — Locks distribuídos via Redis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Substitui threading.Lock para cenários multi-worker (gunicorn + gevent).

Usa SET NX PX para atomicidade + TTL auto-expire (sem deadlock eterno).
Fallback transparente para threading.Lock quando Redis não está disponível.

Uso:
    from reliability.distributed_lock import DistributedLock

    lock = DistributedLock("engine:lead:12345", ttl_ms=90000)
    acquired = lock.acquire(timeout=8.0)
    if acquired:
        try:
            ...  # seção crítica
        finally:
            lock.release()

Ou como context manager:
    with DistributedLock("engine:lead:12345") as acquired:
        if acquired:
            ...
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None
_redis_init_done = False
_redis_lock = threading.Lock()


def _get_redis():
    """Lazy init do cliente Redis. Retorna None se não configurado."""
    global _redis_client, _redis_init_done
    if _redis_init_done:
        return _redis_client
    with _redis_lock:
        if _redis_init_done:
            return _redis_client
        url = (os.getenv("REDIS_URL") or "").strip()
        if not url:
            logger.info("[DLOCK] REDIS_URL não configurada — usando fallback local (threading.Lock)")
            _redis_init_done = True
            return None
        try:
            import redis
            _redis_client = redis.from_url(url, decode_responses=True, socket_timeout=5)
            _redis_client.ping()
            logger.info("[DLOCK] Redis conectado para locks distribuídos")
        except Exception as exc:
            logger.warning("[DLOCK] Falha ao conectar Redis (%s) — fallback local", exc)
            _redis_client = None
        _redis_init_done = True
        return _redis_client


# ── Fallback: pool de threading.Lock por nome ──
_local_locks: dict[str, threading.Lock] = {}
_local_locks_guard = threading.Lock()


def _get_local_lock(name: str) -> threading.Lock:
    with _local_locks_guard:
        lk = _local_locks.get(name)
        if lk is None:
            lk = threading.Lock()
            _local_locks[name] = lk
        return lk


class DistributedLock:
    """
    Lock distribuído Redis com fallback local.

    Args:
        name: Nome único do recurso (ex: "engine:lead:12345")
        ttl_ms: Tempo máximo que o lock fica ativo (milissegundos). Auto-expire.
        prefix: Prefixo no Redis (namespace)
    """

    def __init__(
        self,
        name: str,
        *,
        ttl_ms: int = 90_000,
        prefix: str = "meumisterio:lock:",
    ):
        self.name = name
        self.key = f"{prefix}{name}"
        self.ttl_ms = max(1000, min(ttl_ms, 600_000))
        self._token = str(uuid.uuid4())
        self._acquired = False
        self._local_lock: Optional[threading.Lock] = None

    def acquire(self, timeout: float = 8.0) -> bool:
        """
        Tenta adquirir o lock. Retorna True se conseguiu.

        Args:
            timeout: Segundos máximos para esperar (0 = non-blocking)
        """
        r = _get_redis()

        if r is None:
            # Fallback local
            self._local_lock = _get_local_lock(self.name)
            self._acquired = self._local_lock.acquire(timeout=max(0.001, timeout))
            return self._acquired

        # Redis: polling com backoff
        deadline = time.monotonic() + timeout
        attempt = 0
        while True:
            try:
                # SET NX PX: atômico, com TTL
                result = r.set(self.key, self._token, nx=True, px=self.ttl_ms)
                if result:
                    self._acquired = True
                    return True
            except Exception as exc:
                logger.warning("[DLOCK] Redis SET falhou (%s) — tentando fallback", exc)
                # Fallback para local em caso de falha Redis
                self._local_lock = _get_local_lock(self.name)
                self._acquired = self._local_lock.acquire(timeout=max(0.001, timeout))
                return self._acquired

            if time.monotonic() >= deadline:
                return False

            # Backoff exponencial com jitter
            attempt += 1
            sleep_s = min(0.5, 0.05 * (2 ** min(attempt, 5)))
            time.sleep(sleep_s)

    def release(self) -> bool:
        """Libera o lock. Retorna True se liberou com sucesso."""
        if not self._acquired:
            return False

        if self._local_lock is not None:
            try:
                self._local_lock.release()
            except RuntimeError:
                pass
            self._acquired = False
            self._local_lock = None
            return True

        r = _get_redis()
        if r is None:
            self._acquired = False
            return True

        # Lua script: só deleta se o token bater (evita liberar lock de outro worker)
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = r.eval(lua_script, 1, self.key, self._token)
            self._acquired = False
            return bool(result)
        except Exception as exc:
            logger.warning("[DLOCK] Redis DEL falhou: %s", exc)
            self._acquired = False
            return False

    def extend(self, extra_ms: int = 30_000) -> bool:
        """Estende o TTL do lock (útil para operações longas)."""
        if not self._acquired:
            return False
        r = _get_redis()
        if r is None:
            return True  # local lock não tem TTL

        lua_extend = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("pexpire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        try:
            result = r.eval(lua_extend, 1, self.key, self._token, str(extra_ms))
            return bool(result)
        except Exception:
            return False

    def __enter__(self):
        self.acquire()
        return self._acquired

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False

    @property
    def is_held(self) -> bool:
        return self._acquired


class DistributedSemaphore:
    """
    Semáforo distribuído via Redis (contador atômico).
    Equivalente ao threading.BoundedSemaphore mas multi-worker.

    Uso:
        sem = DistributedSemaphore("engine:processing", max_concurrent=24)
        acquired = sem.acquire(timeout=8)
        if acquired:
            try:
                ...
            finally:
                sem.release()
    """

    def __init__(
        self,
        name: str,
        *,
        max_concurrent: int = 24,
        prefix: str = "meumisterio:sem:",
    ):
        self.name = name
        self.key = f"{prefix}{name}"
        self.max_concurrent = max(1, max_concurrent)
        self._acquired = False
        self._local_sem: Optional[threading.BoundedSemaphore] = None

    def acquire(self, timeout: float = 8.0) -> bool:
        r = _get_redis()

        if r is None:
            # Fallback local
            if self._local_sem is None:
                self._local_sem = threading.BoundedSemaphore(value=self.max_concurrent)
            self._acquired = self._local_sem.acquire(timeout=max(0.001, timeout))
            return self._acquired

        deadline = time.monotonic() + timeout
        while True:
            try:
                # INCR atômico + verificação
                current = r.incr(self.key)
                # TTL de segurança (reset automático se travar)
                r.expire(self.key, 300)
                if current <= self.max_concurrent:
                    self._acquired = True
                    return True
                # Passou do limite — decrementar e esperar
                r.decr(self.key)
            except Exception as exc:
                logger.warning("[DSEM] Redis falhou (%s) — fallback local", exc)
                if self._local_sem is None:
                    self._local_sem = threading.BoundedSemaphore(value=self.max_concurrent)
                self._acquired = self._local_sem.acquire(timeout=max(0.001, timeout))
                return self._acquired

            if time.monotonic() >= deadline:
                return False
            time.sleep(0.1)

    def release(self) -> None:
        if not self._acquired:
            return

        if self._local_sem is not None:
            try:
                self._local_sem.release()
            except ValueError:
                pass
            self._acquired = False
            return

        r = _get_redis()
        if r is not None:
            try:
                val = r.decr(self.key)
                if val < 0:
                    r.set(self.key, 0)
            except Exception:
                pass
        self._acquired = False
