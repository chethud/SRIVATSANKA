"""Persist WhatsApp chat messages for the dashboard inbox."""

from __future__ import annotations

import json
import logging

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Enquiry, WhatsappChatMessage
from app.schemas import MediaAttachment
from app.services.whatsapp_client import normalize_phone

logger = logging.getLogger(__name__)


def _media_to_json(media: list[MediaAttachment] | None) -> str | None:
    if not media:
        return None
    payload = [{"url": m.url, "caption": m.caption} for m in media]
    return json.dumps(payload)


def _media_from_json(raw: str | None) -> list[dict]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


async def log_customer_message(db: AsyncSession, phone: str, text: str) -> None:
    phone = normalize_phone(phone)
    if not phone or not text.strip():
        return
    db.add(WhatsappChatMessage(phoneNumber=phone, role="customer", body=text.strip()))
    await db.commit()


async def log_bot_message(
    db: AsyncSession,
    phone: str,
    text: str,
    media: list[MediaAttachment] | None = None,
) -> None:
    phone = normalize_phone(phone)
    if not phone or not text.strip():
        return
    db.add(
        WhatsappChatMessage(
            phoneNumber=phone,
            role="bot",
            body=text.strip(),
            mediaJson=_media_to_json(media),
        )
    )
    await db.commit()


async def log_owner_message(db: AsyncSession, phone: str, text: str) -> None:
    phone = normalize_phone(phone)
    if not phone or not text.strip():
        return
    db.add(WhatsappChatMessage(phoneNumber=phone, role="owner", body=text.strip()))
    await db.commit()


async def _customer_name_for_phone(db: AsyncSession, phone: str) -> str | None:
    result = await db.execute(
        select(Enquiry.customerName)
        .where(Enquiry.phoneNumber == phone)
        .order_by(desc(Enquiry.createdAt))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row if row else None


async def list_conversations(db: AsyncSession) -> list[dict]:
    summary = await db.execute(
        select(
            WhatsappChatMessage.phoneNumber,
            func.max(WhatsappChatMessage.createdAt).label("last_at"),
            func.count().label("message_count"),
        )
        .group_by(WhatsappChatMessage.phoneNumber)
        .order_by(desc(func.max(WhatsappChatMessage.createdAt)))
    )
    rows = summary.all()
    conversations: list[dict] = []
    for phone, last_at, message_count in rows:
        latest = await db.execute(
            select(WhatsappChatMessage)
            .where(WhatsappChatMessage.phoneNumber == phone)
            .order_by(desc(WhatsappChatMessage.createdAt))
            .limit(1)
        )
        msg = latest.scalar_one()
        name = await _customer_name_for_phone(db, phone)
        conversations.append(
            {
                "phoneNumber": phone,
                "customerName": name,
                "lastMessage": msg.body[:160],
                "lastRole": msg.role,
                "lastAt": last_at,
                "messageCount": int(message_count),
            }
        )
    return conversations


async def get_messages(db: AsyncSession, phone: str) -> list[dict]:
    phone = normalize_phone(phone)
    result = await db.execute(
        select(WhatsappChatMessage)
        .where(WhatsappChatMessage.phoneNumber == phone)
        .order_by(WhatsappChatMessage.createdAt.asc())
    )
    messages = []
    for msg in result.scalars().all():
        messages.append(
            {
                "id": msg.id,
                "phoneNumber": msg.phoneNumber,
                "role": msg.role,
                "body": msg.body,
                "media": _media_from_json(msg.mediaJson),
                "createdAt": msg.createdAt,
            }
        )
    return messages
