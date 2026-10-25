"""The owner's private cook log.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cook_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(300), nullable=False),
        sa.Column("made_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_cook_log_slug", "cook_log", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_cook_log_slug", table_name="cook_log")
    op.drop_table("cook_log")
