"""persist social webhook payload for durable retry

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    inspector = Inspector.from_engine(op.get_bind())
    if "social_webhook_receipts" not in inspector.get_table_names():
        return
    columns = {c["name"].lower() for c in inspector.get_columns("social_webhook_receipts")}
    if "payload_json" not in columns:
        op.add_column(
            "social_webhook_receipts",
            sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )


def downgrade():
    inspector = Inspector.from_engine(op.get_bind())
    if "social_webhook_receipts" in inspector.get_table_names():
        columns = {c["name"].lower() for c in inspector.get_columns("social_webhook_receipts")}
        if "payload_json" in columns:
            op.drop_column("social_webhook_receipts", "payload_json")
