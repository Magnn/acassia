#!/bin/bash
# entrypoint.sh — Startup com migrations + gunicorn
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Executa Alembic upgrade antes de iniciar o app.
# Se SKIP_MIGRATIONS=1, pula (útil para CI/debug).
# Se falhar, loga mas não impede o startup (sync_database() faz CREATE IF NOT EXISTS).

set -e

echo "🚀 [ENTRYPOINT] Starting Acássia SaaS..."

# ── Migrations ──────────────────────────────────────────────
if [ "${SKIP_MIGRATIONS:-0}" != "1" ] && [ -f "alembic.ini" ]; then
    echo "📦 [ENTRYPOINT] Running Alembic migrations..."
    if alembic upgrade head 2>&1; then
        echo "✅ [ENTRYPOINT] Migrations OK"
    else
        echo "⚠️ [ENTRYPOINT] Alembic falhou (sync_database() vai compensar) — continuando..."
    fi
else
    echo "⏩ [ENTRYPOINT] Skipping migrations (SKIP_MIGRATIONS=${SKIP_MIGRATIONS:-0})"
fi

# ── Gunicorn ────────────────────────────────────────────────
echo "🌐 [ENTRYPOINT] Starting gunicorn..."
exec gunicorn app:app -c gunicorn_conf.py
