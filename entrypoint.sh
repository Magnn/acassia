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

if [ "${USE_GUNICORN:-0}" = "1" ]; then
    echo "🌐 [ENTRYPOINT] Starting gunicorn on port ${PORT} (1 worker, 8 threads)..."
    exec gunicorn app:app --bind "0.0.0.0:${PORT}" --workers 1 --threads 8 --worker-class gthread --timeout 180 --access-logfile - --error-logfile -
else
    echo "🌐 [ENTRYPOINT] Starting Waitress server via python app.py on port ${PORT}..."
    exec python app.py
fi
