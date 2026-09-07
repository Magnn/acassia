"""notas fiscais

Revision ID: e6f7g8h9i0j1
Revises: d5e6f7g8h9i0
Create Date: 2026-05-05

"""
from alembic import op
import sqlalchemy as sa

revision = 'e6f7g8h9i0j1'
down_revision = 'd5e6f7g8h9i0'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'notas_fiscais',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('ambiente', sa.String(length=20), nullable=True),
        sa.Column('tipo_documento', sa.String(length=10), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=True),
        sa.Column('serie', sa.String(length=10), nullable=True),
        sa.Column('chave_acesso', sa.String(length=44), nullable=True),
        sa.Column('valor_total', sa.Float(), nullable=False),
        sa.Column('cpf_cnpj', sa.String(length=20), nullable=True),
        sa.Column('nome_cliente', sa.String(length=150), nullable=True),
        sa.Column('descricao_servico', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('api_reference_id', sa.String(length=100), nullable=True),
        sa.Column('mensagem_sefaz', sa.Text(), nullable=True),
        sa.Column('url_pdf', sa.String(length=500), nullable=True),
        sa.Column('url_xml', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notas_fiscais_id'), 'notas_fiscais', ['id'], unique=False)
    op.create_index(op.f('ix_notas_fiscais_tenant_id'), 'notas_fiscais', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_notas_fiscais_lead_id'), 'notas_fiscais', ['lead_id'], unique=False)
    op.create_index('ix_nf_tenant_status', 'notas_fiscais', ['tenant_id', 'status'], unique=False)

def downgrade():
    op.drop_index('ix_nf_tenant_status', table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_lead_id'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_tenant_id'), table_name='notas_fiscais')
    op.drop_index(op.f('ix_notas_fiscais_id'), table_name='notas_fiscais')
    op.drop_table('notas_fiscais')
