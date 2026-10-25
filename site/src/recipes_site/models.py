"""Database tables. Recipe text never lives here; git is the source of truth."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RecipeDailyCount(Base):
    """Aggregate, cookie-free counts per recipe per day (views, scales).

    No visitor identifiers of any kind: one row per (slug, day, kind).
    """

    __tablename__ = "recipe_daily_counts"

    slug: Mapped[str] = mapped_column(String(300), primary_key=True)
    day: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
