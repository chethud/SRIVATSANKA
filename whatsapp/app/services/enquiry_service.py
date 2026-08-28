import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Enquiry, EnquiryDish, EnquiryStatus, Notification, NotificationType
from app.schemas import EnquiryFields, SelectedDishItem
from app.services.app_settings import get_owner_phone
from app.services.callback_time import (
    _extract_clock_time,
    format_callback_display,
    now_ist,
    parse_callback_time,
)
from app.services.event_date import parse_event_date
from app.services.location_normalize import normalize_location
from app.services.whatsapp_client import (
    normalize_phone,
    send_whatsapp_message_detailed,
)

logger = logging.getLogger(__name__)

RETRY_WAIT_SECONDS = {1: 30, 2: 120, 3: 600}
MAX_NOTIFICATION_ATTEMPTS = 4


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


def format_whatsapp_display(phone: str | None) -> str:
    digits = normalize_phone(phone or "")
    if not digits:
        return "Not provided"
    return f"+{digits}"


def inquiry_completion_key(fields: EnquiryFields, whatsapp_id: str) -> str:
    phone = normalize_phone(fields.phone_number or whatsapp_id)
    parts = "|".join(
        [
            phone,
            (fields.event_type or "").strip().lower(),
            (fields.event_date or "").strip().lower(),
            (fields.callback_date or "").strip().lower(),
            (fields.callback_time or fields.preferred_callback or "").strip().lower(),
        ]
    )
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:32]


def inquiry_is_complete_for_alert(fields: EnquiryFields) -> bool:
    if not (fields.customer_name or "").strip():
        return False
    if not (fields.event_type or "").strip():
        return False
    if not (fields.event_date or "").strip():
        return False
    if fields.guest_count in (None, ""):
        return False
    loc = (fields.venue_area or fields.event_location or fields.venue_name or "").strip()
    if not loc:
        return False
    has_callback_day = bool((fields.callback_date or fields.preferred_callback or "").strip())
    has_callback_time = bool((fields.callback_time or fields.preferred_callback or "").strip())
    return has_callback_day and has_callback_time


def callback_datetime_from_fields(fields: EnquiryFields) -> datetime:
    date_src = (fields.callback_date or fields.preferred_callback or "").strip()
    time_src = (fields.callback_time or fields.preferred_callback or "").strip()
    composed = " ".join(p for p in (date_src, time_src) if p)
    if composed:
        parsed = parse_callback_time(composed)
        clock = _extract_clock_time((time_src or composed).lower().replace("–", "-"))
        if date_src and clock:
            try:
                day = parse_event_date(date_src)
                return datetime(day.year, day.month, day.day, clock[0], clock[1], 0)
            except Exception:
                return parsed
        return parsed
    return parse_callback_time("in 2 hours")


def _field_or_na(value: object | None) -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"none", "n/a", "-"}:
        return "Not provided"
    return text


def callback_day_label(stored: str | None, when: datetime) -> str:
    raw = (stored or "").strip()
    today = now_ist().date()
    try:
        day = when.date()
    except Exception:
        return raw or "Not provided"
    if day == today:
        return f"Today ({raw})" if raw else "Today"
    if day == today + timedelta(days=1):
        return f"Tomorrow ({raw})" if raw else "Tomorrow"
    return raw or when.strftime("%d %B %Y")


