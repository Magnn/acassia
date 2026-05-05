"""add ab_test_exposures table

Revision ID: b3c4d5e6f7g8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3c4d5e6f7g8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ab_test_exposures',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('blueprint_id', sa.Integer(), sa.ForeignKey('flow_blueprints.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('node_id', sa.String(200), nullable=False),
        sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('variant', sa.String(1), nullable=False),
        sa.Column('weight_a', sa.Integer(), server_default='50'),
        sa.Column('weight_b', sa.Integer(), server_default='50'),
        sa.Column('exposed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('converted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('conversion_value', sa.Float(), server_default='0'),
        sa.Column('converted_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('tenant_id', 'blueprint_id', 'node_id', 'lead_id', name='uq_ab_exposure_lead_node'),
    )


def downgrade():
    op.drop_table('ab_test_exposures')
