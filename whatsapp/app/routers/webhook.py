import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.chat_handoff import is_bot_paused_for_phone
from app.services.chat_log import log_bot_message, log_customer_message
from app.services.conversation_handler import handle_conversation
from app.services.message_idempotency import (
    claim_inbound_message,
    mark_message_result,
    user_lock,
)
from app.services.session_store import session_store
from app.services.whatsapp_client import (
    send_whatsapp_image,
    send_whatsapp_interactive,
    send_whatsapp_message,
    verify_webhook_signature,
)
from app.services.whatsapp_interactive import parse_inbound_message

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
    message_id = (message.get("id") or "").strip()
    from_number = message.get("from", "")

    if not await claim_inbound_message(db, message_id, from_number):
        return {"status": "duplicate"}

    lock = await user_lock(from_number)
    async with lock:
        return await _process_claimed_message(db, message, message_id, from_number)


async def _process_claimed_message(db, message, message_id: str, from_number: str) -> dict:
    mtype = message.get("type")
    text, button_id = parse_inbound_message(message)
    if mtype not in {"text", "interactive", "button"}:
        await send_whatsapp_message(
            from_number,
            "Thanks for reaching Srivatsanka Events and Services! Please type your message so our team can help you plan your event.",
        )
        await mark_message_result(db, message_id, status="sent")
        return {"status": "unsupported_type"}

    if not text and not button_id:
        await mark_message_result(db, message_id, status="skipped")
        return {"status": "empty_message"}

    try:
        await log_customer_message(db, from_number, text or button_id or "")
    except Exception:
        logger.exception("Failed to log customer WhatsApp message for %s", from_number)

    if await is_bot_paused_for_phone(db, from_number):
        logger.info("Bot paused for %s — owner is handling this chat", from_number)
        await mark_message_result(db, message_id, status="skipped")
        return {"status": "bot_paused"}

    session_before = session_store.get(from_number)
    previous_state = session_before.guided_step.value

    try:
        result, _saved = await handle_conversation(
            from_number, text, db, message_id=message_id, button_id=button_id
        )
    except Exception:
        logger.exception("Conversation engine failed for %s message_id=%s", from_number, message_id)
        await mark_message_result(db, message_id, status="error")
        raise

    session = session_store.get(from_number)
    logger.info(
        "whatsapp_turn user_id=%s message_id=%s message_text=%r previous_state=%s next_state=%s "
        "expected_field=%s venue_status=%s location=%r callback=%r response_status=sending",
        from_number,
        message_id,
        text[:180],
        previous_state,
        session.guided_step.value,
        session.last_asked_slot,
        session.fields.venue_status,
        session.fields.event_location,
        session.fields.preferred_callback,
    )

    if result.media:
        ok_img = await send_whatsapp_image(from_number, result.media[0].url, caption=None)
        if not ok_img:
            logger.error("Bot image not delivered to %s", from_number)

    if result.interactive:
        sent, send_err = await send_whatsapp_interactive(from_number, result.interactive)
        if not sent:
            sent, send_err = await send_whatsapp_message(from_number, result.reply)
    else:
        sent, send_err = await send_whatsapp_message(from_number, result.reply)
    if not sent:
        logger.error("Bot reply not delivered to %s: %s", from_number, send_err)
        fail_note = (send_err or "WhatsApp send failed").strip()
        if len(fail_note) > 280:
            fail_note = fail_note[:277] + "…"
        body = f"{result.reply}\n\n⚠️ Not delivered to WhatsApp — {fail_note}"
        try:
            await log_bot_message(db, from_number, body, result.media)
        except Exception:
            logger.exception("Failed to log undelivered bot message for %s", from_number)
        await mark_message_result(db, message_id, status="error")
        return {"status": "send_failed", "error": send_err}

    try:
        await log_bot_message(db, from_number, result.reply, result.media)
    except Exception:
        logger.exception("Failed to log bot WhatsApp message for %s", from_number)
    await mark_message_result(db, message_id, status="sent", response_id=message_id)
    return {"status": "ok"}
