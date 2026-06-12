import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ChatConversationOut, ChatMessageOut, OwnerChatMessageIn
from app.services.chat_log import get_messages, list_conversations, log_owner_message
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

    await log_owner_message(db, normalized, text)
    sent = await send_whatsapp_message(normalized, text)
    if not sent:
        raise HTTPException(status_code=502, detail="Could not send WhatsApp message")
    logger.info("Owner replied to %s via dashboard chat", normalized)
    return {"ok": True, "phoneNumber": normalized}
