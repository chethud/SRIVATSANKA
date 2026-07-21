"""Dashboard AI — answers predefined quick questions with live DB data."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Enquiry, EnquiryStatus, Expense, Notification, Vendor, Worker

# Must stay in sync with website/src/utils/aiAssistantRules.tsx
PREDEFINED_RULE_QUERIES: dict[str, str] = {
    "upcoming": "Show all upcoming events",
    "wedding": "Show wedding enquiries",
    "birthday": "Show birthday enquiries",
    "corporate": "Show corporate enquiries",
    "guests-200": "Show enquiries above 200 guests",
    "recent": "Show recent enquiries",
    "summary": "Business summary",
}


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%d %b %Y")


def _fmt_datetime(dt: datetime) -> str:
    return dt.strftime("%d %b %Y, %I:%M %p")


def _status_label(enquiry: Enquiry) -> str:
    return enquiry.status.value if hasattr(enquiry.status, "value") else str(enquiry.status)


def _guest_label(enquiry: Enquiry) -> str:
    if enquiry.guestCount and enquiry.guestCount > 0:
        return str(enquiry.guestCount)
    return "Set on order (session pax)"


def _format_enquiry_list(enquiries: list[Enquiry], title: str, empty_hint: str = "") -> str:
    if not enquiries:
        hint = f"\n\n{empty_hint}" if empty_hint else ""
        return f"No results for: **{title}**.{hint}"

    lines = [f"**{title}** ({len(enquiries)})\n"]
    for i, e in enumerate(enquiries, 1):
        lines.append(
            f"{i}. **{e.customerName}** – {e.eventType}\n"
            f"   Event: {_fmt_date(e.eventDate)} | {e.eventLocation}\n"
            f"   Guests: {_guest_label(e)} | Phone: {e.phoneNumber}\n"
            f"   Callback: {_fmt_datetime(e.preferredCallbackAt)} | Status: {_status_label(e)}"
        )
    return "\n\n".join(lines)


async def _upcoming_enquiries(db: AsyncSession) -> list[Enquiry]:
    now = datetime.now()
    result = await db.execute(
        select(Enquiry)
        .where(Enquiry.eventDate >= now)
        .order_by(Enquiry.eventDate.asc())
        .limit(20)
    )
    return list(result.scalars().all())


async def _all_enquiries(db: AsyncSession, limit: int = 20) -> list[Enquiry]:
    result = await db.execute(select(Enquiry).order_by(Enquiry.createdAt.desc()).limit(limit))
    return list(result.scalars().all())


async def _enquiries_by_event_type(db: AsyncSession, keyword: str) -> list[Enquiry]:
    result = await db.execute(
        select(Enquiry)
        .where(func.lower(Enquiry.eventType).contains(keyword.lower()))
        .order_by(Enquiry.eventDate.asc())
        .limit(20)
    )
    return list(result.scalars().all())


async def _enquiries_above_guests(db: AsyncSession, min_guests: int) -> list[Enquiry]:
    result = await db.execute(
        select(Enquiry)
        .where(Enquiry.guestCount >= min_guests)
        .order_by(Enquiry.guestCount.desc())
        .limit(20)
    )
    return list(result.scalars().all())


async def _enquiry_stats(db: AsyncSession) -> str:
    total = await db.scalar(select(func.count()).select_from(Enquiry)) or 0
    new = await db.scalar(
        select(func.count())
        .select_from(Enquiry)
        .where(Enquiry.status == EnquiryStatus.NEW, Enquiry.ownerViewedAt.is_(None))
    ) or 0
    converted = await db.scalar(
        select(func.count()).select_from(Enquiry).where(Enquiry.status == EnquiryStatus.CONVERTED)
    ) or 0
    upcoming = await db.scalar(
        select(func.count()).select_from(Enquiry).where(Enquiry.eventDate >= datetime.now())
    ) or 0
    unread = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.read.is_(False))
    ) or 0
    vendors = await db.scalar(select(func.count()).select_from(Vendor)) or 0
    workers = await db.scalar(select(func.count()).select_from(Worker)) or 0
    expenses = await db.scalar(select(func.count()).select_from(Expense)) or 0
    expense_total = await db.scalar(select(func.coalesce(func.sum(Expense.amount), 0))) or 0

    return (
        "**Business Summary**\n\n"
        f"• Total enquiries: {total}\n"
        f"• New (unviewed): {new}\n"
        f"• Converted orders: {converted}\n"
        f"• Upcoming events: {upcoming}\n"
        f"• Unread notifications: {unread}\n"
        f"• Vendors: {vendors}\n"
        f"• Workers: {workers}\n"
        f"• Expense records: {expenses}"
        + (f" (₹{float(expense_total):,.0f})" if expenses else "")
    )


def _resolve_rule_id(rule_id: str | None, query: str) -> str | None:
    if rule_id and rule_id in PREDEFINED_RULE_QUERIES:
        return rule_id

    normalized = " ".join(query.lower().strip().split())
    for rid, canonical in PREDEFINED_RULE_QUERIES.items():
        if normalized == canonical.lower():
            return rid

    # Fuzzy fallbacks for free-typed variants of the same questions
    if any(k in normalized for k in ("upcoming", "future event", "next event", "scheduled")):
        return "upcoming"
    if "wedding" in normalized:
        return "wedding"
    if "birthday" in normalized:
        return "birthday"
    if "corporate" in normalized:
        return "corporate"
    if "guest" in normalized and re.search(r"(?:above|over|more than|>\s*)\s*200\b", normalized):
        return "guests-200"
    if any(k in normalized for k in ("recent enquir", "new enquir", "latest enquir", "all enquir")):
        return "recent"
    if any(k in normalized for k in ("summary", "stats", "overview", "how many", "total", "business")):
        return "summary"
    return None


async def _answer_rule(rule_id: str, db: AsyncSession) -> str:
    if rule_id == "upcoming":
        events = await _upcoming_enquiries(db)
        return _format_enquiry_list(
            events,
            "Upcoming Events",
            empty_hint="There are no events with a future date yet.",
        )

    if rule_id == "wedding":
        items = await _enquiries_by_event_type(db, "wedding")
        return _format_enquiry_list(items, "Wedding Enquiries")

    if rule_id == "birthday":
        items = await _enquiries_by_event_type(db, "birthday")
        return _format_enquiry_list(items, "Birthday Enquiries")

    if rule_id == "corporate":
        items = await _enquiries_by_event_type(db, "corporate")
        return _format_enquiry_list(items, "Corporate Enquiries")

    if rule_id == "guests-200":
        items = await _enquiries_above_guests(db, 200)
        return _format_enquiry_list(
            items,
            "Enquiries with 200+ Guests",
            empty_hint=(
                "No enquiries currently store 200+ guests on the enquiry record. "
                "Session pax is often set later on the order menu."
            ),
        )

    if rule_id == "recent":
        items = await _all_enquiries(db)
        return _format_enquiry_list(items, "Recent Enquiries")

    if rule_id == "summary":
        return await _enquiry_stats(db)

    return (
        "I can answer these questions:\n\n"
        + "\n".join(f"• {q}" for q in PREDEFINED_RULE_QUERIES.values())
    )


async def answer_dashboard_query(
    query: str,
    db: AsyncSession,
    rule_id: str | None = None,
) -> str:
    resolved = _resolve_rule_id(rule_id, query)
    if resolved:
        return await _answer_rule(resolved, db)

    return (
        "Please choose one of the quick questions below, or ask:\n\n"
        + "\n".join(f"• {q}" for q in PREDEFINED_RULE_QUERIES.values())
    )
