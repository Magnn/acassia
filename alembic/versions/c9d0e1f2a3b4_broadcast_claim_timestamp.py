"""add recoverable broadcast recipient claim timestamp

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    inspector = Inspector.from_engine(op.get_bind())
    if "broadcast_recipients" not in inspector.get_table_names():
        return
    columns = {c["name"].lower() for c in inspector.get_columns("broadcast_recipients")}
    if "claimed_at" not in columns:
        op.add_column("broadcast_recipients", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    inspector = Inspector.from_engine(op.get_bind())
    if "broadcast_recipients" in inspector.get_table_names():
        columns = {c["name"].lower() for c in inspector.get_columns("broadcast_recipients")}
        if "claimed_at" in columns:
            op.drop_column("broadcast_recipients", "claimed_at")
