"""Parse natural-language occasion dates from WhatsApp replies."""

from __future__ import annotations

import re
from calendar import monthrange
from datetime import datetime, timedelta

MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

WEEKDAYS = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def _safe_date(year: int, month: int, day: int) -> datetime:
    day = min(max(1, day), monthrange(year, month)[1])
    return datetime(year, month, day, 12, 0, 0)


def _strip_ordinals(text: str) -> str:
    return re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text.lower())


def _next_calendar_month(reference: datetime) -> tuple[int, int]:
    month = reference.month + 1
    year = reference.year
    if month > 12:
        month = 1
        year += 1
    return year, month


def _parse_next_month_day(lower: str, reference: datetime) -> datetime | None:
    """Handle '15 next month', 'next month 15', 'next month on 15th'."""
    match = re.search(r"\b(\d{1,2})\s*(?:of\s+)?next\s+month\b", lower)
    if match:
        year, month = _next_calendar_month(reference)
        return _safe_date(year, month, int(match.group(1)))

    match = re.search(r"\bnext\s+month(?:\s+on)?\s+(\d{1,2})\b", lower)
    if match:
        year, month = _next_calendar_month(reference)
        return _safe_date(year, month, int(match.group(1)))

    return None


def parse_event_date(text: str, now: datetime | None = None) -> datetime:
    """Convert customer occasion date text to a concrete datetime (noon local)."""
    reference = now or datetime.now()
    raw = (text or "").strip()
    if not raw:
        return _start_of_day(reference + timedelta(days=7))

    for fmt in ("%d %B %Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%d %b %Y", "%d/%m/%y"):
        try:
            return datetime.strptime(raw, fmt).replace(hour=12, minute=0, second=0, microsecond=0)
        except ValueError:
            continue

    lower = _strip_ordinals(raw)

    if any(w in lower for w in ("day after tomorrow", "overmorrow")):
        return _start_of_day(reference + timedelta(days=2))
    if any(w in lower for w in ("tomorrow", "tmrw", "tmr", "kal")):
        return _start_of_day(reference + timedelta(days=1))
    if any(w in lower for w in ("today", "tonight")):
        return _start_of_day(reference)

    match = re.search(r"\b(\d{1,2})\s*(?:of\s+)?this\s+month\b", lower)
    if match:
        return _safe_date(reference.year, reference.month, int(match.group(1)))

    next_month = _parse_next_month_day(lower, reference)
    if next_month is not None:
        return next_month

    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            days_ahead = (weekday - reference.weekday()) % 7
            if days_ahead == 0 and "next" in lower:
                days_ahead = 7
            if days_ahead == 0 and reference.hour >= 18:
                days_ahead = 7
            return _start_of_day(reference + timedelta(days=days_ahead))

    match = re.search(
        r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)(?:\s+(\d{4}))?\b",
        lower,
    )
    if match:
        day = int(match.group(1))
        month = MONTHS[match.group(2)]
        year = int(match.group(3)) if match.group(3) else reference.year
        if not match.group(3) and _safe_date(year, month, day) < _start_of_day(reference) - timedelta(days=1):
            year += 1
        return _safe_date(year, month, day)

    match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:\s+(\d{4}))?\b",
        lower,
    )
    if match:
        month = MONTHS[match.group(1)]
        day = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else reference.year
        if not match.group(3) and _safe_date(year, month, day) < _start_of_day(reference) - timedelta(days=1):
            year += 1
        return _safe_date(year, month, day)

    match = re.fullmatch(r"(\d{1,2})", lower.strip())
    if match:
        day = int(match.group(1))
        if day >= reference.day:
            return _safe_date(reference.year, reference.month, day)
        month = reference.month + 1
        year = reference.year
        if month > 12:
            month = 1
            year += 1
        return _safe_date(year, month, day)

    return _start_of_day(reference + timedelta(days=7))
