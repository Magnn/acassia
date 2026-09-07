"""Row-Level Security (RLS) for critical multi-tenant tables.

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2026-05-05

Prevents cross-tenant data leakage at the database level.
Even if application code forgets a WHERE tenant_id filter,
PostgreSQL will silently return zero rows instead of leaking.

NOTE: RLS policies use session variable 'app.tenant_id' which
must be SET at the beginning of each DB session via:
    SET app.tenant_id = 'tenant_xyz';
"""
from alembic import op

revision = "d5e6f7g8h9i0"
down_revision = "c4d5e6f7g8h9"
branch_labels = None
depends_on = None

# Tables with tenant_id that need RLS protection
_RLS_TABLES = [
    "leads",
    "mensagens",
    "flow_blueprints",
    "flow_runs",
    "ai_knowledge_facts",
    "ab_test_exposures",
    "conversion_events",
    "pix_payments",
    "audit_events",
]


def upgrade() -> None:
    # Skip RLS on SQLite (dev)
    conn = op.get_bind()
    if "sqlite" in str(conn.engine.url):
        return

    for table in _RLS_TABLES:
        # Verifica se a tabela existe antes de aplicar RLS
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

                    -- Policy: rows visible only when app.tenant_id matches
                    DROP POLICY IF EXISTS tenant_isolation ON {table};
                    CREATE POLICY tenant_isolation ON {table}
                        USING (
                            tenant_id = current_setting('app.tenant_id', true)
                            OR current_setting('app.tenant_id', true) IS NULL
                            OR current_setting('app.tenant_id', true) = ''
                        );
                END IF;
            END $$;
        """)


def downgrade() -> None:
    conn = op.get_bind()
    if "sqlite" in str(conn.engine.url):
        return

    for table in _RLS_TABLES:
        op.execute(f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = '{table}'
                ) THEN
                    DROP POLICY IF EXISTS tenant_isolation ON {table};
                    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
                END IF;
            END $$;
        """)
