"""
Fila durável opcional para payloads do webhook WhatsApp (Meta at-least-once).

Com REDIS_URL definido: LPUSH → worker BRPOP → mesma `_triagem_meta(data)` de sempre.
Sem Redis ou falha de conexão: app.py usa thread in-process (comportamento anterior).

Não substitui a fila por lead (LeadInboxManager); apenas torna **persistente** o passo
webhook → triagem após responder 200 OK à Meta.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

QUEUE_KEY = os.getenv("REDIS_INBOUND_QUEUE_KEY", "meumisterio:wa:inbound").strip() or "meumisterio:wa:inbound"

_redis_client: Any = None
_redis_unavailable: bool = False
_consumer_started = False
_consumer_lock = threading.Lock()


def _client():
    """Cliente Redis singleton; None se desabilitado ou indisponível."""
    global _redis_client, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis_client is not None:
        return _redis_client
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis  # noqa: WPS433 — opcional

        # TLS remoto (Upstash rediss://) precisa de mais tempo para handshake;
        # local (redis://) pode usar timeout menor sem problema.
        _is_tls = url.startswith("rediss://")
        _sock_connect_timeout = float(os.getenv("REDIS_SOCKET_TIMEOUT", "10" if _is_tls else "5") or 10)
        # socket_timeout precisa ser maior que brpop_timeout para o BRPOP não expirar o socket
        # antes de o Redis responder com "nada na fila" ao fim do block period.
        _brpop_timeout = int(os.getenv("REDIS_BRPOP_TIMEOUT", "10") or 10)
        _sock_read_timeout = _brpop_timeout + 5

        r = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=_sock_connect_timeout,
            socket_timeout=_sock_read_timeout,
            retry_on_timeout=True,
        )
        r.ping()
        _redis_client = r
        logger.info("📮 [REDIS] Conectado%s (fila inbound: %s).", " [TLS]" if _is_tls else "", QUEUE_KEY)
        return _redis_client
    except Exception as e:
        _redis_unavailable = True
        logger.warning("⚠️ [REDIS] Indisponível — usando apenas thread in-process: %s", e)
        return None


def redis_inbound_ready() -> bool:
    """True se REDIS_URL está set e ping OK."""
    if not (os.getenv("REDIS_URL") or "").strip():
        return False
    return _client() is not None


def enqueue_inbound_webhook(data: dict) -> bool:
    """
    Enfileira o JSON bruto do webhook. Retorna True se gravou no Redis.
    """
    r = _client()
    if not r:
        return False
    try:
        payload = json.dumps(data, ensure_ascii=False)
        r.lpush(QUEUE_KEY, payload)
        return True
    except Exception as e:
        logger.warning("⚠️ [REDIS] LPUSH falhou — fallback in-process: %s", e)
        return False


def start_consumer_if_configured(handler: Callable[[dict], Any]) -> None:
    """
    Inicia thread daemon que consome BRPOP e chama `handler(data)`.
    Idempotente (uma vez por processo).
    """
    global _consumer_started
    if not (os.getenv("REDIS_URL") or "").strip():
        return
    if _client() is None:
        return
    with _consumer_lock:
        if _consumer_started:
            return
        _consumer_started = True

    def _loop():
        brpop_timeout = int(os.getenv("REDIS_BRPOP_TIMEOUT", "10") or 10)
        logger.info("📮 [REDIS] Worker inbound iniciado (BRPOP timeout=%ss).", brpop_timeout)
        while True:
            try:
                r = _client()
                if not r:
                    time.sleep(5.0)
                    continue
                out = r.brpop(QUEUE_KEY, timeout=brpop_timeout)
                if not out:
                    continue
                raw = out[1]
                data = json.loads(raw)
                if not isinstance(data, dict):
                    logger.warning("⚠️ [REDIS] Payload inválido (não-dict), ignorado.")
                    continue
                handler(data)
            except json.JSONDecodeError as e:
                logger.error("🚨 [REDIS] JSON inválido na fila: %s", e)
            except Exception as e:
                logger.error("🚨 [REDIS] Erro no worker inbound: %s", e, exc_info=True)
                # Reconexão: descarta cliente em cache para forçar novo ping na próxima iteração
                global _redis_client, _redis_unavailable
                _redis_client = None
                _redis_unavailable = False
                time.sleep(3.0)

    threading.Thread(target=_loop, daemon=True, name="RedisWAInbound").start()


def queue_depth() -> Optional[int]:
    """LLEN da fila (None se Redis off)."""
    r = _client()
    if not r:
        return None
    try:
        return int(r.llen(QUEUE_KEY))
    except Exception:
        return None
