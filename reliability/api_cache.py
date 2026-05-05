"""
reliability/api_cache.py — Cache Redis para APIs analíticas pesadas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Evita full-table-scans repetidos no PostgreSQL para endpoints de
dashboard/KPIs que são polled constantemente.

Uso como decorador:

    @app.route("/api/stats")
    @cached_api(ttl_s=300, key_fn=lambda: f"stats:{get_request_tenant_id()}")
    def api_stats():
        ...

Ou como helper manual:

    cached = get_cached("my:key")
    if cached is not None:
        return jsonify(cached), 200
    result = expensive_query()
    set_cached("my:key", result, ttl_s=300)
"""

from __future__ import annotations

import functools
import json
import logging
import os
import time
from typing import Callable

logger = logging.getLogger(__name__)

_redis_client = None
_redis_init_done = False


def _get_redis():
    """Lazy init — reutiliza o singleton do distributed_lock se possível."""
    global _redis_client, _redis_init_done
    if _redis_init_done:
        return _redis_client
    try:
        from reliability.distributed_lock import _get_redis as _dlock_redis
        _redis_client = _dlock_redis()
    except Exception:
        url = (os.getenv("REDIS_URL") or "").strip()
        if url:
            try:
                import redis
                _redis_client = redis.from_url(url, decode_responses=True, socket_timeout=3)
                _redis_client.ping()
            except Exception:
                _redis_client = None
    _redis_init_done = True
    return _redis_client


_CACHE_PREFIX = "meumisterio:apicache:"


def get_cached(key: str) -> dict | list | None:
    """Retorna dados cacheados ou None."""
    r = _get_redis()
    if not r:
        return None
    try:
        raw = r.get(f"{_CACHE_PREFIX}{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def set_cached(key: str, data, ttl_s: int = 300) -> bool:
    """Grava dados no cache com TTL."""
    r = _get_redis()
    if not r:
        return False
    try:
        raw = json.dumps(data, ensure_ascii=False, default=str)
        r.setex(f"{_CACHE_PREFIX}{key}", ttl_s, raw)
        return True
    except Exception as exc:
        logger.debug("[CACHE] set falhou para %s: %s", key, exc)
        return False


def invalidate(key: str) -> bool:
    """Remove cache de uma key específica."""
    r = _get_redis()
    if not r:
        return False
    try:
        r.delete(f"{_CACHE_PREFIX}{key}")
        return True
    except Exception:
        return False


def invalidate_pattern(pattern: str) -> int:
    """Remove todas as keys que matcham o pattern (ex: 'stats:*')."""
    r = _get_redis()
    if not r:
        return 0
    try:
        full_pattern = f"{_CACHE_PREFIX}{pattern}"
        keys = r.keys(full_pattern)
        if keys:
            return r.delete(*keys)
        return 0
    except Exception:
        return 0


def cached_api(
    ttl_s: int = 300,
    key_fn: Callable[[], str] | None = None,
):
    """
    Decorador para cachear resposta JSON de endpoints Flask.

    Args:
        ttl_s: Tempo de vida do cache em segundos (default: 5 min)
        key_fn: Função que retorna a cache key (deve incluir tenant_id).
                Se None, usa o nome da função + request args.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Construir cache key
            if key_fn:
                try:
                    cache_key = key_fn()
                except Exception:
                    cache_key = fn.__name__
            else:
                from flask import request as _req
                qs = "&".join(sorted(f"{k}={v}" for k, v in _req.args.items()))
                cache_key = f"{fn.__name__}:{qs}" if qs else fn.__name__

            # Check cache
            cached = get_cached(cache_key)
            if cached is not None:
                from flask import jsonify
                logger.debug("[CACHE] HIT %s", cache_key)
                return jsonify(cached), 200

            # Cache MISS — executar função
            t0 = time.time()
            result = fn(*args, **kwargs)
            elapsed_ms = (time.time() - t0) * 1000

            # Extrair dados do response Flask para cachear
            try:
                from flask import Response
                if isinstance(result, tuple):
                    response, status_code = result[0], result[1]
                    if status_code == 200:
                        if isinstance(response, Response):
                            data = json.loads(response.get_data(as_text=True))
                        else:
                            data = response
                        set_cached(cache_key, data, ttl_s)
                        logger.debug(
                            "[CACHE] MISS→SET %s (%.0fms, ttl=%ds)",
                            cache_key, elapsed_ms, ttl_s,
                        )
            except Exception:
                pass

            return result
        return wrapper
    return decorator
