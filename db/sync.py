"""
db/sync.py — Sincronização de schema (cross-dialect: SQLite + PostgreSQL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Garante que colunas adicionadas após o schema original existam no DB.
Usa SQLAlchemy inspect() em vez de PRAGMA (SQLite-only).
"""

import logging
import sys
from sqlalchemy import text, inspect as sa_inspect
from db.database import engine, Base, DB_DRIVER

logger = logging.getLogger(__name__)


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Verifica se uma coluna existe na tabela (funciona em SQLite e PostgreSQL)."""
    try:
        columns = inspector.get_columns(table_name)
        return any(c["name"].lower() == column_name.lower() for c in columns)
    except Exception:
        return False


def _table_exists(inspector, table_name: str) -> bool:
    """Verifica se uma tabela existe (cross-dialect)."""
    try:
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def _add_column_if_missing(inspector, table_name: str, column_name: str, column_def: str):
    """
    Adiciona coluna se não existir.
    column_def deve ser compatível com o dialect atual.
    """
    if not _table_exists(inspector, table_name):
        return  # Tabela não existe ainda — create_all vai cuidar
    if _column_exists(inspector, table_name, column_name):
        return  # Já existe

    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}"))
        logger.info("🧩 [DATABASE] Coluna %s.%s adicionada.", table_name, column_name)
    except Exception as e:
        logger.warning("⚠️ [DATABASE] Não foi possível adicionar %s.%s: %s", table_name, column_name, e)


def _ensure_mensagens_media_url_column(inspector):
    """Migração leve para bancos existentes: garante `mensagens.media_url`."""
    _add_column_if_missing(inspector, "mensagens", "media_url", "TEXT")


def _ensure_leads_tenant_id_column(inspector):
    """Migração leve: garante `leads.tenant_id` em bases antigas."""
    _add_column_if_missing(
        inspector, "leads", "tenant_id",
        "VARCHAR(64) NOT NULL DEFAULT 'default'"
    )


def _ensure_leads_metadata_version_column(inspector):
    """Merge otimista em metadata_json (motor vs fila de envio)."""
    _add_column_if_missing(
        inspector, "leads", "metadata_version",
        "INTEGER NOT NULL DEFAULT 0"
    )


def sync_database():
    """
    Sincroniza schema: cria tabelas faltantes e adiciona colunas novas.
    Funciona tanto em SQLite quanto em PostgreSQL.
    """
    try:
        # 1. Cria tabelas que não existem
        Base.metadata.create_all(bind=engine)

        # 2. Inspector cross-dialect para checar colunas
        inspector = sa_inspect(engine)

        # 3. Migrações leves (colunas adicionadas após o schema original)
        _ensure_leads_tenant_id_column(inspector)
        _ensure_mensagens_media_url_column(inspector)
        _ensure_leads_metadata_version_column(inspector)

        logger.info("✅ [DATABASE] Tabelas sincronizadas (%s).", DB_DRIVER)
    except Exception as e:
        logger.critical("🚨 [DATABASE] Falha ao sincronizar banco: %s", e)
        sys.exit(1)
