import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.chat_handoff import is_bot_paused_for_phone
from app.services.chat_log import log_bot_message, log_customer_message
from app.services.conversation_handler import handle_conversation
from app.services.whatsapp_client import send_whatsapp_image, send_whatsapp_message, verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = (request.query_params.get("hub.verify_token") or "").strip()
    challenge = request.query_params.get("hub.challenge")
    expected = settings.whatsapp_verify_token.strip()

    if mode == "subscribe" and token and token == expected:
        logger.info("Meta webhook verified")
        return Response(content=challenge or "", media_type="text/plain", status_code=200)

    logger.warning(
        "Meta webhook verify failed (mode=%s, token_match=%s, expected_len=%d, got_len=%d)",
        mode,
        token == expected,
        len(expected),
        len(token),
    )
    return Response(status_code=403)


@router.post("/webhook")
async def receive_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw_body = await request.body()

    if not verify_webhook_signature(raw_body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Invalid signature")

    import json

    try:
        body = json.loads(raw_body)
        value = body["entry"][0]["changes"][0]["value"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return {"status": "ignored"}

    messages = value.get("messages", [])
    if not messages:
        return {"status": "no_messages"}

    message = messages[0]
    from_number = message.get("from", "")

    if message.get("type") != "text":
        await send_whatsapp_message(
            from_number,
            "Thanks for reaching SRIVATSANKA EVENTS! Please type your message so our team can help you plan your event.",
        )
        return {"status": "unsupported_type"}

    text = message.get("text", {}).get("body", "").strip()
    if not text:
        return {"status": "empty_message"}

    try:
        await log_customer_message(db, from_number, text)
    except Exception:
        logger.exception("Failed to log customer WhatsApp message for %s", from_number)

    if await is_bot_paused_for_phone(db, from_number):
        logger.info("Bot paused for %s — owner is handling this chat", from_number)
        return {"status": "bot_paused"}

    result, _saved = await handle_conversation(from_number, text, db)
    for attachment in result.media:
        await send_whatsapp_image(from_number, attachment.url, caption=attachment.caption)
    sent, send_err = await send_whatsapp_message(from_number, result.reply)
    if not sent:
        logger.error("Bot reply not delivered to %s: %s", from_number, send_err)

    try:
        await log_bot_message(db, from_number, result.reply, result.media)
    except Exception:
        logger.exception("Failed to log bot WhatsApp message for %s", from_number)
    return {"status": "ok"}