def format_owner_lead_message(enquiry: Enquiry, *, customer_phone: str) -> str:
    date_status = _field_or_na(getattr(enquiry, "dateStatus", None))
    if date_status not in {"Not provided"}:
        date_status = date_status.replace("confirmed", "Confirmed").replace("tentative", "Tentative")
    venue_name = (getattr(enquiry, "venueName", None) or "").strip()
    venue_area = (getattr(enquiry, "venueArea", None) or enquiry.eventLocation or "").strip()
    if venue_name and venue_area and venue_name.lower() not in venue_area.lower():
        venue = f"{venue_name}, {venue_area}"
    else:
        venue = venue_area or venue_name or "Not provided"
    catering = _field_or_na(getattr(enquiry, "mealPreference", None))
    requirements = getattr(enquiry, "specialRequirements", None) or "None"
    if str(requirements).strip().lower() in {"", "none", "not provided"}:
        requirements = "None"
    cb_date = getattr(enquiry, "callbackDate", None)
    cb_time = getattr(enquiry, "callbackTime", None)
    day_label = callback_day_label(cb_date, enquiry.preferredCallbackAt)
    time_label = (cb_time or "").strip() or "Not provided"
    event_date = enquiry.eventDate.strftime("%d %B %Y") if enquiry.eventDate else "Not provided"
    guest_label = str(enquiry.guestCount)
    if enquiry.notes:
        for line in enquiry.notes.splitlines():
            if line.startswith("Guest count requested: "):
                guest_label = line.split(": ", 1)[1].strip() or guest_label
                break
    return (
        "🔔 NEW EVENT INQUIRY\n\n"
        f"👤 Customer: {enquiry.customerName or 'Not provided'}\n"
        f"📱 WhatsApp: {format_whatsapp_display(customer_phone)}\n\n"
        f"🎉 Event: {enquiry.eventType or 'Not provided'}\n\n"
        f"📅 Event Date: {event_date}\n"
        f"📌 Date Status: {date_status}\n\n"
        f"👥 Guests: {guest_label or 'Not provided'}\n\n"
        f"📍 Venue: {venue}\n\n"
        f"🍽️ Catering: {catering}\n\n"
        f"📝 Special Requirements:\n{requirements}\n\n"
        f"📞 Callback: {day_label}\n"
        f"⏰ Time: {time_label}\n\n"
        "Please follow up with the customer."
    )


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def notification_retry_due(enquiry: Enquiry, now: datetime | None = None) -> bool:
    status = (getattr(enquiry, "notificationStatus", None) or "pending").lower()
    if status == "sent":
        return False
    attempts = int(getattr(enquiry, "notificationAttempts", 0) or 0)
    if attempts >= MAX_NOTIFICATION_ATTEMPTS:
        return False
    last = getattr(enquiry, "lastNotificationAttempt", None)
    if attempts <= 0 or last is None:
        return True
    wait = RETRY_WAIT_SECONDS.get(attempts)
    if wait is None:
        return False
    stamp = now or _utcnow_naive()
    if last.tzinfo is not None:
        last = last.replace(tzinfo=None)
    return (stamp - last).total_seconds() >= wait


