import re
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Enquiry, EnquiryStatus, Notification


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%d %b %Y")


def _fmt_datetime(dt: datetime) -> str:
    return dt.strftime("%d %b %Y, %I:%M %p")


def _format_enquiry_list(enquiries: list[Enquiry], title: str) -> str:
    if not enquiries:
        return f"No results for: {title}"

    lines = [f"**{title}** ({len(enquiries)})\n"]
    for i, e in enumerate(enquiries, 1):
        status = e.status.value if hasattr(e.status, "value") else str(e.status)
        lines.append(
            f"{i}. **{e.customerName}** – {e.eventType}\n"
            f"   Event: {_fmt_date(e.eventDate)} | {e.eventLocation}\n"
            f"   Guests: {e.guestCount} | Phone: {e.phoneNumber}\n"
            f"   Callback: {_fmt_datetime(e.preferredCallbackAt)} | Status: {status}"
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
    upcoming = await db.scalar(
        select(func.count()).select_from(Enquiry).where(Enquiry.eventDate >= datetime.now())
    ) or 0
    unread = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.read.is_(False))
    ) or 0

    return (
        "**Business Summary**\n\n"
        f"• Total enquiries: {total}\n"
        f"• New enquiries: {new}\n"
        f"• Upcoming events: {upcoming}\n"
        f"• Unread notifications: {unread}"
    )


async def answer_dashboard_query(query: str, db: AsyncSession) -> str:
    q = query.lower().strip()

    # Upcoming events
    if any(k in q for k in ("upcoming", "future event", "next event", "scheduled")):
        events = await _upcoming_enquiries(db)
        return _format_enquiry_list(events, "Upcoming Events")

    # Wedding / event type filters
    event_keywords = {
        "wedding": "wedding",
        "birthday": "birthday",
        "corporate": "corporate",
        "reception": "reception",
    }
    for label, keyword in event_keywords.items():
        if label in q:
            items = await _enquiries_by_event_type(db, keyword)
            return _format_enquiry_list(items, f"{label.title()} Enquiries")

    # Guest count filter
    guest_match = re.search(r"(?:above|over|more than|>\s*)\s*(\d+)", q)
    if "guest" in q and guest_match:
        min_guests = int(guest_match.group(1))
        items = await _enquiries_above_guests(db, min_guests)
        return _format_enquiry_list(items, f"Enquiries with {min_guests}+ Guests")

    # Order lookup (orders module not yet in DB)
    order_match = re.search(r"ord[-\s]?(\d+)", q, re.I)
    if "order" in q and order_match:
        order_id = f"ORD-{order_match.group(1).zfill(4)}"
        return (
            f"No order found for **{order_id}**.\n\n"
            "Orders are not in the system yet. You can view enquiries instead — "
            "try: *Show all upcoming events* or *Show wedding enquiries*."
        )

    # Expenses
    if "expense" in q or "cost" in q or "spending" in q:
        return (
            "The **Expenses** module is not set up yet.\n\n"
            "You can currently ask about:\n"
            "• Upcoming events\n"
            "• Wedding / birthday / corporate enquiries\n"
            "• Enquiries above a guest count\n"
            "• Business summary"
        )

    # Vendors
    if "vendor" in q or "supplier" in q or "contact details" in q:
        return (
            "The **Vendor Directory** is not set up yet.\n\n"
            "Add vendors from the Vendors page when available. "
            "For now, try: *Show all upcoming events*."
        )

    # Stats / summary
    if any(k in q for k in ("summary", "stats", "overview", "how many", "total")):
        return await _enquiry_stats(db)

    # New / recent enquiries
    if any(k in q for k in ("new enquiry", "recent enquiry", "latest enquiry", "all enquiry")):
        items = await _all_enquiries(db)
        return _format_enquiry_list(items, "Recent Enquiries")

    # Default: show upcoming if any, else help
    upcoming = await _upcoming_enquiries(db)
    if upcoming:
        return (
            _format_enquiry_list(upcoming, "Upcoming Events")
            + "\n\n_Tip: Try \"Show wedding enquiries\" or \"Show enquiries above 200 guests\"._"
        )

    return (
        "I can help you with your events data. Try asking:\n\n"
        "• Show all upcoming events\n"
        "• Show wedding enquiries\n"
        "• Show enquiries above 200 guests\n"
        "• Business summary\n\n"
        "Orders, expenses, and vendors will be available once those modules are added."
    )
