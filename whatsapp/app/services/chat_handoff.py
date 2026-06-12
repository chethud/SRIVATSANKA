"""Pause/resume automatic bot replies when the owner takes over from the dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WhatsappChatState
from app.services.whatsapp_client import normalize_phone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def pause_bot_for_phone(db: AsyncSession, phone: str) -> None:
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
    phone = normalize_phone(phone)
    if not phone:
        return False
    state = await db.get(WhatsappChatState, phone)
    return bool(state and state.botPaused)


async def get_bot_paused_map(db: AsyncSession, phones: list[str]) -> dict[str, bool]:
    if not phones:
        return {}
    result: dict[str, bool] = {}
    for phone in phones:
        normalized = normalize_phone(phone)
        if normalized:
            result[normalized] = await is_bot_paused_for_phone(db, normalized)
    return result