async def save_enquiry(
    db: AsyncSession,
    fields: EnquiryFields,
    whatsapp_id: str,
    dishes: list[SelectedDishItem] | None = None,
    *,
    inbound_message_id: str | None = None,
) -> Enquiry:
    phone = normalize_phone(fields.phone_number or whatsapp_id)
    key = inquiry_completion_key(fields, whatsapp_id)
    existing = await db.execute(select(Enquiry).where(Enquiry.completionKey == key).limit(1))
    found = existing.scalar_one_or_none()
    if found is not None:
        logger.info("Enquiry already saved for completionKey=%s id=%s", key, found.id)
        if (found.notificationStatus or "") != "sent":
            await send_owner_lead_notification(db, found)
        return found

    callback_at = callback_datetime_from_fields(fields)
    event_date_raw = (fields.event_date or "").strip()
    event_date_parsed = parse_event_date(event_date_raw)
    note_lines: list[str] = []
    if event_date_raw:
        note_lines.append(f"Occasion date requested: {event_date_raw}")
    if fields.date_status:
        note_lines.append(f"Date status: {fields.date_status}")
    if fields.guest_count is not None:
        note_lines.append(f"Guest count requested: {fields.guest_count}")
    if fields.venue_name:
        note_lines.append(f"Venue name: {fields.venue_name}")
    if fields.venue_area:
        note_lines.append(f"Venue area: {fields.venue_area}")
    if fields.meal_preference:
        note_lines.append(f"Catering: {fields.meal_preference}")
    if fields.special_requirements:
        note_lines.append(f"Special requirements: {fields.special_requirements}")
    if fields.preferred_callback:
        note_lines.append(f"Callback requested: {fields.preferred_callback}")
        note_lines.append(f"Callback scheduled: {format_callback_display(callback_at, fields.preferred_callback)}")
    if fields.callback_date:
        note_lines.append(f"Callback date: {fields.callback_date}")
    if fields.callback_time:
        note_lines.append(f"Callback time: {fields.callback_time}")
    if fields.notes:
        note_lines.append(fields.notes)
    if dishes:
        note_lines.append("Cuisine preferences via WhatsApp")

    enquiry = Enquiry(
        customerName=fields.customer_name or "Unknown",
        phoneNumber=phone,
        eventType=fields.event_type or "General",
        eventDate=event_date_parsed,
        eventLocation=normalize_location(fields.event_location or fields.venue_area or fields.venue_name or "TBD"),
        guestCount=guest_count_for_db(fields.guest_count),
        preferredCallbackAt=callback_at,
        status=EnquiryStatus.NEW,
        notes="\n".join(note_lines) if note_lines else None,
        dateStatus=fields.date_status,
        venueName=fields.venue_name,
        venueArea=fields.venue_area or fields.event_location,
        mealPreference=fields.meal_preference,
        specialRequirements=fields.special_requirements,
        callbackDate=fields.callback_date,
        callbackTime=fields.callback_time,
        completionKey=key,
        whatsappMessageId=inbound_message_id,
        notificationStatus="pending",
        notificationAttempts=0,
    )
    db.add(enquiry)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(Enquiry).where(Enquiry.completionKey == key).limit(1))
        found = result.scalar_one_or_none()
        if found is not None:
            if (found.notificationStatus or "") != "sent":
                await send_owner_lead_notification(db, found)
            return found
        raise

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

    logger.info("Enquiry saved: %s (%s)", enquiry.id, enquiry.customerName)
    if inquiry_is_complete_for_alert(fields):
        await send_owner_lead_notification(db, enquiry)
    else:
        logger.warning("Enquiry %s saved but incomplete for owner alert", enquiry.id)
        enquiry.notificationStatus = "failed"
        enquiry.notificationError = "Inquiry incomplete — owner alert not sent"
        await db.commit()
    return enquiry


