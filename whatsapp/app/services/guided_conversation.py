"""Conversational replies during guided WhatsApp enquiry (Gemini + fallback)."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    EVENT_TYPE_DETAILS,
    POPULAR_DISHES,
    WEBSITE_URL,
)
from app.services.gemini_conversation import (
    generate_details_phase_reply,
    generate_showcase_reply,
    is_gemini_configured,
    looks_like_question,
)
from app.services.session_store import ConversationSession
from app.services.website_gallery import customer_wants_photos

logger = logging.getLogger(__name__)

READY_PHRASES = (
    "ok",
    "okay",
    "yes",
    "ready",
    "proceed",
    "continue",
    "fine",
    "good",
    "done",
    "next",
    "no questions",
    "looks good",
    "sounds good",
    "let's go",
    "lets go",
    "go ahead",
    "move on",
    "that's all",
    "thats all",
)


def customer_wants_to_proceed(text: str) -> bool:
    t = text.lower().strip().rstrip("!.,")
    if t in READY_PHRASES:
        return True
    return any(
        phrase in t
        for phrase in (
            "no question",
            "no doubt",
            "all good",
            "i am ready",
            "im ready",
            "please continue",
            "take my detail",
            "note my detail",
            "share my detail",
        )
    )


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
    t = user_text.lower()

    if sharing_photos or customer_wants_photos(user_text):
        return (
            f"Sure, *{name}*! Sharing a few photos from past events now 👇\n\n"
            f"Ask anything else, or reply *ok* when you'd like us to note your date and call time."
        )

    if any(w in t for w in ("company", "about", "who are", "your team", "srivatsanka", "kannan")):
        return (
            f"We're *{COMPANY['brand_name']}* — pure veg catering in Bengaluru since {COMPANY['established']}, "
            f"led by {COMPANY['managing_director']}. Weddings, corporate & family events. "
            f"More at {WEBSITE_URL}\n\n"
            f"Anything else, or reply *ok* to continue?"
        )

    if any(w in t for w in ("how many", "work", "done", "events", "experience", "portfolio", "wedding")):
        return (
            f"We've catered hundreds of events across Bengaluru — weddings, receptions, house warmings & more. "
            f"For *{details['title']}*, {details['description'][:120]}…\n\n"
            f"Reply *ok* when ready, or ask another question."
        )

    if any(w in t for w in ("price", "cost", "charge", "budget", "rate")):
        return (
            f"Every menu is customised for your guest count and dishes — our team shares pricing on a call, "
            f"not as a fixed list here.\n\n"
            f"Reply *ok* to continue, or ask anything else."
        )

    if any(w in t for w in ("menu", "dish", "food", "cuisine", "veg", "service")):
        dishes = ", ".join(POPULAR_DISHES[:4])
        return (
            f"100% pure vegetarian — {dishes}, live counters & more.\n\n"
            f"Reply *ok* when ready, or ask another question."
        )

    return (
        f"Happy to help, *{name}*! We're {COMPANY['brand_name']} — hygienic pure-veg catering with a personal touch.\n\n"
        f"You're planning *{event}*. What would you like to know? Or reply *ok* when ready for date & call time."
    )


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
            return await generate_details_phase_reply(session, user_text, next_detail_prompt)
        return await generate_showcase_reply(
            session,
            user_text,
            sharing_photos=sharing_photos,
        )
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
