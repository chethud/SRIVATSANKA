"""Dynamic event-year / month / day lists for WhatsApp (no hardcoded year)."""

from __future__ import annotations

from calendar import month_name, monthrange
from datetime import date, datetime
from zoneinfo import ZoneInfo

EVENT_YEAR_HORIZON = 10  # current year through current+10 inclusive → 11 years
YEAR_PAGE_SIZE = 8
MONTH_PAGE_1 = tuple(range(1, 10))  # Jan–Sep + More
DAY_PAGE_SIZE = 10
IST = ZoneInfo("Asia/Kolkata")


def today_ist() -> date:
    return datetime.now(IST).date()


def available_years(*, offset: int = 0) -> list[int]:
    start = today_ist().year + max(0, offset)
    end = today_ist().year + EVENT_YEAR_HORIZON
    return list(range(start, end + 1))


def year_list_rows(*, offset: int = 0) -> list[tuple[str, str, str]]:
    years = available_years(offset=offset)
    page = years[:YEAR_PAGE_SIZE]
    rows = [(f"event_year_{y}", str(y), "") for y in page]
    if len(years) > YEAR_PAGE_SIZE:
        rows.append(("event_year_more", "More Years", ""))
    return rows


def month_list_rows(*, page: int = 0) -> list[tuple[str, str, str]]:
    if page <= 0:
        rows = [(f"cal_month_{m:02d}", month_name[m], "") for m in MONTH_PAGE_1]
        rows.append(("cal_month_more", "More Months", ""))
        return rows
    return [(f"cal_month_{m:02d}", month_name[m], "") for m in range(10, 13)]


def days_in_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def day_list_rows(*, year: int, month: int, page: int = 0) -> list[tuple[str, str, str]]:
    last = days_in_month(year, month)
    start = page * DAY_PAGE_SIZE + 1
    end = min(start + DAY_PAGE_SIZE - 1, last)
    rows = [(f"event_day_{d}", str(d), "") for d in range(start, end + 1)]
    if end < last:
        rows.append(("event_day_more", "More Dates", ""))
    return rows


def format_event_date(year: int, month: int, day: int) -> str:
    return f"{day} {month_name[month]} {year}"


def iso_event_date(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_year_id(button_id: str) -> int | None:
    if not (button_id or "").startswith("event_year_"):
        return None
    tail = button_id.split("event_year_", 1)[-1]
    if tail in {"more", "back"}:
        return None
    try:
        year = int(tail)
    except ValueError:
        return None
    current = today_ist().year
    if current <= year <= current + EVENT_YEAR_HORIZON:
        return year
    return None


def parse_month_id(button_id: str) -> int | None:
    bid = button_id or ""
    if bid.startswith("cal_month_") and bid != "cal_month_more":
        try:
            month = int(bid.split("_")[-1])
        except ValueError:
            return None
        if 1 <= month <= 12:
            return month
    # Legacy month_YYYY_MM
    if bid.startswith("month_") and bid != "month_other":
        parts = bid.split("_")
        if len(parts) == 3:
            try:
                month = int(parts[2])
            except ValueError:
                return None
            if 1 <= month <= 12:
                return month
    return None


def parse_day_id(button_id: str) -> int | None:
    if not (button_id or "").startswith("event_day_"):
        tail = button_id
    else:
        tail = button_id.split("event_day_", 1)[-1]
    if tail in {"more", "back"}:
        return None
    try:
        day = int(tail)
    except ValueError:
        return None
    if 1 <= day <= 31:
        return day
    return None


def valid_calendar_day(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
        return True
    except ValueError:
        return False
