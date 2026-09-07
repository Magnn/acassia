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

# ── Gunicorn ────────────────────────────────────────────────
PORT="${PORT:-5000}"
echo "🌐 [ENTRYPOINT] Starting gunicorn on port ${PORT} with gthread workers..."
exec gunicorn app:app --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --worker-class gthread --timeout 120
