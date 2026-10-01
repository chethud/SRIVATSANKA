import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ChatConversationOut, ChatMessageOut, OwnerChatMessageIn
from app.services.chat_handoff import BOT_PAUSE_ENABLED, pause_bot_for_phone, resume_bot_for_phone
from app.services.enquiry_service import mark_enquiry_seen_for_phone
from app.services.chat_log import delete_conversation, get_messages, list_conversations, log_owner_message
from app.services.whatsapp_client import normalize_phone, send_whatsapp_message

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.get("/conversations", response_model=list[ChatConversationOut])
async def get_conversations(db: AsyncSession = Depends(get_db)) -> list[ChatConversationOut]:
    rows = await list_conversations(db)
    return [ChatConversationOut(**row) for row in rows]


@router.get("/conversations/{phone}/messages", response_model=list[ChatMessageOut])
async def get_conversation_messages(
    phone: str,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessageOut]:
    normalized = normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    rows = await get_messages(db, normalized)
    return [ChatMessageOut(**row) for row in rows]


@router.post("/conversations/{phone}/messages")
async def send_owner_message(
    phone: str,
    payload: OwnerChatMessageIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    normalized = normalize_phone(phone)
    text = payload.text.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    sent, err = await send_whatsapp_message(normalized, text)
    if not sent:
        raise HTTPException(status_code=502, detail=err or "Could not send WhatsApp message")
    await log_owner_message(db, normalized, text)
    await pause_bot_for_phone(db, normalized)
    await mark_enquiry_seen_for_phone(db, normalized)
    paused = BOT_PAUSE_ENABLED
    logger.info(
        "Owner replied to %s via dashboard chat — bot auto-reply %s",
        normalized,
        "paused" if paused else "still active",
    )
    return {"ok": True, "phoneNumber": normalized, "botPaused": paused}


@router.post("/conversations/{phone}/pause")
async def pause_bot_for_conversation(
    phone: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Owner clicked Reply — stop auto-replies so they can message manually."""
    normalized = normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    await pause_bot_for_phone(db, normalized)
    await mark_enquiry_seen_for_phone(db, normalized)
    paused = BOT_PAUSE_ENABLED
    logger.info(
        "Bot auto-reply %s for %s (owner taking over)",
        "paused" if paused else "left active",
        normalized,
    )
    return {"ok": True, "phoneNumber": normalized, "botPaused": paused}


@router.post("/conversations/{phone}/resume")
async def resume_bot_for_conversation(
    phone: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    normalized = normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    await resume_bot_for_phone(db, normalized)
    logger.info("Bot auto-reply resumed for %s", normalized)
    return {"ok": True, "phoneNumber": normalized, "botPaused": False}


@router.delete("/conversations/{phone}")
async def delete_chat_conversation(
    phone: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    normalized = normalize_phone(phone)
    if not normalized:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    deleted = await delete_conversation(db, normalized)
    return {"ok": True, "phoneNumber": normalized, "deletedMessages": deleted}
