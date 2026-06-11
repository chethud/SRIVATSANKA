"""Gemini-powered WhatsApp conversation replies with chat history."""

import asyncio
import logging
import re

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import COMPANY, build_agent_context
from app.services.session_store import ConversationSession

logger = logging.getLogger(__name__)

PLACEHOLDER_KEYS = ("paste-your", "your-gemini-api-key", "changeme")


def is_gemini_configured() -> bool:
    key = (settings.gemini_api_key or "").strip()
    if not key or len(key) < 10:
        return False
    lower = key.lower()
    return not any(p in lower for p in PLACEHOLDER_KEYS)


def _build_chat_history(session: ConversationSession) -> list[dict]:
    """History for Gemini chat — excludes the latest user turn (sent separately)."""
    history: list[dict] = []
    for msg in session.history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    return history


def _generate_reply(system_instruction: str, session: ConversationSession, user_text: str) -> str:
    genai.configure(api_key=settings.gemini_api_key)
    models = [settings.gemini_model.strip(), "gemini-2.0-flash", "gemini-2.5-flash", "gemini-flash-latest"]
    seen: set[str] = set()
    last_error: Exception | None = None

    for model_name in models:
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
                generation_config=genai.GenerationConfig(temperature=0.72),
            )
            chat = model.start_chat(history=_build_chat_history(session))
            response = chat.send_message(user_text)
            text = (response.text or "").strip()
            if not text:
                raise ValueError("Empty Gemini response")
            return text[:2000]
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini model %s failed: %s", model_name, exc)

    if last_error:
        raise last_error
    raise ValueError("No Gemini model available")


def _showcase_system(session: ConversationSession, *, sharing_photos: bool = False) -> str:
    name = session.fields.customer_name or "the customer"
    event = session.fields.event_type or "their celebration"
    context = build_agent_context()
    photo_note = (
        "\nIMPORTANT: The customer asked for photos. Our system is sending WhatsApp gallery images from "
        "past events right now. Acknowledge that you are sharing them — do not redirect only to the website."
        if sharing_photos
        else ""
    )
    return f"""You are a warm, experienced catering consultant for {COMPANY['brand_name']} on WhatsApp.
You represent {COMPANY['legal_name']} — pure vegetarian catering in Bengaluru since {COMPANY['established']}.
Speak as part of {COMPANY['managing_director']}'s team. Never say you are a bot or AI.

You are chatting with *{name}* who is planning *{event}*.

{context}

HOW TO REPLY
- Read the customer's message carefully and answer their specific question first.
- Use company knowledge above — be concrete (menus, hygiene, experience, wedding spreads, live counters, popular dishes, etc.).
- When they ask for photos, pictures, or past events: confirm you are sharing real photos from our gallery on WhatsApp right now (images arrive separately). Do NOT say you cannot share photos here.
- Sound natural and human: 2–4 short WhatsApp paragraphs, light emoji only if natural.
- Use *bold* sparingly for key phrases.
- Do NOT ask for event date, venue, or callback time yet unless they ask what information you need next.
- End by inviting another question OR reply *ok* when they are ready to share event date and callback time.
- Plain text only — no JSON, no bullet lists longer than 4 items.{photo_note}"""


def _collect_details_system(session: ConversationSession, next_prompt: str | None) -> str:
    name = session.fields.customer_name or "the customer"
    event = session.fields.event_type or "their celebration"
    context = build_agent_context()
    pending = next_prompt or "remaining event details"
    collected = session.fields.model_dump()
    return f"""You are a warm catering consultant for {COMPANY['brand_name']} on WhatsApp, helping *{name}* with *{event}*.

{context}

We are collecting enquiry details. Already noted: {collected}
Still need from the customer: {pending}

If they ask a question, answer it clearly using company knowledge, then gently remind them what detail we still need.
Do NOT invent or assume dates, venues, or callback times they have not given.
Keep replies short and friendly. Plain text only."""


async def generate_showcase_reply(
    session: ConversationSession,
    user_text: str,
    *,
    sharing_photos: bool = False,
) -> str:
    system = _showcase_system(session, sharing_photos=sharing_photos)
    return await asyncio.to_thread(_generate_reply, system, session, user_text)


async def generate_details_phase_reply(
    session: ConversationSession,
    user_text: str,
    next_prompt: str | None,
) -> str:
    system = _collect_details_system(session, next_prompt)
    return await asyncio.to_thread(_generate_reply, system, session, user_text)


def looks_like_question(text: str) -> bool:
    t = text.lower().strip()
    if "?" in text:
        return True
    cues = (
        "what ",
        "why ",
        "how do",
        "how does",
        "how many",
        "how much",
        "can you",
        "do you",
        "tell me",
        "more detail",
        "more about",
        "about your",
        "about the",
        "explain",
        "information",
        "your service",
        "your menu",
        "your price",
        "your cost",
    )
    return any(c in t for c in cues)


def _is_probable_date(text: str) -> bool:
    t = text.lower()
    if re.search(r"\d", text):
        return True
    months = (
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    )
    return any(m in t for m in months) or "tomorrow" in t or "next week" in t or "this weekend" in t


def _is_probable_callback(text: str) -> bool:
    t = text.lower()
    if re.search(r"\d{1,2}\s*(am|pm|:\d{2})", t):
        return True
    if re.search(r"\bin\s+\d+\s*(min|hour)", t):
        return True
    return any(
        w in t
        for w in (
            "today",
            "tomorrow",
            "morning",
            "evening",
            "afternoon",
            "noon",
            "call me",
            "tonight",
        )
    )


def is_likely_field_answer(text: str, field_key: str) -> bool:
    if looks_like_question(text):
        if field_key == "event_date" and _is_probable_date(text):
            return True
        if field_key == "preferred_callback" and _is_probable_callback(text):
            return True
        if field_key == "event_location" and len(text.strip()) > 4 and "?" not in text:
            # "Indiranagar" or "Whitefield area" — not a question
            if not text.lower().startswith(("what", "how", "why", "can", "do ", "tell")):
                return True
        return False
    return len(text.strip()) >= 2
