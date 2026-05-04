"""
gunicorn.conf.py — Configuração de produção para Gunicorn
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Uso: gunicorn -c gunicorn.conf.py app:app

Gevent workers permitem concorrência real (websockets, I/O bound)
sem precisar de async/await no código Flask existente.
"""

import os
import multiprocessing

# ── Workers ──
# CPU-bound: 2 * cores + 1
# I/O-bound (nosso caso): 4 * cores
_cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv("WEB_CONCURRENCY", str(min(4 * _cpu_count, 12))))
worker_class = "gevent"
worker_connections = 1000

# ── Bind ──
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# ── Timeouts ──
timeout = 120          # Webhook Meta pode demorar (Gemini LLM)
graceful_timeout = 30  # Tempo para worker terminar requests em andamento
keepalive = 5

# ── Request Limits ──
max_requests = 1000         # Recicla worker após N requests (previne memory leaks)
max_requests_jitter = 50    # Jitter para não reciclar todos ao mesmo tempo

# ── Logging ──
accesslog = "-"        # stdout
errorlog = "-"         # stderr
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" %(D)sμs'

# ── Security ──
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# ── Hooks ──
def on_starting(server):
    """Log de inicialização."""
    server.log.info(
        "🚀 [GUNICORN] Meu Mistério SaaS — %s workers (%s) na porta %s",
        workers,
        worker_class,
        bind,
    )

def post_fork(server, worker):
    """Após fork: reinicializa conexões DB (evita compartilhar sockets)."""
    server.log.info("👷 [GUNICORN] Worker %s (pid=%s) iniciado", worker.age, worker.pid)

def worker_exit(server, worker):
    """Cleanup ao worker morrer."""
    server.log.info("💀 [GUNICORN] Worker %s (pid=%s) finalizado", worker.age, worker.pid)

# ── Preload ──
# preload_app = True reduz memória (copy-on-write) mas impede hot-reload.
# Em dev, deixe False. Em prod com muitos workers, ative.
preload_app = os.getenv("GUNICORN_PRELOAD", "false").lower() in ("1", "true", "yes")
