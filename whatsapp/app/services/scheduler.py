import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Enquiry, EnquiryStatus, Notification, NotificationType
from app.services.enquiry_service import notify_owner_callback_reminder

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def check_callback_reminders() -> None:
    now = datetime.now()
    window_start = now + timedelta(minutes=15)
    window_end = now + timedelta(minutes=20)

    async with SessionLocal() as db:
        result = await db.execute(
            select(Enquiry).where(
                Enquiry.status == EnquiryStatus.NEW,
                Enquiry.reminderSent.is_(False),
                Enquiry.preferredCallbackAt >= window_start,
                Enquiry.preferredCallbackAt <= window_end,
            )
        )
        enquiries = result.scalars().all()

        for enquiry in enquiries:
            logger.info("Sending callback reminder for %s (%s)", enquiry.customerName, enquiry.id)
            await notify_owner_callback_reminder(enquiry)
            enquiry.reminderSent = True
            db.add(
                Notification(
                    type=NotificationType.CALLBACK_REMINDER,
                    title="Callback Reminder",
                    message=f"Call {enquiry.customerName} in 15–20 minutes",
                    enquiryId=enquiry.id,
                )
            )
        if enquiries:
            await db.commit()


def start_scheduler() -> None:
    scheduler.add_job(check_callback_reminders, "interval", minutes=1, id="callback_reminders")
    scheduler.start()
    logger.info("Callback reminder scheduler started (WhatsApp alert 15–20 min before callback)")
