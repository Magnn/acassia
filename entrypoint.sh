#!/bin/bash
# entrypoint.sh — Startup com migrations + gunicorn
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executa Alembic upgrade antes de iniciar o app.
# Se SKIP_MIGRATIONS=1, pula (útil para CI/debug).
# Falha de migração impede o startup: código novo não pode operar em schema antigo.

echo "🚀 [ENTRYPOINT] Starting Acássia SaaS..."

# ── Migrations ──────────────────────────────────────────────
if [ "${SKIP_MIGRATIONS:-0}" != "1" ] && [ -f "alembic.ini" ]; then
    echo "📦 [ENTRYPOINT] Running Alembic migrations..."
    if ! alembic upgrade head; then
        echo "❌ [ENTRYPOINT] Alembic falhou — abortando startup para proteger os dados."
        exit 1
    fi
else
    echo "⏩ [ENTRYPOINT] Skipping migrations (SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-0})"
fi

# ── Indexes + ANALYZE (idempotente, roda a cada boot) ───────
if [ -f "scripts/add_missing_indexes.py" ]; then
    echo "🔧 [ENTRYPOINT] Ensuring PostgreSQL indexes..."
    python scripts/add_missing_indexes.py || true
fi

# ── Seed Super-Admin (idempotente) ──────────────────────────
if [ -f "scripts/seed_admin.py" ]; then
    echo "👑 [ENTRYPOINT] Ensuring Super-Admin user..."
    python scripts/seed_admin.py || true
fi

# ── Server Boot ─────────────────────────────────────────────
PORT="${PORT:-5000}"
export PORT

# Constrói binds para garantir escuta na porta Railway ($PORT) e nas portas 8080/5000
BINDS="-b 0.0.0.0:${PORT}"
if [ "${PORT}" != "8080" ]; then
    BINDS="${BINDS} -b 0.0.0.0:8080"
fi
if [ "${PORT}" != "5000" ]; then
    BINDS="${BINDS} -b 0.0.0.0:5000"
fi

GUNICORN_WORKERS="${GUNICORN_WORKERS:-1}"
GUNICORN_THREADS="${GUNICORN_THREADS:-24}"

echo "🌐 [ENTRYPOINT] Starting server (${GUNICORN_WORKERS} worker(s), ${GUNICORN_THREADS} threads) listening on: ${BINDS}..."
exec gunicorn app:app ${BINDS} --workers "${GUNICORN_WORKERS}" --threads "${GUNICORN_THREADS}" --worker-class gthread --timeout 180 --access-logfile - --error-logfile -
