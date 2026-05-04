"""
Alembic migration — Sprint 2: Dream Interpreter, Vision Board, Community
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Creates 6 new tables for the spiritual expansion modules.

Revision ID: a1b2c3d4e5f6
Revises: cc44c90edc2e
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = 'a1b2c3d4e5f6'
down_revision = 'cc44c90edc2e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Dream Entries ────────────────────────────────────────────────
    op.create_table(
        'dream_entries',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.String(64), nullable=True, index=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumer_profiles.id'), nullable=True, index=True),
        sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('dream_date', sa.Date(), nullable=True),
        sa.Column('symbols', sa.JSON(), default=list),
        sa.Column('interpretation', sa.Text(), nullable=True),
        sa.Column('emotional_tone', sa.String(32), nullable=True),
        sa.Column('archetype', sa.String(64), nullable=True),
        sa.Column('recurring_themes', sa.JSON(), default=list),
        sa.Column('lucidity_level', sa.Integer(), nullable=True),
        sa.Column('moon_phase', sa.String(32), nullable=True),
        sa.Column('sign', sa.String(32), nullable=True),
        sa.Column('tarot_card_id', sa.Integer(), sa.ForeignKey('tarot_cards.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Vision Board Items ───────────────────────────────────────────
    op.create_table(
        'vision_board_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.String(64), nullable=True, index=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumer_profiles.id'), nullable=True, index=True),
        sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id'), nullable=True),
        sa.Column('category', sa.String(32), nullable=False),
        sa.Column('affirmation', sa.Text(), nullable=False),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('is_manifested', sa.Boolean(), default=False, nullable=False),
        sa.Column('manifested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('manifestation_notes', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Community Groups ─────────────────────────────────────────────
    op.create_table(
        'community_groups',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('tenant_id', sa.String(64), nullable=True, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), nullable=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(32), nullable=False, server_default='general'),
        sa.Column('icon', sa.String(8), nullable=True),
        sa.Column('cover_image_url', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=True, nullable=False),
        sa.Column('oracle_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('oracle_persona', sa.Text(), nullable=True),
        sa.Column('member_count', sa.Integer(), default=0),
        sa.Column('post_count', sa.Integer(), default=0),
        sa.Column('is_archived', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Community Members ────────────────────────────────────────────
    op.create_table(
        'community_members',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('community_groups.id'), nullable=False, index=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumer_profiles.id'), nullable=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('tenant_id', sa.String(64), nullable=True),
        sa.Column('role', sa.String(16), server_default='member'),
        sa.Column('notifications_on', sa.Boolean(), default=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Community Posts ──────────────────────────────────────────────
    op.create_table(
        'community_posts',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('community_groups.id'), nullable=False, index=True),
        sa.Column('author_consumer_id', sa.Integer(), sa.ForeignKey('consumer_profiles.id'), nullable=True),
        sa.Column('author_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('tenant_id', sa.String(64), nullable=True, index=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('post_type', sa.String(16), server_default='post'),
        sa.Column('media_url', sa.Text(), nullable=True),
        sa.Column('media_type', sa.String(16), nullable=True),
        sa.Column('reply_to_id', sa.Integer(), sa.ForeignKey('community_posts.id'), nullable=True),
        sa.Column('reply_count', sa.Integer(), default=0),
        sa.Column('is_oracle_response', sa.Boolean(), default=False),
        sa.Column('oracle_context', sa.JSON(), default=dict),
        sa.Column('reaction_count', sa.Integer(), default=0),
        sa.Column('is_pinned', sa.Boolean(), default=False),
        sa.Column('is_deleted', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── Community Reactions ──────────────────────────────────────────
    op.create_table(
        'community_reactions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('community_posts.id'), nullable=False, index=True),
        sa.Column('consumer_id', sa.Integer(), sa.ForeignKey('consumer_profiles.id'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reaction_type', sa.String(16), server_default='like'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('community_reactions')
    op.drop_table('community_posts')
    op.drop_table('community_members')
    op.drop_table('community_groups')
    op.drop_table('vision_board_items')
    op.drop_table('dream_entries')
