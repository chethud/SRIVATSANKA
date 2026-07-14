"""Gemini-powered WhatsApp conversation replies with chat history."""

import asyncio
import logging
import re

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import COMPANY, build_short_company_context
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


NATURAL_STYLE = """HOW YOU THINK AND REPLY
1. Read the customer's latest message carefully — understand what they mean, not just keywords.
2. Reply to that specific point first, in your own words (like a real person on WhatsApp).
3. Keep it warm and concise — 1–3 short sentences, under 320 characters.
4. One question at a time. No bullet lists, brochures, or copy-paste marketing.
5. Never say you are a bot or AI. At most one emoji, only if it fits naturally.
6. Match their tone — casual if they're casual, polite if they're formal."""


def trim_whatsapp_reply(text: str, max_chars: int = 320) -> str:
    """Keep bot replies concise — WhatsApp should feel like texting, not email."""
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    for sep in (". ", ".\n", "! ", "? ", " — ", "\n"):
        idx = chunk.rfind(sep)
        if idx > max_chars // 2:
            return chunk[: idx + len(sep.rstrip())].strip()
    return chunk.rstrip().rstrip(",") + "…"


def _generate_reply(system_instruction: str, session: ConversationSession, user_text: str) -> str:
    genai.configure(api_key=settings.gemini_api_key)
    primary = settings.gemini_model.strip() or "gemini-flash-latest"
    models = [primary, "gemini-2.0-flash"]
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
                generation_config=genai.GenerationConfig(temperature=0.7, max_output_tokens=180),
            )
            chat = model.start_chat(history=_build_chat_history(session))
            response = chat.send_message(user_text)
            text = (response.text or "").strip()
            if not text:
                raise ValueError("Empty Gemini response")
            return trim_whatsapp_reply(text[:2000])
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini model %s failed: %s", model_name, exc)

    if last_error:
        raise last_error
    raise ValueError("No Gemini model available")


def _showcase_system(session: ConversationSession, *, sharing_photos: bool = False) -> str:
    name = session.fields.customer_name or "the customer"
    event = session.fields.event_type or "their celebration"
    context = build_short_company_context()
    photo_note = (
        "\nThe customer asked for photos — our system is sending gallery images now. "
        "Briefly acknowledge that you're sharing them."
        if sharing_photos
        else "\nDo NOT send or mention sharing photos unless the customer explicitly asked."
    )
    return f"""You are a friendly human events consultant for {COMPANY['brand_name']} on WhatsApp.
You work with {COMPANY['managing_director']}'s team in Bengaluru.

Chatting with *{name}* about their *{event}*.

{context}

{NATURAL_STYLE}

RIGHT NOW
- Answer what they asked — pricing, menu, experience, photos, etc. — before anything else.
- Do NOT ask for date, venue, or callback unless they ask what you need next.
- If they seem ready to move on, you can gently mention you'll note date & location next.{photo_note}"""


def _collect_details_system(session: ConversationSession, next_prompt: str | None) -> str:
    name = session.fields.customer_name or "the customer"
    event = session.fields.event_type or "their celebration"
    context = build_short_company_context()
    pending = next_prompt or "remaining event details"
    collected = session.fields.model_dump()
    return f"""You are a friendly human events consultant for {COMPANY['brand_name']} on WhatsApp.

{context}

Helping *{name}* plan their *{event}*.
Already noted: {collected}
Still need from them: {pending}

{NATURAL_STYLE}

RIGHT NOW
- If they gave the detail we asked for, acknowledge it naturally.
- If they asked something else, answer that first — then gently ask for: {pending}
- Do NOT invent dates, locations, or callback times they didn't say."""


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
    return any(m in t for m in months) or "tomorrow" in t or "next week" in t or "this weekend" in t or "this month" in t or "next month" in t


def _is_probable_callback(text: str) -> bool:
    t = text.lower()
    if re.search(r"@?\s*\d{1,2}\s*(am|pm|:\d{2})", t):
        return True
    if re.search(r"\bin\s+\d+\s*(min|hour)", t):
        return True
    return any(
        w in t
        for w in (
            "today",
            "tomorrow",
            "tommarow",
            "tomorow",
            "morning",
            "evening",
            "afternoon",
            "noon",
            "call me",
            "tonight",
        )
    ) or bool(re.search(r"\btom\w*row\b", t))


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
