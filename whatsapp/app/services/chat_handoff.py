"""Pause/resume automatic bot replies when the owner takes over from the dashboard.

Bot pause is disabled: owner replies must never stop WhatsApp auto-replies.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WhatsappChatState
from app.services.whatsapp_client import normalize_phone

# When False, owner dashboard replies never pause the bot.
BOT_PAUSE_ENABLED = False


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def clear_all_bot_pauses(db: AsyncSession) -> int:
    """Clear any leftover botPaused flags (e.g. after deploy)."""
    result = await db.execute(
        update(WhatsappChatState)
        .where(WhatsappChatState.botPaused.is_(True))
        .values(botPaused=False, pausedAt=None)
    )
    await db.commit()
    return int(result.rowcount or 0)


async def pause_bot_for_phone(db: AsyncSession, phone: str) -> None:
    if not BOT_PAUSE_ENABLED:
        # Keep any prior pause cleared so inbound messages still get bot replies.
        await resume_bot_for_phone(db, phone)
        return
    phone = normalize_phone(phone)
    if not phone:
        return
    state = await db.get(WhatsappChatState, phone)
    if state:
        state.botPaused = True
        state.pausedAt = _utcnow()
    else:
        db.add(WhatsappChatState(phoneNumber=phone, botPaused=True, pausedAt=_utcnow()))
    await db.commit()


async def resume_bot_for_phone(db: AsyncSession, phone: str) -> None:
    phone = normalize_phone(phone)
    if not phone:
        return
    state = await db.get(WhatsappChatState, phone)
    if state:
        state.botPaused = False
        state.pausedAt = None
    else:
        db.add(WhatsappChatState(phoneNumber=phone, botPaused=False))
    await db.commit()


async def is_bot_paused_for_phone(db: AsyncSession, phone: str) -> bool:
    if not BOT_PAUSE_ENABLED:
        return False
    phone = normalize_phone(phone)
    if not phone:
        return False
    state = await db.get(WhatsappChatState, phone)
    return bool(state and state.botPaused)


async def get_bot_paused_map(db: AsyncSession, phones: list[str]) -> dict[str, bool]:
    if not phones:
        return {}
    if not BOT_PAUSE_ENABLED:
        return {normalize_phone(p): False for p in phones if normalize_phone(p)}
    result: dict[str, bool] = {}
    for phone in phones:
        normalized = normalize_phone(phone)
        if normalized:
            result[normalized] = await is_bot_paused_for_phone(db, normalized)
    return result
