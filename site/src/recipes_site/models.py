"""Database tables. Recipe text never lives here; git is the source of truth."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import Date, DateTime, Integer, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RecipeDailyCount(Base):
    """Aggregate, cookie-free counts per recipe per day (views, scales, list adds).

    No visitor identifiers of any kind: one row per (slug, day, kind).
    """

    __tablename__ = "recipe_daily_counts"

    slug: Mapped[str] = mapped_column(String(300), primary_key=True)
    day: Mapped[dt.date] = mapped_column(Date, primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class CookLog(Base):
    """The owner's private log: one row each time a recipe was made."""

    __tablename__ = "cook_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    made_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
