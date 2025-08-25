"""User limits table and fix ad_photos column name

Revision ID: 0002_user_limits
Revises: 0001_initial
Create Date: 2025-08-23 00:00:01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_user_limits"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Попытаться переименовать столбец "order" -> sort_order (на SQLite имя могло быть с кавычками)
    try:
        with op.batch_alter_table("ad_photos") as batch_op:
            batch_op.alter_column('"order"', new_column_name="sort_order")
    except Exception:
        try:
            with op.batch_alter_table("ad_photos") as batch_op:
                batch_op.alter_column("order", new_column_name="sort_order")
        except Exception:
            pass  # уже ок

    # Таблица персональных лимитов
    op.create_table(
        "user_limits",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("mode", sa.String(length=16), nullable=False),   # 'unlimited' | 'quota'
        sa.Column("quota_total", sa.Integer, nullable=True),
        sa.Column("quota_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_user_limits_expires", "user_limits", ["expires_at"])

def downgrade() -> None:
    op.drop_index("ix_user_limits_expires", table_name="user_limits")
    op.drop_table("user_limits")
