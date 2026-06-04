import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Enquiry, EnquiryDish, EnquiryStatus, Notification, NotificationType
from app.schemas import EnquiryFields, SelectedDishItem
from app.services.ai_agent import parse_callback_time, parse_event_date
from app.services.whatsapp_client import normalize_phone, send_whatsapp_message

logger = logging.getLogger(__name__)


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

    enquiry = Enquiry(
        customerName=fields.customer_name or "Unknown",
        phoneNumber=phone,
        eventType=fields.event_type or "General",
        eventDate=parse_event_date(fields.event_date or ""),
        eventLocation=fields.event_location or "TBD",
        guestCount=fields.guest_count or 0,
        preferredCallbackAt=parse_callback_time(fields.preferred_callback or "in 2 hours"),
        status=EnquiryStatus.NEW,
        notes="Menu selected via WhatsApp" if dishes else None,
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
    )
    db.add(notification)
    await db.commit()
    await db.refresh(enquiry)

    logger.info("Enquiry saved: %s (%s) with %d dishes", enquiry.id, enquiry.customerName, len(dishes or []))
    await notify_owner_new_enquiry(enquiry, dishes)
    return enquiry


def _format_dishes_for_whatsapp(dishes: list[SelectedDishItem] | None) -> str:
    if not dishes:
        return "Menu: To be discussed on callback"
    lines = ["*Selected Dishes:*"]
    for d in dishes:
        custom = ", ".join(d.customizations) if d.customizations else "No customization"
        lines.append(f"• {d.dish_name} ({d.category}) – {custom}")
    return "\n".join(lines)


async def notify_owner_new_enquiry(
    enquiry: Enquiry, dishes: list[SelectedDishItem] | None = None
) -> None:
    owner = normalize_phone(settings.owner_phone_number)
    if not owner:
        logger.warning("OWNER_PHONE_NUMBER not set – skipping owner alert")
        return

    menu_section = _format_dishes_for_whatsapp(dishes)
    message = (
        "🔔 *New Enquiry!*\n\n"
        f"Name: {enquiry.customerName}\n"
        f"Phone: {enquiry.phoneNumber}\n"
        f"Event: {enquiry.eventType}\n"
        f"Date: {enquiry.eventDate.strftime('%d %b %Y')}\n"
        f"Location: {enquiry.eventLocation}\n"
        f"Guests: {enquiry.guestCount}\n"
        f"Callback: {enquiry.preferredCallbackAt.strftime('%d %b %Y, %I:%M %p')}\n\n"
        f"{menu_section}\n\n"
        "Please contact the customer at the preferred callback time."
    )
    sent = await send_whatsapp_message(owner, message)
    if sent:
        logger.info("Owner notified via WhatsApp: %s", owner)
    else:
        logger.error("Failed to send owner WhatsApp alert to %s", owner)


async def notify_owner_callback_reminder(enquiry: Enquiry) -> None:
    owner = normalize_phone(settings.owner_phone_number)
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
    sent = await send_whatsapp_message(owner, message)
    if sent:
        logger.info("Callback reminder sent to owner for enquiry %s", enquiry.id)
