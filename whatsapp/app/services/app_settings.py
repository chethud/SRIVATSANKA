"""Persisted app settings that can override env defaults."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import AppSetting
from app.services.whatsapp_client import normalize_phone

OWNER_PHONE_KEY = "owner_phone_number"


async def get_setting(db: AsyncSession, key: str) -> str | None:
    row = await db.get(AppSetting, key)
    if not row:
        return None
    value = (row.value or "").strip()
    return value or None


async def set_setting(db: AsyncSession, key: str, value: str) -> str:
    cleaned = (value or "").strip()
    row = await db.get(AppSetting, key)
    if row:
        row.value = cleaned
    else:
        db.add(AppSetting(key=key, value=cleaned))
    await db.commit()
    return cleaned


async def get_owner_phone(db: AsyncSession) -> str:
    """Dashboard override wins; otherwise OWNER_PHONE_NUMBER from env."""
    override = await get_setting(db, OWNER_PHONE_KEY)
    if override:
        return normalize_phone(override)
    return normalize_phone(settings.owner_phone_number)


async def set_owner_phone(db: AsyncSession, phone: str) -> str:
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        raise ValueError("Enter a valid phone number with country code (e.g. 919945607074)")
    await set_setting(db, OWNER_PHONE_KEY, normalized)
    return normalized
