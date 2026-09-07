"""
scripts/add_missing_indexes.py — Adiciona indexes faltantes no PostgreSQL.

Idempotente: usa CREATE INDEX IF NOT EXISTS.
Executar após cada migração ou deploy:
    python scripts/add_missing_indexes.py

Os indexes também foram adicionados nos models.py (index=True),
então novos deploys os criarão automaticamente via db.sync.
"""

from dotenv import load_dotenv
load_dotenv()

import logging
from db.database import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

INDEXES = [
    # tenant_id indexes (11 tabelas)
    "CREATE INDEX IF NOT EXISTS ix_community_members_tenant_id ON community_members (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_member_area_assets_tenant_id ON member_area_assets (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_ritual_logs_tenant_id ON ritual_logs (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_tarot_decks_tenant_id ON tarot_decks (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_billing_tenant_id ON tenant_billing (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_feature_flags_tenant_id ON tenant_feature_flags (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_health_tenant_id ON tenant_health (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_quota_warnings_tenant_id ON tenant_quota_warnings (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_tenant_usage_counters_tenant_id ON tenant_usage_counters (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_trail_enrollments_tenant_id ON trail_enrollments (tenant_id)",
    "CREATE INDEX IF NOT EXISTS ix_user_badges_tenant_id ON user_badges (tenant_id)",
    # lead_id indexes (6 tabelas)
    "CREATE INDEX IF NOT EXISTS ix_dream_entries_lead_id ON dream_entries (lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_expert_schedule_slots_lead_id ON expert_schedule_slots (lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_group_link_visits_lead_id ON group_link_visits (lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_natal_charts_lead_id ON lead_natal_charts (lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_lead_numerology_lead_id ON lead_numerology (lead_id)",
    "CREATE INDEX IF NOT EXISTS ix_vision_board_items_lead_id ON vision_board_items (lead_id)",
    # status/created_at indexes (tabelas criticas)
    "CREATE INDEX IF NOT EXISTS ix_broadcast_campaigns_status ON broadcast_campaigns (status)",
    "CREATE INDEX IF NOT EXISTS ix_broadcast_campaigns_created_at ON broadcast_campaigns (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_flow_runs_status ON flow_runs (status)",
    "CREATE INDEX IF NOT EXISTS ix_content_assets_status ON content_assets (status)",
    "CREATE INDEX IF NOT EXISTS ix_content_assets_created_at ON content_assets (created_at)",
    # evento column for audit filtering
    "CREATE INDEX IF NOT EXISTS ix_eventos_audit_evento ON eventos_audit (evento)",
]


def main():
    created = 0
    with engine.begin() as conn:
        for sql in INDEXES:
            name = sql.split("IF NOT EXISTS ")[-1].split(" ON")[0]
            try:
                conn.execute(text(sql))
                logger.info("OK: %s", name)
                created += 1
            except Exception as exc:
                logger.warning("SKIP: %s -- %s", name, exc)
    logger.info("Done: %d/%d indexes processed", created, len(INDEXES))


if __name__ == "__main__":
    main()
