"""add sentiment routing urgency columns

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Sentiment Routing: urgência detectada pela IA
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_urgent', sa.Boolean(), nullable=True, server_default='false'))
        batch_op.add_column(sa.Column('urgent_reason', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('urgent_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_lead_is_urgent', ['is_urgent'])


def downgrade():
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.drop_index('ix_lead_is_urgent')
        batch_op.drop_column('urgent_at')
        batch_op.drop_column('urgent_reason')
        batch_op.drop_column('is_urgent')
