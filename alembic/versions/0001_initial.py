"""Initial schema for oshpoint bot

Revision ID: 0001_initial
Revises: 
Create Date: 2025-08-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.sqlite as sqlite


# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('telegram_id', sa.Integer, nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('lang', sa.String(length=2), nullable=True, server_default='ru'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Ad drafts table
    op.create_table(
        'ad_drafts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('subcategory', sa.String(length=50), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('short_desc', sa.Text, nullable=True),
        sa.Column('condition', sa.String(length=20), nullable=True),
        sa.Column('detail_desc', sa.Text, nullable=True),
        sa.Column('price', sa.Integer, nullable=True),
        sa.Column('city', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')), 
    )
    op.create_index('ix_ad_drafts_user_status', 'ad_drafts', ['user_id', 'status'])

    # Ad photos table
    op.create_table(
        'ad_photos',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('draft_id', sa.Integer, sa.ForeignKey('ad_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_id', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer, nullable=True),
    )

    # Ad publishes
    op.create_table(
        'ad_publishes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('draft_id', sa.Integer, sa.ForeignKey('ad_drafts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')), 
    )
    op.create_index('ix_ad_publishes_user_published_at', 'ad_publishes', ['user_id', 'published_at'])

    # Settings table (singleton)
    op.create_table(
        'settings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('rules_markdown', sa.Text, nullable=True),
        sa.Column('channels_json', sa.JSON, nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')), 
    )


def downgrade() -> None:
    op.drop_table('settings')
    op.drop_index('ix_ad_publishes_user_published_at', table_name='ad_publishes')
    op.drop_table('ad_publishes')
    op.drop_table('ad_photos')
    op.drop_index('ix_ad_drafts_user_status', table_name='ad_drafts')
    op.drop_table('ad_drafts')
    op.drop_table('users')
