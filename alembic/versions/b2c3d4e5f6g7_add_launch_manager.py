"""add launch manager tables

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'launch_campaigns',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(64), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_jid', sa.String(100), nullable=True),
        sa.Column('product_name', sa.String(200), nullable=True),
        sa.Column('link_vendas', sa.String(500), nullable=True),
        sa.Column('preco_lancamento', sa.String(20), nullable=True),
        sa.Column('preco_normal', sa.String(20), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('variables', sa.JSON(), server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'launch_phases',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('launch_id', sa.Integer(), sa.ForeignKey('launch_campaigns.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('phase_type', sa.String(30), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('group_name_template', sa.String(300), nullable=True),
        sa.Column('message_template', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('sort_order', sa.Integer(), server_default='0'),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('launch_phases')
    op.drop_table('launch_campaigns')
