import logging

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Enquiry, EnquiryDish, EnquiryStatus, Notification, NotificationType
from app.schemas import EnquiryFields, SelectedDishItem
from app.services.app_settings import get_owner_phone
from app.services.event_date import parse_event_date
from app.services.location_normalize import normalize_location
from app.services.callback_time import format_callback_display, parse_callback_time
from app.services.whatsapp_client import normalize_phone, send_whatsapp_message
import re

logger = logging.getLogger(__name__)


def guest_count_for_db(value: int | str | None) -> int:
    """Map conversational guest values (including ranges) to a DB integer."""
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, value)
    nums = [int(n) for n in re.findall(r"\d+", str(value))]
    if len(nums) >= 2:
        return max(nums[0], nums[1])
    if nums:
        return nums[0]
    return 0


def _callback_text_from_notes(notes: str | None) -> str | None:
    if not notes:
        return None
    prefix = "Callback requested: "
    for line in notes.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip() or None
    return None


async def save_enquiry(
    db: AsyncSession,
    fields: EnquiryFields,
    whatsapp_id: str,
    dishes: list[SelectedDishItem] | None = None,
) -> Enquiry:
    phone = normalize_phone(fields.phone_number or whatsapp_id)
    dish_lines = []
    if dishes:
        for d in dishes:
            custom = ", ".join(d.customizations) if d.customizations else "None"
            dish_lines.append(f"{d.dish_name} ({d.category}) – {custom}")

    callback_at = parse_callback_time(fields.preferred_callback or "in 2 hours")
    event_date_raw = (fields.event_date or "").strip()
    event_date_parsed = parse_event_date(event_date_raw)
    note_lines: list[str] = []
    if event_date_raw:
        note_lines.append(f"Occasion date requested: {event_date_raw}")
    if fields.guest_count is not None:
        note_lines.append(f"Guest count requested: {fields.guest_count}")
    if fields.preferred_callback:
        note_lines.append(f"Callback requested: {fields.preferred_callback}")
        note_lines.append(f"Callback scheduled: {format_callback_display(callback_at, fields.preferred_callback)}")
    if fields.notes:
        note_lines.append(fields.notes)
    if dishes:
        note_lines.append("Cuisine preferences via WhatsApp")

    enquiry = Enquiry(
        customerName=fields.customer_name or "Unknown",
        phoneNumber=phone,
        eventType=fields.event_type or "General",
        eventDate=event_date_parsed,
        eventLocation=normalize_location(fields.event_location or "TBD"),
        guestCount=guest_count_for_db(fields.guest_count),
        preferredCallbackAt=callback_at,
        status=EnquiryStatus.NEW,
        notes="\n".join(note_lines) if note_lines else None,
    )
    db.add(enquiry)
    await db.flush()

    for item in dishes or []:
        db.add(
            EnquiryDish(
                enquiryId=enquiry.id,
                dishId=item.dish_id,
                dishName=item.dish_name,
                category=item.category,
                customizations=", ".join(item.customizations) if item.customizations else None,
                notes=item.notes,
            )
        )

    notification = Notification(
        type=NotificationType.NEW_ENQUIRY,
        title="New Enquiry",
        message=f"{enquiry.customerName} – {enquiry.eventType} on {fields.event_date}",
        enquiryId=enquiry.id,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(enquiry)

    logger.info("Enquiry saved: %s (%s) with %d dishes", enquiry.id, enquiry.customerName, len(dishes or []))
    await notify_owner_new_enquiry(db, enquiry, dishes)
    return enquiry


def _format_dishes_for_whatsapp(dishes: list[SelectedDishItem] | None) -> str:
    if not dishes:
        return "Cuisine: To be discussed on callback"
    lines = ["*Cuisine / menu style:*"]
    for d in dishes:
        lines.append(f"• {d.dish_name}")
    return "\n".join(lines)


async def notify_owner_new_enquiry(
    db: AsyncSession,
    enquiry: Enquiry,
    dishes: list[SelectedDishItem] | None = None,
) -> None:
    owner = await get_owner_phone(db)
    if not owner:
        logger.warning("OWNER_PHONE_NUMBER not set – skipping owner alert")
        return

    menu_section = _format_dishes_for_whatsapp(dishes)
    callback_original = _callback_text_from_notes(enquiry.notes)
    guest_label = str(enquiry.guestCount)
    if enquiry.notes:
        for line in enquiry.notes.splitlines():
            if line.startswith("Guest count requested: "):
                guest_label = line.split(": ", 1)[1].strip() or guest_label
                break
    message = (
        "🔔 *New Enquiry!*\n\n"
        f"Name: {enquiry.customerName}\n"
        f"Phone: {enquiry.phoneNumber}\n"
        f"Event: {enquiry.eventType}\n"
        f"Date: {enquiry.eventDate.strftime('%d %b %Y')}\n"
        f"Location: {enquiry.eventLocation}\n"
        f"Guests: {guest_label}\n"
        f"Callback: {format_callback_display(enquiry.preferredCallbackAt, callback_original)}\n\n"
        f"{menu_section}\n\n"
        "Please contact the customer at the preferred callback time."
    )
    sent, _err = await send_whatsapp_message(owner, message)
    if sent:
        logger.info("Owner notified via WhatsApp: %s", owner)
    else:
        logger.error("Failed to send owner WhatsApp alert to %s", owner)


async def notify_owner_callback_reminder(db: AsyncSession, enquiry: Enquiry) -> None:
    owner = await get_owner_phone(db)
    if not owner:
        return

    message = (
        "⏰ *Callback Reminder*\n\n"
        f"Call *{enquiry.customerName}* now (in ~15 minutes).\n\n"
        f"Phone: {enquiry.phoneNumber}\n"
        f"Event: {enquiry.eventType}\n"
        f"Date: {enquiry.eventDate.strftime('%d %b %Y')}\n"
        f"Location: {enquiry.eventLocation}\n"
        f"Guests: {enquiry.guestCount}"
    )
    sent, _err = await send_whatsapp_message(owner, message)
    if sent:
        logger.info("Callback reminder sent to owner for enquiry %s", enquiry.id)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def mark_enquiry_seen_for_phone(db: AsyncSession, phone: str) -> None:
    """When the owner replies manually, mark the latest NEW enquiry as SEEN."""
    phone = normalize_phone(phone)
    if not phone:
        return

    result = await db.execute(
        select(Enquiry)
        .where(Enquiry.phoneNumber == phone)
        .order_by(desc(Enquiry.createdAt))
        .limit(1)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry or enquiry.status != EnquiryStatus.NEW:
        return

    enquiry.status = EnquiryStatus.SEEN
    enquiry.ownerViewedAt = _utcnow()
    await db.commit()
    logger.info("Enquiry %s marked SEEN after owner reply to %s", enquiry.id, phone)
