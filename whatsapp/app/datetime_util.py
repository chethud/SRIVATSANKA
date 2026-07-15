"""Normalize datetimes for TIMESTAMP WITHOUT TIME ZONE columns (Postgres/asyncpg)."""

from __future__ import annotations

from datetime import datetime, timezone


def as_naive_utc(dt: datetime) -> datetime:
    """Convert aware datetimes to naive UTC; leave naive values unchanged."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)
