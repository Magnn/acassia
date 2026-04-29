"""
Alembic env — integrado com o engine SQLAlchemy do projeto.

- Lê DATABASE_URL via db.database (mesma fonte que a app usa em runtime,
  então dev=SQLite e prod=Postgres ficam transparentes).
- Importa db.models pra autogenerate detectar mudanças nos modelos.

Comandos típicos:
  alembic revision --autogenerate -m "descrição"
  alembic upgrade head
  alembic current
  alembic history
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

# Adiciona raiz do projeto ao path pra `from db.database import ...` funcionar.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Carrega .env antes de tocar em db.database (DATABASE_URL pode vir de lá)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from db.database import engine as app_engine  # type: ignore  # noqa: E402
from db.models import Base  # type: ignore  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Sobrescreve sqlalchemy.url do alembic.ini com a URL real do app.
config.set_main_option("sqlalchemy.url", str(app_engine.url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Modo offline — gera SQL puro sem conectar."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # render_as_batch=True permite ALTER TABLE em SQLite (que não suporta
        # ALTER nativo). Em Postgres é no-op. Habilita migração transparente.
        render_as_batch=True,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo online — reutiliza o engine do app (mesma URL, mesmo dialect)."""
    with app_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
            compare_server_default=True,
            poolclass=pool.NullPool,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
