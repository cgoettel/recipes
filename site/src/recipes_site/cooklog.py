"""The owner's cook log: when each recipe was made, with an optional note.

Doubles as the "tested" marker: a recipe that has never been logged is
untested. Private: only the /me routes read or write it.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select

from recipes_site.db import session_scope
from recipes_site.models import CookLog


@dataclass
class Status:
    count: int
    last: dt.date | None


@dataclass
class Made:
    slug: str
    made_on: dt.date
    note: str | None


def add(slug: str, note: str | None, made_on: dt.date | None = None) -> None:
    note = (note or "").strip()[:500] or None
    with session_scope() as session:
        session.add(
            CookLog(slug=slug, note=note, made_on=made_on or dt.datetime.now(dt.UTC).date())
        )


def status(slug: str) -> Status:
    stmt = select(func.count(CookLog.id), func.max(CookLog.made_on)).where(CookLog.slug == slug)
    with session_scope() as session:
        count, last = session.execute(stmt).one()
    return Status(count=int(count), last=last)


def recent(limit: int = 50) -> list[Made]:
    stmt = select(CookLog).order_by(CookLog.made_on.desc(), CookLog.created_at.desc()).limit(limit)
    with session_scope() as session:
        return [Made(r.slug, r.made_on, r.note) for r in session.scalars(stmt)]


def made_slugs() -> set[str]:
    with session_scope() as session:
        return set(session.scalars(select(CookLog.slug).distinct()))
