"""Conversational replies during guided showcase (customer questions)."""

import asyncio
import json
import logging

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import (
    COMPANY,
    EVENT_TYPE_DETAILS,
    SOCIAL_PROOF,
    WEBSITE_URL,
    build_agent_context,
)
from app.services.session_store import ConversationSession

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
        )
    )


def customer_is_asking(text: str) -> bool:
    if customer_wants_to_proceed(text):
        return False
    t = text.lower()
    if "?" in text:
        return True
    cues = (
        "how",
        "what",
        "when",
        "where",
        "why",
        "price",
        "cost",
        "charge",
        "menu",
        "many",
        "detail",
        "work",
        "done",
        "experience",
        "photo",
        "image",
        "sample",
        "portfolio",
        "review",
        "rating",
        "capacity",
        "guest",
        "veg",
        "pure",
    )
    return any(c in t for c in cues)


def _fallback_answer(session: ConversationSession, user_text: str) -> str:
    name = session.fields.customer_name or "there"
    event = session.fields.event_type or "celebrations"
    details = EVENT_TYPE_DETAILS.get(event, EVENT_TYPE_DETAILS["General"])
    t = user_text.lower()

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

    if any(w in t for w in ("menu", "dish", "food", "cuisine", "veg")):
        return (
            "We serve *100% pure vegetarian* food — South Indian, North Indian, Chinese, snacks, desserts, "
            "and live counters. Menus are tailored to your function.\n\n"
            "After your enquiry we also note your preferred cuisine styles. "
            "Reply *ok* when ready, or ask another question."
        )

    return (
        f"Happy to help, *{name}*! Our team at *{COMPANY['brand_name']}* focuses on hygienic pure-veg catering "
        f"with a personal touch from {COMPANY['managing_director']}.\n\n"
        f"You are planning *{event}* — {details['description']}\n\n"
        f"See more: {WEBSITE_URL}\n\n"
        "What would you like to know? Or reply *ok* when you are ready for us to collect event date & call time."
    )


def _call_gemini_qa(session: ConversationSession, user_text: str) -> str:
    genai.configure(api_key=settings.gemini_api_key)
    event = session.fields.event_type or "event"
    name = session.fields.customer_name or "the customer"
    context = build_agent_context()

    prompt = f"""You are a warm SRIVATSANKA catering consultant on WhatsApp chatting with {name}.
They are interested in: {event}

{context}

The customer asked: "{user_text}"

Reply in 2-4 short WhatsApp paragraphs. Answer their question using the company knowledge above.
Be specific and reassuring. Do NOT ask for event date yet.
End by inviting more questions OR reply *ok* when ready to share event date and callback time.
Do not use JSON — plain text only."""

    model = genai.GenerativeModel(settings.gemini_model)
    response = model.generate_content(prompt)
    return (response.text or "").strip()[:2000]


async def answer_showcase_question(session: ConversationSession, user_text: str) -> str:
    session.history.append({"role": "user", "content": user_text})

    if not settings.gemini_api_key or settings.gemini_api_key.startswith("paste-your"):
        reply = _fallback_answer(session, user_text)
    else:
        try:
            reply = await asyncio.to_thread(_call_gemini_qa, session, user_text)
        except Exception:
            logger.exception("Showcase Q&A failed")
            reply = _fallback_answer(session, user_text)

    session.history.append({"role": "assistant", "content": reply})
    return reply
