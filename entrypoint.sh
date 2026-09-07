#!/bin/bash
# entrypoint.sh — Startup com migrations + gunicorn
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executa Alembic upgrade antes de iniciar o app.
# Se SKIP_MIGRATIONS=1, pula (útil para CI/debug).
# Se falhar, loga mas não impede o startup (sync_database() faz CREATE IF NOT EXISTS).

echo "🚀 [ENTRYPOINT] Starting Acássia SaaS..."

# ── Migrations ──────────────────────────────────────────────
if [ "${SKIP_MIGRATIONS:-0}" != "1" ] && [ -f "alembic.ini" ]; then
    echo "📦 [ENTRYPOINT] Running Alembic migrations..."
    alembic upgrade head || echo "⚠️ [ENTRYPOINT] Alembic falhou (sync_database() vai compensar) — continuando..."
else
    echo "⏩ [ENTRYPOINT] Skipping migrations (SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-0})"
fi

# ── Indexes + ANALYZE (idempotente, roda a cada boot) ───────
if [ -f "scripts/add_missing_indexes.py" ]; then
    echo "🔧 [ENTRYPOINT] Ensuring PostgreSQL indexes..."
    python scripts/add_missing_indexes.py || true
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

echo "🌐 [ENTRYPOINT] Starting server (1 worker, 8 threads) listening on: ${BINDS}..."
exec gunicorn app:app ${BINDS} --workers 1 --threads 8 --worker-class gthread --timeout 180 --access-logfile - --error-logfile -
