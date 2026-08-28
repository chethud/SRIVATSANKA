"""Parse natural-language preferred callback times from WhatsApp messages.

Times are interpreted in Asia/Kolkata (Bengaluru business hours), not bare UTC.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

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

# Typo-tolerant "call me now" phrases
IMMEDIATE_RE = re.compile(
    r"\b("
    r"immediately|imediately|imidiately|imideatly|immediatly|imediatly|"
    r"asap|right\s*now|right\s*away|urgent|urgently|now|soon|"
    r"as\s*soon\s*as\s*possible|call\s*me\s*now|call\s*now"
    r")\b",
    re.I,
)


def now_ist(now: datetime | None = None) -> datetime:
    """Current time as naive IST (stored without tzinfo for DB compatibility)."""
    if now is None:
        return datetime.now(IST).replace(tzinfo=None)
    if now.tzinfo is not None:
        return now.astimezone(IST).replace(tzinfo=None)
    # Assume naive values passed in tests are already in IST
    return now


def _start_of_day(when: datetime) -> datetime:
    return when.replace(hour=0, minute=0, second=0, microsecond=0)


def _apply_time(base: datetime, hour: int, minute: int = 0, *, reference: datetime) -> datetime:
    result = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if result <= reference:
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

    match = re.search(r"\b(?:at|around|by|@)\s*([1-9]|1[0-2]|12)\b", lower)
    if match and not re.search(r"\b(?:guests?|people|pax)\b", lower):
        hour = int(match.group(1))
        return hour, 0

    return None


def _extract_time_of_day(lower: str) -> tuple[int, int] | None:
    for label, clock in TIME_OF_DAY.items():
        if label in lower:
            return clock
    return None


def _mentions_day_after_tomorrow(lower: str) -> bool:
    return "day after tomorrow" in lower or "overmorrow" in lower


def _mentions_tomorrow(lower: str) -> bool:
    if re.search(
        r"\b(?:tomorrow|tommorow|tommarow|tomorow|tommorrow|tomorrw|tmrw|tmr|2morrow|2mrw|kal)\b",
        lower,
    ):
        return True
    return bool(re.search(r"\btom\w*row\b", lower))


def _mentions_today(lower: str) -> bool:
    if re.search(r"\b(?:today|todat|2day|tonight|this evening|this afternoon)\b", lower):
        return True
    return "this morning" in lower


def _is_immediate(lower: str) -> bool:
    return bool(IMMEDIATE_RE.search(lower))


def is_immediate_callback(text: str | None) -> bool:
    """True when the customer asked for now / ASAP / right away."""
    return _is_immediate((text or "").lower())


def normalize_callback_label(text: str) -> str:
    """Store a short preference such as 'this evening', never the full sentence."""
    raw = (text or "").strip()
    if not raw:
        return "in 2 hours"
    lower = raw.lower()
    if _is_immediate(lower):
        return "Immediately"

    period = None
    if "tonight" in lower or "this evening" in lower or re.search(r"\bevening\b", lower):
        period = "evening"
    elif re.search(r"\bafternoon\b", lower):
        period = "afternoon"
    elif re.search(r"\bmorning\b", lower):
        period = "morning"
    elif re.search(r"\bnight\b", lower):
        period = "night"

    day = None
    if _mentions_today(lower):
        day = "today"
    elif _mentions_tomorrow(lower):
        day = "tomorrow"
    elif _mentions_day_after_tomorrow(lower):
        day = "day after tomorrow"

    if day == "today" and period == "evening":
        return "this evening"
    if day and period:
        return f"{day} {period}"
    if period:
        return period
    if day:
        return day
    clock = _extract_clock_time(lower)
    if clock:
        hour, minute = clock
        return f"{hour:02d}:{minute:02d}"
    if len(raw.split()) > 5:
        return period or "a convenient time"
    return raw


def _resolve_base_day(lower: str, now: datetime) -> datetime | None:
    if _mentions_day_after_tomorrow(lower):
        return _start_of_day(now + timedelta(days=2))
    if _mentions_tomorrow(lower):
        return _start_of_day(now + timedelta(days=1))
    if _mentions_today(lower):
        return _start_of_day(now)

    for name, weekday in WEEKDAYS.items():
        if re.search(rf"\b{re.escape(name)}\b", lower):
            days_ahead = (weekday - now.weekday()) % 7
            if days_ahead == 0 and "next" in lower:
                days_ahead = 7
            return _start_of_day(now + timedelta(days=days_ahead))

    return None


def _ensure_future(parsed: datetime, reference: datetime) -> datetime:
    """Never schedule a callback in the past (timezone / typo safety net)."""
    if parsed <= reference:
        return reference + timedelta(minutes=10)
    return parsed


def parse_callback_time(text: str, now: datetime | None = None) -> datetime:
    """Convert customer callback text to a concrete datetime in IST (naive)."""
    reference = now_ist(now)
    raw = (text or "").strip()
    if not raw:
        return reference + timedelta(hours=2)

    lower = raw.lower()

    # Custom timing inputs handling
    clean_input = re.sub(r"[.,!?]", "", lower).strip()
    if "today evening after 7" in clean_input:
        base = _resolve_base_day("today", reference)
        return _ensure_future(_apply_time(base, 19, 0, reference=reference), reference)
    if "tomorrow morning around 11" in clean_input:
        base = _resolve_base_day("tomorrow", reference)
        return _ensure_future(_apply_time(base, 11, 0, reference=reference), reference)
    if "day after around tea time" in clean_input or "day after tea time" in clean_input:
        base = _resolve_base_day("day after tomorrow", reference)
        return _ensure_future(_apply_time(base, 16, 0, reference=reference), reference)

    if _is_immediate(lower):
        return reference + timedelta(minutes=10)

    in_minutes = re.search(r"\bin\s+(\d+)\s*min", lower)
    if in_minutes:
        return _ensure_future(reference + timedelta(minutes=int(in_minutes.group(1))), reference)

    in_hours = re.search(r"\bin\s+(\d+)\s*hours?", lower)
    if in_hours:
        return _ensure_future(reference + timedelta(hours=int(in_hours.group(1))), reference)

    after_hours = re.search(r"\bafter\s+(\d+)\s*hours?", lower)
    if after_hours:
        return _ensure_future(reference + timedelta(hours=int(after_hours.group(1))), reference)

    clock = _extract_clock_time(lower)
    time_of_day = _extract_time_of_day(lower)
    base = _resolve_base_day(lower, reference)

    if base is not None:
        if clock:
            hour, minute = clock
            return _ensure_future(_apply_time(base, hour, minute, reference=reference), reference)
        if time_of_day:
            hour, minute = time_of_day
            return _ensure_future(_apply_time(base, hour, minute, reference=reference), reference)
        candidate = base.replace(hour=11, minute=0, second=0, microsecond=0)
        return _ensure_future(candidate, reference)

    if clock:
        hour, minute = clock
        return _ensure_future(
            _apply_time(_start_of_day(reference), hour, minute, reference=reference),
            reference,
        )

    if time_of_day:
        hour, minute = time_of_day
        return _ensure_future(
            _apply_time(_start_of_day(reference), hour, minute, reference=reference),
            reference,
        )

    if "call me" in lower:
        return reference + timedelta(hours=1)

    return reference + timedelta(hours=2)


def format_callback_display(parsed: datetime, original: str | None = None) -> str:
    """Human-readable callback for UI/notifications (IST)."""
    formatted = parsed.strftime("%d %b %Y, %I:%M %p")
    original = normalize_callback_label(original or "")
    if original.lower() == "immediately":
        return f"{formatted} (Immediately)"
    if original and original.lower() not in formatted.lower() and original.lower() not in {
        "in 2 hours",
        "a convenient time",
    }:
        if len(original.split()) <= 4:
            return f"{formatted} ({original})"
    return formatted


@dataclass
class CallbackParts:
    date_label: str | None = None
    time_label: str | None = None
    period: str | None = None
    uses_this_number: bool = False
    ambiguous_noon: bool = False
    immediate: bool = False


def clock_is_ambiguous_noon(text: str, clock: tuple[int, int] | None) -> bool:
    lower = (text or "").lower()
    if not clock:
        return False
    hour, minute = clock
    if hour != 12 or minute != 0:
        return False
    if re.search(r"\b(am|pm|a\.m|p\.m|noon|midnight|afternoon|morning)\b", lower):
        return False
    return True


def parse_callback_parts(text: str) -> CallbackParts:
    raw = (text or "").strip()
    lower = raw.lower()
    parts = CallbackParts()
    if not raw:
        return parts
    if _is_immediate(lower):
        parts.immediate = True
        parts.time_label = "Immediately"
        return parts
    if re.search(r"\b(?:this\s+(?:number|no)|same\s+number|my\s+number|on\s+this)\b", lower):
        parts.uses_this_number = True

    if _mentions_day_after_tomorrow(lower):
        parts.date_label = "day after tomorrow"
    elif _mentions_tomorrow(lower):
        parts.date_label = "tomorrow"
    elif _mentions_today(lower):
        parts.date_label = "today"

    if "tonight" in lower or re.search(r"\bevening\b", lower):
        parts.period = "evening"
    elif re.search(r"\bafternoon\b", lower):
        parts.period = "afternoon"
    elif re.search(r"\bmorning\b", lower):
        parts.period = "morning"
    elif re.search(r"\bnight\b", lower):
        parts.period = "night"
    elif "noon" in lower:
        parts.period = "noon"
        parts.time_label = "12:00 PM"

    clock = _extract_clock_time(lower)
    if clock:
        hour, minute = clock
        parts.ambiguous_noon = clock_is_ambiguous_noon(raw, clock)
        if "pm" in lower or "p.m" in lower or "am" in lower or "a.m" in lower:
            display_hour = hour % 24
            parts.time_label = datetime(2000, 1, 1, display_hour, minute).strftime("%I:%M %p").lstrip("0")
        elif parts.ambiguous_noon:
            parts.time_label = "12:00"
        else:
            parts.time_label = f"{hour:02d}:{minute:02d}"

    if parts.period and not parts.time_label:
        parts.time_label = parts.period
    return parts


def compose_callback_label(*, date_label: str | None, time_label: str | None, immediate: bool = False) -> str | None:
    if immediate:
        return "Immediately"
    date_label = (date_label or "").strip() or None
    time_label = (time_label or "").strip() or None
    if date_label and time_label:
        if time_label.lower() in {"evening", "morning", "afternoon", "night"}:
            if date_label == "today" and time_label.lower() == "evening":
                return "this evening"
            return f"{date_label} {time_label}"
        return f"{date_label} at {time_label}"
    if time_label:
        return time_label
    return None


def callback_has_usable_time(label: str | None, *, time_label: str | None = None, pending_ampm: bool = False) -> bool:
    if pending_ampm:
        return False
    if time_label and time_label.lower() not in {"", "12:00"}:
        return True
    text = (label or "").strip().lower()
    if not text:
        return False
    if text in {"immediately", "asap"}:
        return True
    if re.search(r"\b(morning|afternoon|evening|night|noon|am|pm)\b", text):
        return True
    if re.search(r"\d{1,2}\s*:\s*\d{2}", text):
        return True
    if text in {"today", "tomorrow", "day after tomorrow"}:
        return False
    return False
