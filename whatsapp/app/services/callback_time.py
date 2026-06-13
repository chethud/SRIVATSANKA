"""Parse natural-language preferred callback times from WhatsApp messages."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

TIME_OF_DAY = {
    "morning": (10, 0),
    "afternoon": (14, 0),
    "evening": (18, 0),
    "night": (20, 0),
    "noon": (12, 0),
    "lunch": (13, 0),
    "breakfast": (9, 0),
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


def _start_of_day(when: datetime) -> datetime:
    return when.replace(hour=0, minute=0, second=0, microsecond=0)


def _apply_time(base: datetime, hour: int, minute: int = 0, *, reference: datetime) -> datetime:
    result = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if result < reference and base.date() == reference.date():
        result += timedelta(days=1)
    return result


def _extract_clock_time(lower: str) -> tuple[int, int] | None:
    match = re.search(r"@?\s*(\d{1,2})\s*[:.]\s*(\d{2})\s*(am|pm|a\.m|p\.m)?\b", lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        meridiem = (match.group(3) or "").replace(".", "")
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        elif not meridiem and hour <= 12 and ("pm" in lower or "p.m" in lower) and hour < 12:
            hour += 12
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    match = re.search(r"@?\s*(\d{1,2})\s*(am|pm|a\.m|p\.m)\b", lower)
    if match:
        hour = int(match.group(1))
        meridiem = match.group(2).replace(".", "")
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return hour, 0

    match = re.search(r"\b([01]?\d|2[0-3])\s*:\s*([0-5]\d)\b", lower)
    if match and "am" not in lower and "pm" not in lower:
        return int(match.group(1)), int(match.group(2))

    return None


def _extract_time_of_day(lower: str) -> tuple[int, int] | None:
    for label, clock in TIME_OF_DAY.items():
        if label in lower:
            return clock
    return None


def _resolve_base_day(lower: str, now: datetime) -> datetime | None:
    if "day after tomorrow" in lower:
        return _start_of_day(now + timedelta(days=2))
    if any(w in lower for w in ("tomorrow", "tmrw", "tmr", "kal")):
        return _start_of_day(now + timedelta(days=1))
    if any(w in lower for w in ("today", "tonight", "this evening", "this afternoon")):
        return _start_of_day(now)

    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            days_ahead = (weekday - now.weekday()) % 7
            if days_ahead == 0 and "next" in lower:
                days_ahead = 7
            return _start_of_day(now + timedelta(days=days_ahead))

    return None


def parse_callback_time(text: str, now: datetime | None = None) -> datetime:
    """Convert customer callback text to a concrete datetime (local server time)."""
    reference = now or datetime.now()
    raw = (text or "").strip()
    if not raw:
        return reference + timedelta(hours=2)

    lower = raw.lower()

    in_minutes = re.search(r"\bin\s+(\d+)\s*min", lower)
    if in_minutes:
        return reference + timedelta(minutes=int(in_minutes.group(1)))

    in_hours = re.search(r"\bin\s+(\d+)\s*hours?", lower)
    if in_hours:
        return reference + timedelta(hours=int(in_hours.group(1)))

    after_hours = re.search(r"\bafter\s+(\d+)\s*hours?", lower)
    if after_hours:
        return reference + timedelta(hours=int(after_hours.group(1)))

    clock = _extract_clock_time(lower)
    time_of_day = _extract_time_of_day(lower)
    base = _resolve_base_day(lower, reference)

    if base is not None:
        if clock:
            hour, minute = clock
            return _apply_time(base, hour, minute, reference=reference)
        if time_of_day:
            hour, minute = time_of_day
            return _apply_time(base, hour, minute, reference=reference)
        return base.replace(hour=11, minute=0, second=0, microsecond=0)

    if clock:
        hour, minute = clock
        return _apply_time(_start_of_day(reference), hour, minute, reference=reference)

    if time_of_day:
        hour, minute = time_of_day
        return _apply_time(_start_of_day(reference), hour, minute, reference=reference)

    if any(w in lower for w in ("soon", "asap", "now", "call me")):
        return reference + timedelta(hours=1)

    return reference + timedelta(hours=2)


def format_callback_display(parsed: datetime, original: str | None = None) -> str:
    """Human-readable callback for UI/notifications."""
    formatted = parsed.strftime("%d %b %Y, %I:%M %p")
    original = (original or "").strip()
    if original and original.lower() not in formatted.lower():
        return f"{formatted} ({original})"
    return formatted