async def append_followup_note_for_phone(
    db: AsyncSession,
    whatsapp_id: str,
    note: str,
) -> bool:
    """Append a post-sign-off customer note to the latest enquiry for this phone."""
    text = (note or "").strip()
    if not text:
        return False
    phone = normalize_phone(whatsapp_id)
    result = await db.execute(
        select(Enquiry).where(Enquiry.phoneNumber == phone).order_by(desc(Enquiry.createdAt)).limit(1)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        return False
    marker = f"[Follow-up note]: {text}"
    existing = (enquiry.notes or "").strip()
    if marker in existing:
        return True
    enquiry.notes = f"{existing}\n{marker}".strip() if existing else marker
    await db.commit()
    return True


def _format_dishes_for_whatsapp(dishes: list[SelectedDishItem] | None) -> str:
    if not dishes:
        return "Cuisine: To be discussed on callback"
    lines = ["*Cuisine / menu style:*"]
    for d in dishes:
        lines.append(f"• {d.dish_name}")
    return "\n".join(lines)


async def send_owner_lead_notification(
    db: AsyncSession,
    enquiry: Enquiry,
    *,
    force: bool = False,
) -> bool:
    """Send the owner WhatsApp alert. Never sends to the customer unless they are the owner."""
    if not force and (enquiry.notificationStatus or "") == "sent":
        return True
    if not force and not notification_retry_due(enquiry):
        return False

    owner = normalize_phone(await get_owner_phone(db))
    customer = normalize_phone(enquiry.phoneNumber)
    now = _utcnow_naive()
    enquiry.lastNotificationAttempt = now
    enquiry.notificationAttempts = int(enquiry.notificationAttempts or 0) + 1

    if not owner:
        enquiry.notificationStatus = "failed"
        enquiry.notificationError = "OWNER_WHATSAPP_NUMBER is not configured"
        await db.commit()
        logger.warning("OWNER_WHATSAPP_NUMBER not set – skipping owner alert for %s", enquiry.id)
        return False

    recipient = owner
    if recipient != owner:
        enquiry.notificationStatus = "failed"
        enquiry.notificationError = "Owner alert recipient mismatch"
        await db.commit()
        return False
    if recipient == customer and owner != customer:
        enquiry.notificationStatus = "failed"
        enquiry.notificationError = "Refused to send owner alert to customer number"
        await db.commit()
        return False

    message = format_owner_lead_message(enquiry, customer_phone=customer)
    result = await send_whatsapp_message_detailed(recipient, message)
    if result.ok:
        enquiry.notificationStatus = "sent"
        enquiry.notificationMessageId = result.message_id
        enquiry.notificationSentAt = now
        enquiry.notificationError = None
        await db.commit()
        logger.info("Owner notified via WhatsApp: %s enquiry=%s", recipient, enquiry.id)
        return True

    enquiry.notificationStatus = "failed"
    enquiry.notificationError = (result.error or "Unknown WhatsApp error")[:500]
    await db.commit()
    logger.error("Failed to send owner WhatsApp alert to %s: %s", recipient, result.error)
    return False


async def notify_owner_new_enquiry(
    db: AsyncSession,
    enquiry: Enquiry,
    dishes: list[SelectedDishItem] | None = None,
) -> None:
    del dishes
    await send_owner_lead_notification(db, enquiry, force=True)


async def notify_owner_callback_reminder(db: AsyncSession, enquiry: Enquiry) -> bool:
    owner = normalize_phone(await get_owner_phone(db))
    if not owner:
        enquiry.reminderError = "OWNER_WHATSAPP_NUMBER is not configured"
        enquiry.lastReminderAttempt = _utcnow_naive()
        enquiry.reminderAttempts = int(enquiry.reminderAttempts or 0) + 1
        await db.commit()
        return False

    recipient = owner
    if recipient != owner:
        return False
    customer = normalize_phone(enquiry.phoneNumber)
    if recipient == customer and owner != customer:
        enquiry.reminderError = "Refused to send reminder to customer number"
        await db.commit()
        return False

    cb_time = (getattr(enquiry, "callbackTime", None) or "").strip()
    message = (
        "⏰ CALLBACK REMINDER (15 minutes)\n\n"
        f"Call *{enquiry.customerName}* in about 15 minutes.\n\n"
        f"📱 WhatsApp: {format_whatsapp_display(enquiry.phoneNumber)}\n"
        f"🎉 Event: {enquiry.eventType}\n"
        f"📅 Date: {enquiry.eventDate.strftime('%d %B %Y')}\n"
        f"📍 Venue: {getattr(enquiry, 'venueArea', None) or enquiry.eventLocation}\n"
        f"👥 Guests: {enquiry.guestCount}\n"
        f"📞 Callback: {callback_day_label(getattr(enquiry, 'callbackDate', None), enquiry.preferredCallbackAt)}\n"
        f"⏰ Time: {cb_time or format_callback_display(enquiry.preferredCallbackAt, _callback_text_from_notes(enquiry.notes))}"
    )
    result = await send_whatsapp_message_detailed(recipient, message)
    enquiry.lastReminderAttempt = _utcnow_naive()
    enquiry.reminderAttempts = int(enquiry.reminderAttempts or 0) + 1
    if result.ok:
        enquiry.reminderSent = True
        enquiry.reminderError = None
        await db.commit()
        logger.info("Callback reminder sent to owner for enquiry %s", enquiry.id)
        return True
    enquiry.reminderError = (result.error or "Unknown WhatsApp error")[:500]
    await db.commit()
    logger.error("Callback reminder failed for enquiry %s: %s", enquiry.id, result.error)
    return False


async def retry_failed_owner_alerts(db: AsyncSession) -> int:
    result = await db.execute(
        select(Enquiry).where(Enquiry.notificationStatus.in_(["failed", "pending"]))
    )
    sent = 0
    for enquiry in result.scalars().all():
        if notification_retry_due(enquiry):
            if await send_owner_lead_notification(db, enquiry):
                sent += 1
    return sent


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
