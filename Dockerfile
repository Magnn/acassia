# Dockerfile — Acássia SaaS Platform
# Multi-stage build para produção otimizada
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Stage 1: Dependencies ──
FROM python:3.12-slim AS deps

WORKDIR /app

# System dependencies para psycopg2, Pillow, bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir psycopg2-binary gunicorn gevent

# ── Stage 2: Application ──
FROM python:3.12-slim AS runtime

WORKDIR /app

# Apenas runtime libs (sem compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar pacotes instalados do stage anterior
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copiar aplicação
COPY . .

# Diretórios necessários
RUN mkdir -p downloads scripts/reports media

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production \
    PORT=5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

EXPOSE ${PORT}

# Gunicorn com gevent workers para concorrência real
# Workers = 2 * CPU + 1 (ajustar via WEB_CONCURRENCY)
CMD gunicorn app:app \
    --bind 0.0.0.0:${PORT} \
    --workers ${WEB_CONCURRENCY:-3} \
    --worker-class gevent \
    --worker-connections 1000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
