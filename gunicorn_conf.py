"""
gunicorn_conf.py — Configuração Gunicorn para produção
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monkey-patch do gevent ANTES de qualquer import para garantir
que threading.Lock, time.sleep, socket, etc. sejam compatíveis
com greenlets. Sem isso, threads daemon do Engine (recovery monitor,
inbox manager) podem deadlockar o event loop do gevent.

Uso no Dockerfile:
    gunicorn app:app -c gunicorn_conf.py
"""

import os

# ── Monkey-patch gevent (DEVE ser a primeira coisa) ──────────────────
# Só faz patch se estamos realmente rodando com gevent worker
_worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gevent").strip().lower()
if _worker_class == "gevent":
    try:
        from gevent import monkey
        monkey.patch_all(thread=True, select=True, socket=True)
    except ImportError:
        pass

# ── Gunicorn settings ────────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "3"))
worker_class = _worker_class
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5  # Mantém conexões HTTP keep-alive por 5s (melhor para webhooks frequentes)
max_requests = 1000
max_requests_jitter = 50
preload_app = True  # Carrega app no master antes de fork (salva ~100MB RAM via CoW)
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# ── Pre-fork hook ────────────────────────────────────────────────────
def post_fork(server, worker):
    """
    Chamado após cada worker fork. Útil para:
    - Resetar conexões de pool (SQLAlchemy herda conn do parent process)
    - Log de worker ID
    """
    import logging
    logger = logging.getLogger("gunicorn.worker")
    logger.info(
        "[GUNICORN] Worker %s forked (pid=%s, class=%s)",
        worker.pid, os.getpid(), _worker_class,
    )
    # Força re-criação de conexões no pool (evita shared FDs entre workers)
    try:
        from db.database import engine as db_engine
        db_engine.dispose()
    except Exception:
        pass
