"""Payments table

Revision ID: 0003_payments
Revises: 0002_user_limits
Create Date: 2025-08-23 00:30:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_payments"
down_revision = "0002_user_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),  # extra | pin | unlimited
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),  # pending|approved|rejected
        sa.Column("file_type", sa.String(16), nullable=True),  # photo|document
        sa.Column("file_id", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_id", sa.Integer, nullable=True),
    )
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_user", "payments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_user", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_table("payments")
