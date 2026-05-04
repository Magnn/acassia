"""
api/saas/realtime.py — Server-Sent Events (SSE) para real-time updates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Substitui polling (refetchInterval) por push events.
O frontend conecta em /saas/inbox/stream e recebe atualizações
de novas mensagens, status de leads, e typing indicators.

Pattern: cada tenant tem um canal Redis pub/sub.
O SSE endpoint escuta esse canal e faz streaming para o browser.
Fallback: polling continua funcionando se Redis estiver indisponível.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone

from flask import Blueprint, Response, request, stream_with_context
from flask_login import current_user, login_required

logger = logging.getLogger(__name__)

realtime_bp = Blueprint("saas_realtime", __name__, url_prefix="/saas/inbox")

# ── In-memory event bus (fallback quando Redis não disponível) ──
# Dict[tenant_id → set[queue.Queue]]
_local_channels: dict[str, set[queue.Queue]] = {}
_local_lock = threading.Lock()


def _get_redis():
    """Lazy Redis client."""
    url = (os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis
        return redis.from_url(url, decode_responses=True, socket_timeout=5)
    except Exception:
        return None


def publish_inbox_event(tenant_id: str, event_type: str, payload: dict) -> None:
    """
    Publica evento para todos os clientes SSE conectados a este tenant.

    Chamada pelo webhook/engine quando:
      - Nova mensagem chega (event_type="message_created")
      - Status do lead muda (event_type="lead_updated")
      - Typing indicator (event_type="typing")

    Args:
        tenant_id: ID do tenant
        event_type: Tipo do evento (message_created, lead_updated, typing)
        payload: Dados do evento (ex: {lead_id, message, ...})
    """
    data = {
        "type": event_type,
        "tenant_id": tenant_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    msg = json.dumps(data, ensure_ascii=False, default=str)

    # Tentar Redis pub/sub primeiro
    r = _get_redis()
    if r is not None:
        try:
            channel = f"meumisterio:inbox:{tenant_id}"
            r.publish(channel, msg)
            return
        except Exception as exc:
            logger.warning("[SSE] Redis publish falhou (%s) — fallback local", exc)

    # Fallback: in-memory queues
    with _local_lock:
        subscribers = _local_channels.get(tenant_id, set())
        dead = set()
        for q in subscribers:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.add(q)
        if dead:
            _local_channels[tenant_id] = subscribers - dead


def _subscribe_local(tenant_id: str) -> queue.Queue:
    """Registra subscriber in-memory."""
    q: queue.Queue = queue.Queue(maxsize=100)
    with _local_lock:
        if tenant_id not in _local_channels:
            _local_channels[tenant_id] = set()
        _local_channels[tenant_id].add(q)
    return q


def _unsubscribe_local(tenant_id: str, q: queue.Queue) -> None:
    """Remove subscriber in-memory."""
    with _local_lock:
        subs = _local_channels.get(tenant_id)
        if subs:
            subs.discard(q)
            if not subs:
                del _local_channels[tenant_id]


@realtime_bp.route("/stream", methods=["GET"])
@login_required
def inbox_stream():
    """
    SSE endpoint — real-time updates para a inbox.

    O frontend conecta via EventSource:
        const es = new EventSource('/saas/inbox/stream', { withCredentials: true });
        es.addEventListener('message_created', (e) => { ... });
        es.addEventListener('lead_updated', (e) => { ... });
        es.addEventListener('typing', (e) => { ... });
        es.addEventListener('heartbeat', (e) => { ... });

    Heartbeat a cada 15s para manter a conexão viva (evita timeout de proxies).
    """
    tenant_id = current_user.tenant_id

    def generate():
        # Enviar evento inicial de conexão
        yield _sse_format("connected", {"tenant_id": tenant_id})

        r = _get_redis()

        if r is not None:
            # ── Redis pub/sub mode ──
            try:
                pubsub = r.pubsub()
                channel = f"meumisterio:inbox:{tenant_id}"
                pubsub.subscribe(channel)
                logger.info("[SSE] Cliente conectado via Redis pub/sub — tenant=%s", tenant_id)

                last_heartbeat = time.time()
                while True:
                    # Non-blocking get com timeout
                    msg = pubsub.get_message(timeout=1.0)
                    if msg and msg["type"] == "message":
                        data = msg.get("data", "{}")
                        try:
                            parsed = json.loads(data)
                            event_type = parsed.pop("type", "update")
                            yield _sse_format(event_type, parsed)
                        except (json.JSONDecodeError, TypeError):
                            yield _sse_format("update", {"raw": data})

                    # Heartbeat a cada 15s
                    now = time.time()
                    if now - last_heartbeat >= 15:
                        yield _sse_format("heartbeat", {"ts": int(now)})
                        last_heartbeat = now

            except GeneratorExit:
                logger.info("[SSE] Cliente desconectou — tenant=%s", tenant_id)
                try:
                    pubsub.unsubscribe()
                    pubsub.close()
                except Exception:
                    pass
                return
            except Exception as exc:
                logger.warning("[SSE] Redis pub/sub erro (%s) — caindo", exc)
                return
        else:
            # ── Local queue mode ──
            local_q = _subscribe_local(tenant_id)
            logger.info("[SSE] Cliente conectado via queue local — tenant=%s", tenant_id)
            try:
                last_heartbeat = time.time()
                while True:
                    try:
                        msg = local_q.get(timeout=1.0)
                        try:
                            parsed = json.loads(msg)
                            event_type = parsed.pop("type", "update")
                            yield _sse_format(event_type, parsed)
                        except (json.JSONDecodeError, TypeError):
                            yield _sse_format("update", {"raw": msg})
                    except queue.Empty:
                        pass

                    now = time.time()
                    if now - last_heartbeat >= 15:
                        yield _sse_format("heartbeat", {"ts": int(now)})
                        last_heartbeat = now

            except GeneratorExit:
                logger.info("[SSE] Cliente desconectou — tenant=%s", tenant_id)
                _unsubscribe_local(tenant_id, local_q)
                return

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx: não bufferizar
            "Connection": "keep-alive",
        },
    )


def _sse_format(event_type: str, data: dict) -> str:
    """Formata dados como SSE (Server-Sent Events)."""
    json_str = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {json_str}\n\n"
