import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services.conversation_handler import handle_conversation
from app.services.whatsapp_client import send_whatsapp_message, verify_webhook_signature

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


@router.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge or "", media_type="text/plain")
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
            "Thanks for reaching SRIVATSANKA! Please type your message so our team can help you plan your event.",
        )
        return {"status": "unsupported_type"}

    text = message.get("text", {}).get("body", "").strip()
    if not text:
        return {"status": "empty_message"}

    result, _saved = await handle_conversation(from_number, text, db)
    await send_whatsapp_message(from_number, result.reply)
    return {"status": "ok"}
