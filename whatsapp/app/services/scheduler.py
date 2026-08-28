import logging
from datetime import timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Enquiry, Notification, NotificationType
from app.services.callback_time import now_ist
from app.services.enquiry_service import notify_owner_callback_reminder, retry_failed_owner_alerts

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def check_callback_reminders() -> None:
    now = now_ist()
    window_start = now + timedelta(minutes=14)
    window_end = now + timedelta(minutes=16)

    async with SessionLocal() as db:
        result = await db.execute(
            select(Enquiry).where(
                Enquiry.reminderSent.is_(False),
                Enquiry.preferredCallbackAt >= window_start,
                Enquiry.preferredCallbackAt <= window_end,
            )
        )
        enquiries = result.scalars().all()

        for enquiry in enquiries:
            logger.info("Sending callback reminder for %s (%s)", enquiry.customerName, enquiry.id)
            sent = await notify_owner_callback_reminder(db, enquiry)
            if sent:
                db.add(
                    Notification(
                        type=NotificationType.CALLBACK_REMINDER,
                        title="Callback Reminder",
                        message=f"Call {enquiry.customerName} in 15 minutes",
                        enquiryId=enquiry.id,
                    )
                )
                await db.commit()


async def check_owner_alert_retries() -> None:
    async with SessionLocal() as db:
        try:
            sent = await retry_failed_owner_alerts(db)
            if sent:
                logger.info("Retried owner alerts: %s sent", sent)
        except Exception:
            logger.exception("Owner alert retry job failed")


def start_scheduler() -> None:
    if not scheduler.get_job("callback_reminders"):
        scheduler.add_job(check_callback_reminders, "interval", minutes=1, id="callback_reminders")
    if not scheduler.get_job("owner_alert_retries"):
        scheduler.add_job(check_owner_alert_retries, "interval", seconds=15, id="owner_alert_retries")
    if not scheduler.running:
        scheduler.start()
        logger.info("Owner alert + 15-minute callback reminder scheduler started")
