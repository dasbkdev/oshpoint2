"""Add channel refs and sold flag to ad_publishes

Revision ID: 0004_adpublish_refs
Revises: 0003_payments
Create Date: 2025-08-23 01:10:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_adpublish_refs"
down_revision = "0003_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ad_publishes") as batch:
        batch.add_column(sa.Column("channel_id", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("message_ids_json", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("is_sold", sa.Boolean(), nullable=False, server_default=sa.text("0")))


def downgrade() -> None:
    with op.batch_alter_table("ad_publishes") as batch:
        batch.drop_column("is_sold")
        batch.drop_column("message_ids_json")
        batch.drop_column("channel_id")
