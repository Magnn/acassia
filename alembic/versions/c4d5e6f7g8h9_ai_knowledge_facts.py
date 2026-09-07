"""ai_knowledge_facts table

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7g8h9"
down_revision = "b3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_knowledge_facts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, server_default="geral"),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_ai_kb_tenant_active",
        "ai_knowledge_facts",
        ["tenant_id", "active"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_kb_tenant_active", table_name="ai_knowledge_facts")
    op.drop_table("ai_knowledge_facts")
