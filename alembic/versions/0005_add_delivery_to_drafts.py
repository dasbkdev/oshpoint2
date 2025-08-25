"""Add delivery column to ad_drafts

Revision ID: 0005_add_delivery_to_drafts
Revises: 0004_adpublish_refs
Create Date: 2025-08-23 10:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_add_delivery_to_drafts"
down_revision = "0004_adpublish_refs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ad_drafts") as batch:
        batch.add_column(sa.Column("delivery", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("ad_drafts") as batch:
        batch.drop_column("delivery")
