"""Gemini-powered WhatsApp conversation replies with chat history."""

import asyncio
import logging
import re

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import COMPANY, build_agent_context, build_short_company_context
from app.services.human_style import HUMAN_CONSULTANT_STYLE
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


NATURAL_STYLE = HUMAN_CONSULTANT_STYLE

_LEAK_MARKERS = (
    "official website knowledge",
    "reply guidance",
    "source of truth",
    "system prompt",
    "never invent",
    "base every company",
    "whatsapp capabilities",
    "already noted:",
    "still need from them",
    "right now\n",
    "how you think",
)


def looks_like_leaked_prompt(text: str) -> bool:
    """True if the model echoed internal instructions instead of a customer reply."""
    t = (text or "").strip()
    if not t or len(t) < 8:
        return True
    lower = t.lower()
    if any(m in lower for m in _LEAK_MARKERS):
        return True
    # Headings / markdown dumps
    if re.match(r"^(rules|company|services|faqs|photos|legacy|about)\s*[:\*]", lower):
        return True
    if lower.startswith("rules") and len(t) < 40:
        return True
    # Mostly punctuation / broken markdown
    letters = sum(1 for c in t if c.isalpha())
    if letters < 12:
        return True
    if t.count("*") >= 3 and letters < 40:
        return True
    return False


def sanitize_whatsapp_reply(text: str) -> str:
    """Clean model output for WhatsApp; empty string if unusable."""
    text = (text or "").strip()
    if not text:
        return ""
    # Drop fenced / heading noise
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*+", "", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if looks_like_leaked_prompt(text):
        return ""
    return text


def trim_whatsapp_reply(text: str, max_chars: int = 320) -> str:
    """Keep bot replies short — WhatsApp chat style."""
    text = sanitize_whatsapp_reply(text)
    if not text:
        return ""
    words = text.split()
    if len(words) > 60 and len(text) > max_chars:
        text = " ".join(words[:55]).rstrip(".,;") + "…"
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
                generation_config=genai.GenerationConfig(temperature=0.75, max_output_tokens=180),
            )
            chat = model.start_chat(history=_build_chat_history(session))
            # Steer the model away from dumping knowledge blocks
            prompt = (
                f"Customer message:\n{user_text}\n\n"
                "Reply as a helpful WhatsApp consultant only. "
                "Plain short sentences — no headings, no bullet dumps, no internal labels."
            )
            response = chat.send_message(prompt)
            text = trim_whatsapp_reply((response.text or "").strip()[:2000])
            if not text:
                raise ValueError("Unusable Gemini response")
            return text
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
        "\nThe customer asked for photos — gallery images are being shared with this reply. "
        "Acknowledge warmly that you're sharing a few photos (do not say 'system')."
        if sharing_photos
        else "\nDo NOT send or mention sharing photos unless the customer explicitly asked."
    )
    return f"""You are an experienced celebration consultant for {COMPANY['legal_name']} on WhatsApp
(catering, décor, pooja/rituals, venues, guest hospitality).
You work with {COMPANY['managing_director']}'s team in Bengaluru.

Chatting with {name} about their {event} — say "{event.lower()}" when natural.

{context}

{NATURAL_STYLE}

YOUR TASK
- Reply in short natural WhatsApp sentences only (never headings or labels).
- Keep it short unless they asked for detail.
- Answer ONLY from the website knowledge above.
- Acknowledge briefly, answer, then at most one gentle next step.
- Do NOT rush into date/venue/callback unless they clearly want to continue.
- If ready, offer to note date & venue next in one short line.{photo_note}"""


def _collect_details_system(session: ConversationSession, next_prompt: str | None) -> str:
    name = session.fields.customer_name or "the customer"
    event = session.fields.event_type or "their celebration"
    context = build_short_company_context()
    pending = next_prompt or "remaining event details"
    collected = session.fields.model_dump()
    return f"""You are an experienced celebration consultant for {COMPANY['legal_name']} on WhatsApp.

{context}

Helping {name} plan their {event} (say "{event.lower()}" when known).
Already shared: {collected}
Still helpful to know: {pending}

{NATURAL_STYLE}

YOUR TASK
- Short natural WhatsApp reply only — no headings or labels.
- Acknowledge what they said, then ask for: {pending}
- If they asked something else, answer briefly first.
- Do NOT invent dates, locations, or callback times.
"""


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
        "know more",
        "more detail",
        "more details",
        "more info",
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
