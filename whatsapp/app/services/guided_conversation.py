"""Conversational replies during guided WhatsApp enquiry (Gemini + website knowledge)."""

import logging
import random

from app.data.company_knowledge import (
    COMPANY,
    POPULAR_DISHES,
    match_service_key,
    service_answer,
    short_services_reply,
)
from app.services.conversation_turns import customer_wants_to_proceed, natural_continue_hint
from app.services.gemini_conversation import (
    generate_details_phase_reply,
    generate_showcase_reply,
    is_gemini_configured,
    looks_like_leaked_prompt,
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


def _wants_more_info(text: str) -> bool:
    from app.services.human_style import wants_more_info

    return wants_more_info(text)


def _more_info_reply(session: ConversationSession) -> str:
    occasion = (session.fields.event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"
    # No open follow-up question here — caller asks the next planning field.
    return random.choice(
        (
            f"For your {occasion}, we handle catering, décor, pooja setup, venue help, "
            f"and guest hospitality, all pure veg.",
            f"Sure, we cover food, décor, rituals, venues, and hospitality for your {occasion}.",
            f"Of course. End-to-end {occasion} support: catering, décor, pooja, and venues.",
        )
    )


def _food_reply(session: ConversationSession) -> str:
    occasion = (session.fields.event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"
    dishes = ", ".join(POPULAR_DISHES[:3])
    # No open follow-up question here — caller asks the next planning field.
    return random.choice(
        (
            f"For food, we do pure-veg South Indian menus across Karnataka, Andhra, Tamil Nadu, and Kerala styles, "
            f"with live counters too.",
            f"Happy to focus on food, authentic vegetarian catering for your {occasion}, including {dishes}.",
            f"Sure, food is our main strength. Custom pure-veg menus and live stations for your {occasion}.",
        )
    )


def _fallback_answer(
    session: ConversationSession,
    user_text: str,
    *,
    sharing_photos: bool = False,
) -> str:
    from app.services.human_style import normalize_customer_text

    name = session.fields.customer_name or "there"
    event = session.fields.event_type or "celebration"
    occasion = event if event != "General" else "celebration"
    t = normalize_customer_text(user_text)
    hint = natural_continue_hint(event_type=session.fields.event_type)

    if sharing_photos or customer_wants_photos(user_text):
        return "Sure, sharing a few photos from our site 👇"

    # Focus on the topic they asked about
    if any(w in t for w in ("food", "menu", "dish", "cuisine", "veg", "live counter", "live station", "cater")):
        return _food_reply(session)

    if _wants_more_info(user_text):
        return _more_info_reply(session)

    service_key = match_service_key(user_text)
    if service_key:
        return service_answer(service_key)

    if any(w in t for w in ("company", "about", "who are", "your team", "srivatsanka", "kannan")):
        return (
            f"We're {COMPANY['legal_name']}, catering & celebration services in Bengaluru "
            f"since {COMPANY['established']}. Happy to tell you more."
        )

    if any(w in t for w in ("eat rep", "eat repeat", "restaurant", "dining")):
        return (
            f"That's Eat Rep Eat, our vegetarian experience center at N R Colony. "
            f"Open {COMPANY['eat_rep_eat_hours']}."
        )

    if any(w in t for w in ("how many", "work", "done", "experience", "portfolio", "1000")):
        return f"We've supported many celebrations in Bengaluru, including large gatherings (1000+). {hint}"

    if any(w in t for w in ("price", "cost", "charge", "budget", "rate", "quote")):
        return (
            f"Pricing depends on menu & guest count for your {occasion.lower()}, "
            f"easiest on a quick call. {hint}"
        )

    if any(w in t for w in ("contact", "phone", "number", "email", "address", "location of")):
        return f"You can call {COMPANY['phone']} or email {COMPANY['email']}."

    if "service" in t or "offer" in t or "what do you" in t:
        return short_services_reply()

    # Ultimate generic: JSON pack line (generic.noted_continue) so nothing goes out of the box.
    from app.services import reply_pack

    packed = reply_pack.get_reply(
        "generic.noted_continue",
        name=session.fields.customer_name,
        event_type=session.fields.event_type,
    )
    if packed:
        return f"{packed} {hint}".strip()
    return f"Happy to help, {name}! {hint}"


async def _gemini_or_fallback(
    session: ConversationSession,
    user_text: str,
    *,
    next_detail_prompt: str | None = None,
    sharing_photos: bool = False,
) -> str:
    """JSON-first open-question answer.

    Scripted / website-knowledge replies (in-box) are tried first. Gemini is only
    reached when no scripted answer matches. Any Gemini failure, empty output, or
    leaked-prompt output degrades to the JSON pack (generic.noted_continue) via
    _fallback_answer, so the bot never goes out of the box. Callers always append
    the current slot question after this reply.
    """
    # Prefer a solid website-based reply for "know more" / topic asks (typos included)
    from app.services.human_style import normalize_customer_text

    norm = normalize_customer_text(user_text)
    if not sharing_photos and (
        _wants_more_info(user_text)
        or any(w in norm for w in ("food", "menu", "decor", "décor", "pooja", "venue"))
    ):
        if any(w in norm for w in ("food", "menu", "dish", "cuisine", "veg", "cater")):
            return _food_reply(session)
        if _wants_more_info(user_text):
            return _more_info_reply(session)

    if not is_gemini_configured():
        logger.warning("GEMINI_API_KEY not set; using website knowledge reply for: %s", user_text[:80])
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
        reply = trim_whatsapp_reply(reply)
        if not reply or looks_like_leaked_prompt(reply):
            logger.warning("Rejected bad Gemini reply for: %s", user_text[:80])
            return _fallback_answer(session, user_text, sharing_photos=sharing_photos)
        return reply
    except Exception:
        logger.exception("Gemini conversation failed for message: %s", user_text[:80])
        return _fallback_answer(session, user_text, sharing_photos=sharing_photos)


async def answer_showcase_question(
    session: ConversationSession,
    user_text: str,
    *,
    sharing_photos: bool = False,
) -> str:
    # History is recorded by the caller via record_exchange (avoid duplicates).
    reply = await _gemini_or_fallback(
        session,
        user_text,
        sharing_photos=sharing_photos or customer_wants_photos(user_text),
    )
    return reply


async def answer_details_question(
    session: ConversationSession,
    user_text: str,
    next_detail_prompt: str | None,
) -> str:
    # History is recorded by the caller via record_exchange (avoid duplicates).
    reply = await _gemini_or_fallback(
        session,
        user_text,
        next_detail_prompt=next_detail_prompt,
        sharing_photos=customer_wants_photos(user_text),
    )
    return reply
