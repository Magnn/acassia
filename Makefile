# Makefile — Meu Mistério SaaS Operations
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Atalhos para operações comuns de dev e prod.
#
# Uso: make <target>
#   make dev           — Inicia servidor de desenvolvimento
#   make docker-up     — Sobe stack Docker completa
#   make migrate       — Roda migrações Alembic
#   make test          — Executa testes
#   make lint          — Lint com ruff

.PHONY: help dev prod docker-up docker-down docker-logs migrate migrate-auto test lint frontend clean

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Desenvolvimento ──

dev: ## Inicia servidor Flask em modo dev
	python app.py

dev-frontend: ## Inicia frontend React (Vite dev server)
	cd frontend && npm run dev

install: ## Instala dependências Python
	pip install -r requirements.txt

# ── Produção ──

prod: ## Inicia com Gunicorn (produção local)
	gunicorn -c gunicorn.conf.py app:app

# ── Docker ──

docker-up: ## Sobe stack Docker (PostgreSQL + Redis + App)
	docker compose up -d --build

docker-down: ## Para stack Docker
	docker compose down

docker-logs: ## Logs da aplicação
	docker compose logs -f app

docker-rebuild: ## Rebuilda e sobe
	docker compose down && docker compose build --no-cache && docker compose up -d

# ── Database ──

migrate: ## Executa migrações Alembic (upgrade head)
	alembic upgrade head

migrate-auto: ## Gera migração automática baseada nos models
	@read -p "Descrição da migração: " desc; \
	alembic revision --autogenerate -m "$$desc"

migrate-status: ## Mostra estado atual das migrações
	alembic current && alembic history -n 5

db-create: ## Cria tabelas (sem Alembic — desenvolvimento rápido)
	python -c "from db.database import engine, Base; from db.models import *; Base.metadata.create_all(bind=engine)"

db-migrate-pg: ## Migra dados do SQLite para PostgreSQL
	python scripts/migrate_sqlite_to_postgres.py

# ── Testes ──

test: ## Executa testes
	pytest tests/ -v --tb=short

test-cov: ## Testes com cobertura
	pytest tests/ -v --tb=short --cov=. --cov-report=html

# ── Lint ──

lint: ## Lint com ruff
	ruff check . --select=E,F,W --ignore=E501,E402

lint-fix: ## Lint com auto-fix
	ruff check . --select=E,F,W --ignore=E501,E402 --fix

# ── Frontend ──

frontend: ## Build do frontend React
	cd frontend && npm install && npm run build

# ── Limpeza ──

clean: ## Remove arquivos temporários
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov 2>/dev/null || true
