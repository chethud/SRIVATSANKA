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


def _start_of_day(when: datetime) -> datetime:
    """Normalize to noon local (stable calendar-day marker for events)."""
    return when.replace(hour=12, minute=0, second=0, microsecond=0)


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


def is_urgent_event_date(text: str, now: datetime | None = None) -> bool:
    """True when the occasion is today, tomorrow, or within the next 7 days."""
    raw = (text or "").strip().lower()
    if not raw or "to be discussed" in raw:
        return False

    # Clearly farther-out windows are never urgent
    if any(
        w in raw
        for w in (
            "next month",
            "next year",
            "in a month",
            "after a month",
            "coming month",
        )
    ):
        return False

    if any(
        w in raw
        for w in (
            "today",
            "tonight",
            "tomorrow",
            "tmrw",
            "tmr",
            "day after tomorrow",
            "this week",
            "same week",
            "coming week",
        )
    ):
        return True

    # Only treat concrete calendar dates as urgent (avoid +7-day parse fallback)
    concrete = bool(
        re.search(
            r"\b(?:\d{1,2}\s*(?:st|nd|rd|th)?\s+"
            r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
            r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
            r"|\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
            r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}"
            r"|\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b"
            r"|\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b"
            r"|\b\d{1,2}(?:st|nd|rd|th)?\b)",
            raw,
        )
    )
    if not concrete:
        return False

    reference = now or datetime.now()
    parsed = parse_event_date(text, now=reference)
    delta = (parsed.date() - reference.date()).days
    return 0 <= delta <= 7


def looks_like_event_date(text: str) -> bool:
    """True when the message is a date / month / relative window, not a random digit."""
    t = (text or "").lower().strip()
    if not t:
        return False
    if re.search(
        r"\b(?:the\s+)?(?:\d+(?:st|nd|rd|th)|first|second|third|fourth|1st|2nd|3rd|4th)\s+week\b|"
        r"\b(?:early|mid|late|end of|end\s+of)[\s-]*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|this\s+month|next\s+month)\b|"
        r"\b(?:this|next|coming)\s+(?:week|month|weekend|year)\b|"
        r"\b(?:today|tonight|tomorrow|tmrw|tmr|kal|naale|naley|ivattu|day after)\b",
        t,
    ):
        return True
    if re.search(
        r"\b\d{1,2}[./\-]\d{1,2}(?:[./\-]\d{2,4})?\b|"
        r"\b\d{4}-\d{1,2}-\d{1,2}\b|"
        r"\b\d{1,2}(st|nd|rd|th)\b|"
        r"\b(20\d{2}|19\d{2})\b",
        t,
    ):
        if re.search(r"\bmor\d\b|\bdetai", t) and not re.search(
            r"\b\d{1,2}(st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
            t,
        ):
            if any(w in t for w in ("detail", "info", "know", "tell", "about", "need")):
                return False
        return True
    months = (
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "sept",
        "oct",
        "nov",
        "dec",
    )
    return any(m in t for m in months)


def parse_event_date(text: str, now: datetime | None = None) -> datetime:
    """Convert customer occasion date text to a concrete datetime (noon local)."""
    reference = now or datetime.now()
    raw = (text or "").strip()
    if not raw:
        return _start_of_day(reference + timedelta(days=7))

    for fmt in (
        "%d %B %Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d/%m/%y",
        "%d.%m.%Y",
        "%d.%m.%y",
        "%d-%m-%y",
        "%d %m %Y",
        "%d %m %y",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d/%b/%Y",
    ):
        try:
            return datetime.strptime(raw, fmt).replace(hour=12, minute=0, second=0, microsecond=0)
        except ValueError:
            continue

    lower = _strip_ordinals(raw)

    if any(w in lower for w in ("day after tomorrow", "overmorrow", "day after")):
        if "day after" in lower:
            return _start_of_day(reference + timedelta(days=2))
    if any(w in lower for w in ("tomorrow", "tmrw", "tmr", "kal", "naale", "naley")):
        return _start_of_day(reference + timedelta(days=1))
    if any(w in lower for w in ("today", "tonight", "ivattu")):
        return _start_of_day(reference)

    match = re.search(r"\b(\d{1,2})\s*(?:of\s+)?this\s+month\b", lower)
    if match:
        return _safe_date(reference.year, reference.month, int(match.group(1)))

    next_month = _parse_next_month_day(lower, reference)
    if next_month is not None:
        return next_month

    match = re.search(r"\b(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?\b", lower)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            year_raw = match.group(3)
            if year_raw:
                year = int(year_raw)
                if year < 100:
                    year += 2000
            else:
                year = reference.year
                if _safe_date(year, month, day) < _start_of_day(reference) - timedelta(days=1):
                    year += 1
            return _safe_date(year, month, day)

    week_words = {
        "first": 1,
        "1st": 1,
        "second": 8,
        "2nd": 8,
        "third": 15,
        "3rd": 15,
        "fourth": 22,
        "4th": 22,
        "last": 22,
    }
    match = re.search(
        r"\b(first|second|third|fourth|last|1st|2nd|3rd|4th|\d+(?:st|nd|rd|th))\s+week(?:\s+of)?\s+"
        r"(next month|this month|january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        lower,
    )
    if match:
        week_key = match.group(1)
        day = week_words.get(week_key, 15)
        if week_key[0].isdigit():
            n = int(re.sub(r"\D", "", week_key) or "3")
            day = {1: 1, 2: 8, 3: 15, 4: 22}.get(n, 15)
        when = match.group(2)
        if when == "next month":
            year, month = _next_calendar_month(reference)
        elif when == "this month":
            year, month = reference.year, reference.month
        else:
            month = MONTHS[when]
            year = reference.year
            if _safe_date(year, month, day) < _start_of_day(reference) - timedelta(days=1):
                year += 1
        return _safe_date(year, month, day)

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

    match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        lower,
    )
    if match:
        month = MONTHS[match.group(1)]
        year = reference.year
        if month < reference.month or (month == reference.month and reference.day > 20):
            year += 1
        return _safe_date(year, month, 15)

    if "coming month" in lower or "next month" in lower:
        year, month = _next_calendar_month(reference)
        return _safe_date(year, month, 15)

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
