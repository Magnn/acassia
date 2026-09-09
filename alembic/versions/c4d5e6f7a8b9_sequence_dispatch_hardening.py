"""add enrollment_id, idempotency_key, attempt, message_id to sequence_dispatches

Revision ID: c4d55e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = 'c4d5e6f7a8b9'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'sequence_dispatches' in tables:
        columns = [col['name'] for col in inspector.get_columns('sequence_dispatches')]
        if 'enrollment_id' not in columns:
            op.add_column('sequence_dispatches', sa.Column('enrollment_id', sa.Integer(), nullable=True))
            op.create_index('ix_sequence_dispatches_enrollment_id', 'sequence_dispatches', ['enrollment_id'])
        if 'idempotency_key' not in columns:
            op.add_column('sequence_dispatches', sa.Column('idempotency_key', sa.String(128), nullable=True))
            op.create_index('ix_sequence_dispatches_idempotency_key', 'sequence_dispatches', ['idempotency_key'], unique=True)
        if 'attempt' not in columns:
            op.add_column('sequence_dispatches', sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'))
        if 'run_at' not in columns:
            op.add_column('sequence_dispatches', sa.Column('run_at', sa.DateTime(timezone=True), nullable=True))
        if 'provider_message_id' not in columns:
            op.add_column('sequence_dispatches', sa.Column('provider_message_id', sa.String(128), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'sequence_dispatches' in tables:
        columns = [col['name'] for col in inspector.get_columns('sequence_dispatches')]
        if 'idempotency_key' in columns:
            op.drop_index('ix_sequence_dispatches_idempotency_key', 'sequence_dispatches')
            op.drop_column('sequence_dispatches', 'idempotency_key')
        if 'enrollment_id' in columns:
            op.drop_index('ix_sequence_dispatches_enrollment_id', 'sequence_dispatches')
            op.drop_column('sequence_dispatches', 'enrollment_id')
        if 'provider_message_id' in columns:
            op.drop_column('sequence_dispatches', 'provider_message_id')
        if 'run_at' in columns:
            op.drop_column('sequence_dispatches', 'run_at')
        if 'attempt' in columns:
            op.drop_column('sequence_dispatches', 'attempt')
