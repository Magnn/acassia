"""persist contact import payload for worker processing

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    inspector = Inspector.from_engine(op.get_bind())
    if "contact_imports" not in inspector.get_table_names():
        return
    columns = {c["name"].lower() for c in inspector.get_columns("contact_imports")}
    if "payload_json" not in columns:
        op.add_column("contact_imports", sa.Column(
            "payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'"),
        ))


def downgrade():
    inspector = Inspector.from_engine(op.get_bind())
    if "contact_imports" in inspector.get_table_names():
        columns = {c["name"].lower() for c in inspector.get_columns("contact_imports")}
        if "payload_json" in columns:
            op.drop_column("contact_imports", "payload_json")
