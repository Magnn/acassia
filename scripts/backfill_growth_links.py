"""
scripts/backfill_growth_links.py — Migração offline de links de crescimento legados
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Varre a tabela tenant_flow_variables pela chave "growth.links" e converte
todos os links armazenados como blob JSON para a tabela dedicada growth_links.
"""
import logging
from db.database import SessionLocal
from db import models
from api.saas.growth_links import _migrate_legacy_links

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_growth_links")


def backfill_all():
    db = SessionLocal()
    try:
        rows = db.query(models.TenantFlowVariable).filter_by(key="growth.links").all()
        total = len(rows)
        logger.info(f"Encontrados {total} registros de links legados para migrar.")
        for r in rows:
            tenant_id = r.tenant_id
            _migrate_legacy_links(db, tenant_id)
            logger.info(f"Migrado tenant: {tenant_id}")
        logger.info("Migração offline de growth links concluída com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    backfill_all()
