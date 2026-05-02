import logging
import sys
from sqlalchemy import text
from db.database import engine, Base

logger = logging.getLogger(__name__)

def _ensure_mensagens_media_url_column():
    """Migração leve para bancos existentes: garante `mensagens.media_url`."""
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(mensagens)")).fetchall()
            names = {str(c[1]).lower() for c in cols if len(c) > 1}
            if "media_url" not in names:
                conn.execute(text("ALTER TABLE mensagens ADD COLUMN media_url TEXT"))
                logger.info("🧩 [DATABASE] Coluna mensagens.media_url adicionada.")
    except Exception as e:
        logger.warning(f"⚠️ [DATABASE] Não foi possível garantir media_url: {e}")

def _ensure_leads_tenant_id_column():
    """Migração leve: garante `leads.tenant_id` em bases antigas."""
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
            names = {str(c[1]).lower() for c in cols if len(c) > 1}
            if "tenant_id" not in names:
                conn.execute(text("ALTER TABLE leads ADD COLUMN tenant_id VARCHAR(64) NOT NULL DEFAULT 'default'"))
                logger.info("🧩 [DATABASE] Coluna leads.tenant_id adicionada.")
    except Exception as e:
        logger.warning(f"⚠️ [DATABASE] Não foi possível garantir tenant_id em leads: {e}")

def _ensure_leads_metadata_version_column():
    """Merge otimista em metadata_json (motor vs fila de envio)."""
    try:
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(leads)")).fetchall()
            names = {str(c[1]).lower() for c in cols if len(c) > 1}
            if "metadata_version" not in names:
                conn.execute(text("ALTER TABLE leads ADD COLUMN metadata_version INTEGER NOT NULL DEFAULT 0"))
                logger.info("🧩 [DATABASE] Coluna leads.metadata_version adicionada.")
    except Exception as e:
        logger.warning(f"⚠️ [DATABASE] Não foi possível garantir metadata_version em leads: {e}")

def sync_database():
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_leads_tenant_id_column()
        _ensure_mensagens_media_url_column()
        _ensure_leads_metadata_version_column()
        logger.info("✅ [DATABASE] Tabelas sincronizadas com sucesso.")
    except Exception as e:
        logger.critical(f"🚨 [DATABASE] Falha ao sincronizar banco: {e}")
        sys.exit(1)
