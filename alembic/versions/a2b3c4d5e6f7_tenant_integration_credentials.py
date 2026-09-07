"""add tenant_integration_credentials table

Revision ID: a2b3c4d5e6f7
Revises: 549551fd5210
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'a2b3c4d5e6f7'
down_revision = '549551fd5210'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tenant_integration_credentials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('service', sa.String(64), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('encrypted_data', sa.Text(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tenant_integration_credentials_id', 'tenant_integration_credentials', ['id'])
    op.create_index('ix_tenant_integration_credentials_tenant_id', 'tenant_integration_credentials', ['tenant_id'])
    op.create_index('ix_tenant_integration_credentials_service', 'tenant_integration_credentials', ['service'])


def downgrade():
    op.drop_index('ix_tenant_integration_credentials_service', 'tenant_integration_credentials')
    op.drop_index('ix_tenant_integration_credentials_tenant_id', 'tenant_integration_credentials')
    op.drop_index('ix_tenant_integration_credentials_id', 'tenant_integration_credentials')
    op.drop_table('tenant_integration_credentials')
