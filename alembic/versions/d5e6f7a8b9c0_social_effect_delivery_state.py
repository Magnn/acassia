"""track social webhook effects independently

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("social_webhook_receipts") as batch:
        batch.add_column(sa.Column("public_reply_sent", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("private_reply_sent", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("last_error", sa.String(500), nullable=True))


def downgrade():
    with op.batch_alter_table("social_webhook_receipts") as batch:
        batch.drop_column("last_error")
        batch.drop_column("private_reply_sent")
        batch.drop_column("public_reply_sent")
