"""Wipe all dashboard data (hosted or local)."""

import logging
import shutil
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Dish,
    Enquiry,
    EnquiryDish,
    EventPhoto,
    Expense,
    InvoiceUpload,
    Notification,
    ProcessedWhatsappMessage,
    Vendor,
    WhatsappChatMessage,
    WhatsappChatState,
    Worker,
    WorkerAssignment,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


async def clear_all_dashboard_data(session: AsyncSession) -> dict:
    """Delete every enquiry, order line, vendor, worker, expense, invoice, notification, and dish."""
    counts: dict[str, int] = {}

    for model, key in [
        (EnquiryDish, "enquiry_dishes"),
        (InvoiceUpload, "invoice_uploads"),
        (EventPhoto, "event_photos"),
        (WorkerAssignment, "worker_assignments"),
        (WhatsappChatMessage, "chat_messages"),
        (WhatsappChatState, "chat_states"),
        (ProcessedWhatsappMessage, "processed_whatsapp_messages"),
        (Enquiry, "enquiries"),
        (Notification, "notifications"),
        (Expense, "expenses"),
        (Worker, "workers"),
        (Vendor, "vendors"),
        (Dish, "dishes"),
    ]:
        n = await session.scalar(select(func.count()).select_from(model)) or 0
        if n:
            await session.execute(delete(model))
        counts[key] = n

    await session.commit()

    files_removed = 0
    if UPLOAD_DIR.exists():
        for path in UPLOAD_DIR.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
                files_removed += 1
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                files_removed += 1

    counts["upload_files"] = files_removed
    logger.warning("Dashboard data cleared: %s", counts)
    return counts
