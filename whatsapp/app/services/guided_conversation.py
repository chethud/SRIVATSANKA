"""Conversational replies during guided WhatsApp enquiry (Gemini + fallback)."""

import logging

from app.data.company_knowledge import COMPANY, EVENT_TYPE_DETAILS, POPULAR_DISHES
from app.services.conversation_turns import customer_wants_to_proceed, natural_continue_hint
from app.services.gemini_conversation import (
    generate_details_phase_reply,
    generate_showcase_reply,
    is_gemini_configured,
    looks_like_question,
    trim_whatsapp_reply,
)
from app.services.session_store import ConversationSession
from app.services.website_gallery import customer_wants_photos

logger = logging.getLogger(__name__)


def customer_is_asking(text: str) -> bool:
    if customer_wants_to_proceed(text):
        return False
    return looks_like_question(text)


def _fallback_answer(
    session: ConversationSession,
    user_text: str,
    *,
    sharing_photos: bool = False,
) -> str:
    name = session.fields.customer_name or "there"
    event = session.fields.event_type or "celebrations"
    details = EVENT_TYPE_DETAILS.get(event, EVENT_TYPE_DETAILS["General"])
    hook = details.get("short_reply") or "Happy to help!"
    t = user_text.lower()
    hint = natural_continue_hint()

    if sharing_photos or customer_wants_photos(user_text):
        return f"Here are some photos from our events 👇 {hint}"

    if any(w in t for w in ("company", "about", "who are", "your team", "srivatsanka", "kannan")):
        return (
            f"We're *{COMPANY['brand_name']}* — pure veg events in Bengaluru since {COMPANY['established']}. "
            f"{hint}"
        )

    if any(w in t for w in ("how many", "work", "done", "events", "experience", "portfolio", "wedding")):
        return f"We've handled hundreds of occasions in Bengaluru. {hook} {hint}"

    if any(w in t for w in ("price", "cost", "charge", "budget", "rate")):
        return f"Pricing depends on menu and guest count — our team walks you through it on a call. {hint}"

    if any(w in t for w in ("menu", "dish", "food", "cuisine", "veg", "service")):
        dishes = ", ".join(POPULAR_DISHES[:3])
        return f"We're 100% vegetarian — favourites include {dishes}, and plenty more. {hint}"

    return f"Happy to help, *{name}*! {hint}"


async def _gemini_or_fallback(
    session: ConversationSession,
    user_text: str,
    *,
    next_detail_prompt: str | None = None,
    sharing_photos: bool = False,
) -> str:
    if not is_gemini_configured():
        logger.warning("GEMINI_API_KEY not set — using template reply for: %s", user_text[:80])
        return _fallback_answer(session, user_text, sharing_photos=sharing_photos)

    try:
        if next_detail_prompt is not None:
            reply = await generate_details_phase_reply(session, user_text, next_detail_prompt)
        else:
            reply = await generate_showcase_reply(
                session,
                user_text,
                sharing_photos=sharing_photos or customer_wants_photos(user_text),
            )
        return trim_whatsapp_reply(reply)
    except Exception:
        logger.exception("Gemini conversation failed for message: %s", user_text[:80])
        return _fallback_answer(session, user_text, sharing_photos=sharing_photos)


async def answer_showcase_question(
    session: ConversationSession,
    user_text: str,
    *,
    sharing_photos: bool = False,
) -> str:
    session.history.append({"role": "user", "content": user_text})
    reply = await _gemini_or_fallback(
        session,
        user_text,
        sharing_photos=sharing_photos or customer_wants_photos(user_text),
    )
    session.history.append({"role": "assistant", "content": reply})
    return reply


async def answer_details_question(
    session: ConversationSession,
    user_text: str,
    next_detail_prompt: str | None,
) -> str:
    session.history.append({"role": "user", "content": user_text})
    reply = await _gemini_or_fallback(
        session,
        user_text,
        next_detail_prompt=next_detail_prompt,
        sharing_photos=customer_wants_photos(user_text),
    )
    session.history.append({"role": "assistant", "content": reply})
    return reply
