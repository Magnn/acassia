"""add social_webhook_receipts, growth_links, contact_imports, and missing columns

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'contact_imports' not in tables:
        op.create_table(
            'contact_imports',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.String(64), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('status', sa.String(20), nullable=False, server_default='processing'),
            sa.Column('total_rows', sa.Integer(), server_default='0'),
            sa.Column('processed_rows', sa.Integer(), server_default='0'),
            sa.Column('success_rows', sa.Integer(), server_default='0'),
            sa.Column('failed_rows', sa.Integer(), server_default='0'),
            sa.Column('column_mapping', sa.JSON(), nullable=True),
            sa.Column('assigned_tags', sa.JSON(), nullable=True),
            sa.Column('enrolled_sequence_id', sa.Integer(), nullable=True),
            sa.Column('error_log', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_contact_imports_id', 'contact_imports', ['id'])
        op.create_index('ix_contact_imports_tenant_id', 'contact_imports', ['tenant_id'])

    if 'social_webhook_receipts' not in tables:
        op.create_table(
            'social_webhook_receipts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('tenant_id', sa.String(64), nullable=False),
            sa.Column('provider', sa.String(32), nullable=False),
            sa.Column('event_key', sa.String(128), nullable=False),
            sa.Column('status', sa.String(32), nullable=False, server_default='sent'),
            sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('tenant_id', 'provider', 'event_key', name='uq_social_event_receipt'),
        )
        op.create_index('ix_social_webhook_receipts_tenant_id', 'social_webhook_receipts', ['tenant_id'])

    if 'growth_links' not in tables:
        op.create_table(
            'growth_links',
            sa.Column('id', sa.String(32), nullable=False),
            sa.Column('tenant_id', sa.String(64), nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('phone', sa.String(32), nullable=False),
            sa.Column('message', sa.Text(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=False),
            sa.Column('wa_url', sa.Text(), nullable=False),
            sa.Column('short_url', sa.Text(), nullable=False),
            sa.Column('qr_code', sa.Text(), nullable=True),
            sa.Column('clicks', sa.Integer(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_growth_links_tenant_id', 'growth_links', ['tenant_id'])

    if 'sequences' in tables:
        columns = [col['name'] for col in inspector.get_columns('sequences')]
        if 'trigger_tag' not in columns:
            op.add_column('sequences', sa.Column('trigger_tag', sa.String(100), nullable=True))

    if 'public_api_keys' in tables:
        columns = [col['name'] for col in inspector.get_columns('public_api_keys')]
        if 'scopes' not in columns:
            op.add_column('public_api_keys', sa.Column('scopes', sa.JSON(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = inspector.get_table_names()

    if 'growth_links' in tables:
        op.drop_index('ix_growth_links_tenant_id', 'growth_links')
        op.drop_table('growth_links')

    if 'social_webhook_receipts' in tables:
        op.drop_index('ix_social_webhook_receipts_tenant_id', 'social_webhook_receipts')
        op.drop_table('social_webhook_receipts')

    if 'contact_imports' in tables:
        op.drop_index('ix_contact_imports_tenant_id', 'contact_imports')
        op.drop_index('ix_contact_imports_id', 'contact_imports')
        op.drop_table('contact_imports')

    if 'public_api_keys' in tables:
        columns = [col['name'] for col in inspector.get_columns('public_api_keys')]
        if 'scopes' in columns:
            op.drop_column('public_api_keys', 'scopes')

    if 'sequences' in tables:
        columns = [col['name'] for col in inspector.get_columns('sequences')]
        if 'trigger_tag' in columns:
            op.drop_column('sequences', 'trigger_tag')
