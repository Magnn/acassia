"""add broadcast_recipients tracking fields

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'broadcast_recipients' in tables:
        columns = [c['name'].lower() for c in inspector.get_columns('broadcast_recipients')]
        if 'idempotency_key' not in columns:
            op.add_column('broadcast_recipients', sa.Column('idempotency_key', sa.String(128), nullable=True))
            op.create_index('ix_broadcast_recipients_idempotency_key', 'broadcast_recipients', ['idempotency_key'])
        if 'provider_message_id' not in columns:
            op.add_column('broadcast_recipients', sa.Column('provider_message_id', sa.String(128), nullable=True))
        if 'attempt' not in columns:
            op.add_column('broadcast_recipients', sa.Column('attempt', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'broadcast_recipients' in tables:
        columns = [c['name'].lower() for c in inspector.get_columns('broadcast_recipients')]
        if 'idempotency_key' in columns:
            op.drop_index('ix_broadcast_recipients_idempotency_key', 'broadcast_recipients')
            op.drop_column('broadcast_recipients', 'idempotency_key')
        if 'provider_message_id' in columns:
            op.drop_column('broadcast_recipients', 'provider_message_id')
        if 'attempt' in columns:
            op.drop_column('broadcast_recipients', 'attempt')
