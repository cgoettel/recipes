"""Count recipe views and scales, aggregate only.

Counting is best effort: the site serves recipes from the image, so a database
outage must never break a page. Failures are logged and dropped.
"""

from __future__ import annotations

import datetime as dt

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from recipes_site.db import session_scope
from recipes_site.models import RecipeDailyCount

logger = structlog.get_logger()

KINDS = ("view", "scale")


def bump(slug: str, kind: str, today: dt.date | None = None) -> None:
    if kind not in KINDS:
        raise ValueError(kind)
    day = today or dt.datetime.now(dt.UTC).date()
    stmt = (
        insert(RecipeDailyCount)
        .values(slug=slug, day=day, kind=kind, count=1)
        .on_conflict_do_update(
            index_elements=["slug", "day", "kind"],
            set_={"count": RecipeDailyCount.count + 1},
        )
    )
    try:
        with session_scope() as session:
            session.execute(stmt)
    except SQLAlchemyError as exc:
        logger.warning("counts.bump_failed", slug=slug, kind=kind, error=str(exc))


def top(kind: str, limit: int = 10) -> list[tuple[str, int]]:
    stmt = (
        select(RecipeDailyCount.slug, func.sum(RecipeDailyCount.count).label("total"))
        .where(RecipeDailyCount.kind == kind)
        .group_by(RecipeDailyCount.slug)
        .order_by(func.sum(RecipeDailyCount.count).desc())
        .limit(limit)
    )
    with session_scope() as session:
        return [(row.slug, int(row.total)) for row in session.execute(stmt)]
