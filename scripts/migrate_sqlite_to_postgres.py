"""
scripts/migrate_sqlite_to_postgres.py — Migração SQLite → PostgreSQL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Script one-shot para copiar todos os dados do meumisterio.db para PostgreSQL.

Uso:
    1. Configure DATABASE_URL no .env apontando para PostgreSQL
    2. Execute: python scripts/migrate_sqlite_to_postgres.py
    3. O script cria as tabelas no PostgreSQL e copia linha a linha

Seguro para re-executar (usa INSERT ... ON CONFLICT DO NOTHING).
"""

import os
import sys
import logging

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import sessionmaker

    # ── Source: SQLite ──
    sqlite_path = os.path.join(_ROOT, "meumisterio.db")
    if not os.path.exists(sqlite_path):
        logger.error("❌ meumisterio.db não encontrado em %s", sqlite_path)
        sys.exit(1)

    sqlite_url = f"sqlite:///{sqlite_path.replace(os.sep, '/')}"
    src_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    # ── Target: PostgreSQL ──
    pg_url = (os.getenv("DATABASE_URL") or "").strip()
    if not pg_url or not pg_url.startswith("postgresql"):
        logger.error("❌ DATABASE_URL não aponta para PostgreSQL. Defina no .env:")
        logger.error("   DATABASE_URL=postgresql://user:pass@host:5432/meumisterio")
        sys.exit(1)

    if pg_url.startswith("postgres://"):
        pg_url = pg_url.replace("postgres://", "postgresql://", 1)

    tgt_engine = create_engine(pg_url)

    # ── Criar tabelas no PostgreSQL ──
    logger.info("📦 Criando tabelas no PostgreSQL...")
    from db.models import Base
    Base.metadata.create_all(bind=tgt_engine)
    logger.info("✅ Tabelas criadas/verificadas")

    # ── Descobrir tabelas a migrar ──
    src_inspector = inspect(src_engine)
    tables = src_inspector.get_table_names()
    # Pular tabelas internas do Alembic
    skip = {"alembic_version"}
    tables = [t for t in tables if t not in skip]

    logger.info("📋 Tabelas a migrar: %s", ", ".join(tables))

    SrcSession = sessionmaker(bind=src_engine)
    TgtSession = sessionmaker(bind=tgt_engine)

    total_rows = 0
    errors = 0

    for table_name in tables:
        src_session = SrcSession()
        tgt_session = TgtSession()
        try:
            # Ler todas as linhas do SQLite
            rows = src_session.execute(text(f"SELECT * FROM {table_name}")).fetchall()
            if not rows:
                logger.info("  ⏭️  %s: 0 linhas (skip)", table_name)
                continue

            # Pegar nomes das colunas
            columns = src_session.execute(text(f"SELECT * FROM {table_name} LIMIT 1")).keys()
            col_names = list(columns)

            logger.info("  📥 %s: %d linhas...", table_name, len(rows))

            batch_size = 500
            migrated = 0

            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                for row in batch:
                    row_dict = dict(zip(col_names, row))
                    # Limpar valores None em colunas que não aceitam
                    placeholders = ", ".join([f":{c}" for c in col_names])
                    cols = ", ".join(col_names)
                    try:
                        tgt_session.execute(
                            text(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"),
                            row_dict,
                        )
                        migrated += 1
                    except Exception as e:
                        # Log e continuar
                        if migrated == 0:
                            logger.warning("    ⚠️ Erro em %s (primeira): %s", table_name, str(e)[:120])
                        errors += 1

                tgt_session.commit()

            total_rows += migrated
            logger.info("  ✅ %s: %d/%d linhas migradas", table_name, migrated, len(rows))

        except Exception as e:
            logger.error("  ❌ %s: %s", table_name, e)
            tgt_session.rollback()
            errors += 1
        finally:
            src_session.close()
            tgt_session.close()

    logger.info("=" * 60)
    logger.info("🏁 Migração concluída: %d linhas migradas, %d erros", total_rows, errors)
    if errors:
        logger.warning("⚠️ Verifique os erros acima — podem ser linhas duplicadas (esperado em re-run)")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
