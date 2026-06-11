"""Conversational replies during guided WhatsApp enquiry (Gemini + fallback)."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    EVENT_TYPE_DETAILS,
    POPULAR_DISHES,
    SOCIAL_PROOF,
    WEBSITE_ABOUT,
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
        dishes = ", ".join(POPULAR_DISHES[:4])
        return (
            f"Of course, *{name}*! 🌿\n\n"
            "Sharing photos from past events we have catered — wedding spreads, live counters, "
            "and elegant pure-veg presentation.\n\n"
            f"For your *{event}*, we specialise in {dishes}, and more — all with Mr. Kannan's personal oversight.\n\n"
            f"Browse our full gallery anytime: {WEBSITE_URL}\n\n"
            "Ask anything else, or reply *ok* when you would like us to note your event date and callback time."
        )

    if any(w in t for w in ("how many", "work", "done", "events", "experience", "portfolio", "wedding")):
        proof = "\n".join(f"• {p}" for p in SOCIAL_PROOF[:4])
        return (
            f"Great question, *{name}*! 🌿\n\n"
            f"Since {COMPANY['established']}, our team has catered *hundreds of events* across Bengaluru — "
            f"weddings, receptions, house warmings, baby showers, and corporate functions.\n\n"
            f"{proof}\n\n"
            f"For *{details['title']}*, {details['description']}\n\n"
            f"More photos & reviews: {WEBSITE_URL}\n\n"
            "Ask anything else, or reply *ok* when you would like us to note your event date and callback time."
        )

    if any(w in t for w in ("price", "cost", "charge", "budget", "rate")):
        return (
            f"*{name}*, every {event} menu is customised for guest count, venue, and dishes — "
            "so pricing is shared on a call with our team, not as a fixed list here.\n\n"
            "We will discuss packages when we call you. Any other questions? "
            "Or reply *ok* to continue with your event details."
        )

    if any(w in t for w in ("menu", "dish", "food", "cuisine", "veg", "service")):
        dishes = ", ".join(POPULAR_DISHES[:5])
        return (
            f"We serve *100% pure vegetarian* food — {dishes}, snacks, desserts, and live counters.\n\n"
            f"{WEBSITE_ABOUT[:200]}…\n\n"
            "Reply *ok* when ready, or ask another question."
        )

    return (
        f"Happy to help, *{name}*! Our team at *{COMPANY['brand_name']}* focuses on hygienic pure-veg catering "
        f"with a personal touch from {COMPANY['managing_director']}.\n\n"
        f"You are planning *{event}* — {details['description']}\n\n"
        f"See more on our website: {WEBSITE_URL}\n\n"
        "What would you like to know? Or reply *ok* when you are ready for us to collect event date & call time."
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
