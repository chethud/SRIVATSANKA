"""Conversational replies during guided WhatsApp enquiry (Gemini + website knowledge)."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    POPULAR_DISHES,
    WEBSITE_URL,
    match_service_key,
    service_answer,
    short_services_reply,
)
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
    event = session.fields.event_type or "celebration"
    occasion = event if event != "General" else "celebration"
    t = user_text.lower()
    hint = natural_continue_hint(event_type=session.fields.event_type)

    if sharing_photos or customer_wants_photos(user_text):
        return f"Sure — sharing a few photos from our site 👇 {hint}"

    service_key = match_service_key(user_text)
    if service_key:
        return service_answer(service_key)

    if any(w in t for w in ("company", "about", "who are", "your team", "srivatsanka", "kannan")):
        return (
            f"We're *{COMPANY['brand_name']}* — catering & celebration services in Bengaluru "
            f"since {COMPANY['established']}. More at {WEBSITE_URL}"
        )

    if any(w in t for w in ("eat rep", "eat repeat", "restaurant", "dining")):
        return (
            f"That's *Eat Rep Eat* — our vegetarian experience center at N R Colony. "
            f"Hours {COMPANY['eat_rep_eat_hours']}. {COMPANY['eat_rep_eat_url']}"
        )

    if any(w in t for w in ("how many", "work", "done", "experience", "portfolio", "1000")):
        return f"We've supported many celebrations in Bengaluru, including large gatherings (1000+). {hint}"

    if any(w in t for w in ("price", "cost", "charge", "budget", "rate", "quote")):
        return (
            f"Pricing depends on menu & guest count for your {occasion.lower()} — "
            f"easiest on a quick call. {hint}"
        )

    if any(w in t for w in ("menu", "dish", "food", "cuisine", "veg", "live counter", "live station")):
        dishes = ", ".join(POPULAR_DISHES[:3])
        return f"Fully vegetarian — {dishes}, plus live counters. {hint}"

    if any(w in t for w in ("contact", "phone", "number", "email", "address", "location of")):
        return f"Call {COMPANY['phone']} or email {COMPANY['email']}. We're at {COMPANY['address']}."

    if "service" in t or "offer" in t or "what do you" in t:
        return short_services_reply()

    return f"Happy to help, *{name}*! {hint}"


async def _gemini_or_fallback(
    session: ConversationSession,
    user_text: str,
    *,
    next_detail_prompt: str | None = None,
    sharing_photos: bool = False,
) -> str:
    if not is_gemini_configured():
        logger.warning("GEMINI_API_KEY not set — using website knowledge reply for: %s", user_text[:80])
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
