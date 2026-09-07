# Dockerfile — Acássia SaaS Platform
# Multi-stage build para produção otimizada
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Stage 1: Frontend Build ──
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Dependencies ──
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
RUN pip install --no-cache-dir -r requirements.txt

# ── Stage 3: Application ──
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
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Diretórios necessários
RUN mkdir -p downloads scripts/reports media \
    && chmod +x entrypoint.sh

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_ENV=production

# Expose portas comuns de deploy (Railway/Render)
EXPOSE 5000 8080

# Entrypoint: migrations + server
CMD ["./entrypoint.sh"]
