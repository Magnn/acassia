"""add payment_deliveries outbox table

Revision ID: e5f6a7b8c9d0
Revises: d5e6f7a8b9c0
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = 'e5f6a7b8c9d0'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'payment_deliveries' not in tables:
        op.create_table(
            'payment_deliveries',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('tenant_id', sa.String(64), nullable=False),
            sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id'), nullable=False),
            sa.Column('blueprint_id', sa.Integer(), sa.ForeignKey('flow_blueprints.id'), nullable=True),
            sa.Column('provider', sa.String(32), nullable=False),
            sa.Column('event_id', sa.String(128), nullable=False),
            sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
            sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('payment_metadata', sa.JSON(), nullable=True),
            sa.Column('last_error', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('tenant_id', 'provider', 'event_id', name='uq_payment_delivery_event'),
        )
        op.create_index('ix_payment_deliveries_id', 'payment_deliveries', ['id'])
        op.create_index('ix_payment_deliveries_tenant_id', 'payment_deliveries', ['tenant_id'])
        op.create_index('ix_payment_deliveries_lead_id', 'payment_deliveries', ['lead_id'])
        op.create_index('ix_payment_deliveries_event_id', 'payment_deliveries', ['event_id'])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'payment_deliveries' in tables:
        op.drop_index('ix_payment_deliveries_event_id', 'payment_deliveries')
        op.drop_index('ix_payment_deliveries_lead_id', 'payment_deliveries')
        op.drop_index('ix_payment_deliveries_tenant_id', 'payment_deliveries')
        op.drop_index('ix_payment_deliveries_id', 'payment_deliveries')
        op.drop_table('payment_deliveries')
