"""Durable inbound WhatsApp idempotency and per-user processing locks."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProcessedWhatsappMessage
from app.services.whatsapp_client import normalize_phone

logger = logging.getLogger(__name__)

_USER_LOCKS: dict[str, asyncio.Lock] = {}
_USER_LOCKS_GUARD = asyncio.Lock()


async def user_lock(phone: str) -> asyncio.Lock:
    key = normalize_phone(phone) or (phone or "").strip()
    async with _USER_LOCKS_GUARD:
        lock = _USER_LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _USER_LOCKS[key] = lock
        return lock


async def claim_inbound_message(db: AsyncSession, message_id: str, phone: str) -> bool:
    """Atomically claim a WhatsApp wamid. False means already claimed/processed."""
    mid = (message_id or "").strip()
    if not mid:
        return True
    phone = normalize_phone(phone) or phone
    row = ProcessedWhatsappMessage(
        messageId=mid,
        phoneNumber=phone,
        receivedAt=datetime.now(timezone.utc).replace(tzinfo=None),
        status="claimed",
    )
    db.add(row)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        logger.info("whatsapp_duplicate_ignored message_id=%s phone=%s", mid, phone)
        return False


async def mark_message_result(
    db: AsyncSession,
    message_id: str,
    *,
    status: str,
    response_id: str | None = None,
) -> None:
    mid = (message_id or "").strip()
    if not mid:
        return
    result = await db.execute(
        select(ProcessedWhatsappMessage).where(ProcessedWhatsappMessage.messageId == mid)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.status = status
    row.processedAt = datetime.now(timezone.utc).replace(tzinfo=None)
    if response_id:
        row.responseId = response_id
    await db.commit()
