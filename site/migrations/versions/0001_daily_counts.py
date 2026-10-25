"""Aggregate daily counts per recipe (views, scales).

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recipe_daily_counts",
        sa.Column("slug", sa.String(300), primary_key=True),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("kind", sa.String(20), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("recipe_daily_counts")
