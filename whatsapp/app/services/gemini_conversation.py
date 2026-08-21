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
    """History for Gemini chat, excludes the latest user turn (sent separately)."""
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
    "requirements & tone",
    "requirements and tone",
    "your task",
    "short & natural",
    "understand before responding",
)


def looks_like_leaked_prompt(text: str) -> bool:
    """True if the model echoed internal instructions instead of a customer reply."""
    t = (text or "").strip()
    if not t or len(t) < 8:
        return True
    lower = t.lower()
    if any(m in lower for m in _LEAK_MARKERS):
        # If leak is only a trailing fragment after a real answer, sanitize() will trim it.
        # treat full-message leaks / short garbage as bad.
        first_line = lower.split("\n", 1)[0].strip()
        if any(m in first_line for m in _LEAK_MARKERS) or len(t) < 48:
            return True
    if re.match(r"^(rules|company|services|faqs|photos|legacy|about|requirements)\s*[:\*]", lower):
        return True
    if lower.startswith("rules") and len(t) < 40:
        return True
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
    text = re.sub(r"^#+\s*", "", text, flags=re.M)
    text = re.sub(r"\*\*+", "", text)
    text = re.sub(r"`+", "", text)
    # Kannan.rules.txt: never use em-dashes
    text = text.replace("—", ",").replace("–", ",")

    # Cut off any leaked instruction section, keep the human answer above it
    cut_patterns = (
        r"(?i)\n\s*requirements\s*&\s*tone\b.*",
        r"(?i)\n\s*requirements\s+and\s+tone\b.*",
        r"(?i)\n\s*rules\s*:?\s*\n.*",
        r"(?i)\n\s*your task\b.*",
        r"(?i)\n\s*reply guidance\b.*",
        r"(?i)\n\s*official website knowledge\b.*",
        r"(?i)\n\s*how you think\b.*",
    )
    for pat in cut_patterns:
        text = re.sub(pat, "", text, flags=re.S).strip()

    # Drop trailing orphan bullets / stars
    text = re.sub(r"\n\s*[\*\-•]+\s*$", "", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    # Soften robotic numbered pickers like "1. Lunch 2. Dinner"
    text = re.sub(r"(?m)^\s*\d+\.\s+", "", text)
    text = re.sub(r"\b(\d+)\.\s+(?=[A-Za-z])", r"\1) ", text)

    if looks_like_leaked_prompt(text):
        # Try keeping only the first 1–2 sentences if a leak marker appears later
        lower = text.lower()
        earliest = min(
            (lower.find(m) for m in _LEAK_MARKERS if m in lower),
            default=-1,
        )
        if earliest > 40:
            text = text[:earliest].strip().rstrip(":-*")
            text = re.sub(r"\n{2,}", "\n", text).strip()
            if looks_like_leaked_prompt(text):
                return ""
            return text
        return ""
    return text


def trim_whatsapp_reply(text: str, max_chars: int = 320) -> str:
    """Keep bot replies short, WhatsApp chat style."""
    text = sanitize_whatsapp_reply(text)
    if not text:
        return ""
    words = text.split()
    if len(words) > 60 and len(text) > max_chars:
        text = " ".join(words[:55]).rstrip(".,;") + "…"
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    for sep in (". ", ".\n", "! ", "? ", "\n"):
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
            # Steer the model away from dumping knowledge blocks.
            prompt = (
                f"Customer message:\n{user_text}\n\n"
                "Reply as a helpful WhatsApp consultant only. "
                "Plain short sentences only. No headings, no bullet dumps, no internal labels."
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
You work with {COMPANY['managing_director']}'s team.

Chatting with {name} about their {event}. Say "{event.lower()}" when natural.

{context}

{NATURAL_STYLE}

YOUR TASK
- Reply in short natural WhatsApp sentences only (never headings or labels).
- Keep it short unless they asked for detail.
- Answer ONLY from the website knowledge above.
- Acknowledge briefly, answer, then at most one gentle next step.
- Do NOT rush into date, venue, or callback unless they clearly want to continue.
- Do not assume the event is in Bengaluru or Bangalore. Always confirm the venue status and location explicitly.
- Custom / fusion / live counters: respond warmly and note it for the planner/chef call. Never reject restrictively.
- If they want to discuss on call, offer to schedule a callback instead of forcing more form questions.
- If they choose straight to planning, ask for the date only. Do not dump mandap/floral/menu showcase text.
- If ready, offer to note the date and venue details next in one short line.{photo_note}"""


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
- Short natural WhatsApp reply only, no headings or labels.
- Acknowledge what they said, then ask for: {pending}
- If they asked something else, answer briefly first.
- Custom / fusion / live counters: respond warmly and say you noted it for the planner/chef call. Never reject restrictively.
- If they want to discuss on call, pivot immediately to asking for the best callback time.
- If the event is today/tomorrow/within 7 days, prioritize an immediate senior callback and skip meal/theme questions.
- Meal lunch/dinner/high tea: only for birthdays or informal family gatherings.
- Guest ranges and relative dates must keep full context (e.g. "30 to 50", "3rd week of next month").
- Venue replies: acknowledge the clean place name only.
- Callback now/ASAP: say the lead planning team will call ASAP, never invent a timestamp.
- Do NOT invent dates, locations, or callback times.
- Do not assume the event is in Bengaluru or Bangalore. If asking for location, explicitly ask whether the venue is fixed and collect either venue name plus area or preferred city/locality.
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
    from app.services.human_style import normalize_customer_text, wants_more_info

    t = normalize_customer_text(text)
    if "?" in text:
        return True
    if wants_more_info(text):
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
        "share more",
        "about your event",
        "about events",
    )
    return any(c in t for c in cues)


def _is_probable_date(text: str) -> bool:
    """True only when the message actually looks like a date, not any digit (e.g. mor3)."""
    from app.services.event_date import looks_like_event_date

    return looks_like_event_date(text)


def is_likely_field_answer(text: str, field_key: str, *, last_asked_slot: str | None = None) -> bool:
    from app.services.human_style import has_callback_intent, is_meal_type_answer
    from app.services.event_date import has_service_planning_intent
    from app.services.human_style import wants_more_info, wants_showcase_look
    from app.services.website_gallery import customer_wants_photos

    if has_service_planning_intent(text):
        return False

    if wants_more_info(text):
        return False
    if field_key == "event_date" and (wants_showcase_look(text) or customer_wants_photos(text)):
        return False
    if looks_like_question(text):
        if field_key == "event_date" and _is_probable_date(text):
            return True
        if field_key == "preferred_callback" and _is_probable_callback(text, last_asked_slot=last_asked_slot):
            return True
        if field_key == "event_location" and _is_probable_location(text) and "?" not in text:
            return True
        return False
    if field_key == "event_date":
        return _is_probable_date(text)
    if field_key == "preferred_callback":
        return _is_probable_callback(text, last_asked_slot=last_asked_slot)
    if field_key == "guest_count":
        t = text.strip()
        if re.search(r"\b\d{1,2}(?:st|nd|rd|th)\b", t, re.I) and re.search(
            r"\b(week|month|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b",
            t,
            re.I,
        ):
            return False
        if re.search(r"\d+", t) and re.search(r"\b(guests?|people|pax|persons?)\b", t, re.I):
            return True
        if re.search(r"^\s*\d{1,5}(?:\s*(?:-|to|–|—)\s*\d{1,5})?\s*$", t, re.I):
            return True
        if any(w in t.lower() for w in ("hundred", "thousand", "pax", "people", "guests", "approx", "about", "around")):
            return bool(re.search(r"\d+", t)) or any(
                w in t.lower() for w in ("hundred", "thousand")
            )
        return False
    if field_key == "meal_preference":
        if is_meal_type_answer(text):
            return True
        t = text.lower()
        return any(
            w in t
            for w in (
                "lunch",
                "dinner",
                "breakfast",
                "snacks",
                "tea",
                "coffee",
                "meal",
                "food",
                "veg",
                "skip",
                "none",
            )
        )
    if field_key == "event_location":
        return _is_probable_location(text)
    return False


def _is_probable_location(text: str) -> bool:
    t = text.strip()
    if len(t) < 2 or len(t) > 80:
        return False
    if len(t.split()) > 10:
        return False
    lower = t.lower()
    if looks_like_question(t):
        return False
    # Guest-count answers must never be treated as venues
    if re.search(r"\b(guests?|people|pax|persons?)\b", lower) or re.search(
        r"^\s*\d{1,5}(?:\s*(?:-|to|–|—)\s*\d{1,5})?\s*$",
        lower,
    ):
        return False
    place_cues = (
        "venue",
        "hall",
        "home",
        "house",
        "apartment",
        "flat",
        "resort",
        "hotel",
        "temple",
        "bangalore",
        "bengaluru",
        "mysore",
        "mysuru",
        "chennai",
        "hyderabad",
        "area",
        "road",
        "layout",
        "nagar",
        "puram",
        "not fixed",
        "not yet",
        "undecided",
        "help",
        "suggest",
        "looking for venue",
    )
    if any(c in lower for c in place_cues):
        return True
    # Short place-like token(s), not a full sentence about something else
    if 1 <= len(t.split()) <= 5 and not re.search(
        r"\b(call|menu|food|decor|price|cost|photo|portfolio|guest|pax|people)\b",
        lower,
    ):
        return True
    return False


def _is_probable_callback(text: str, *, last_asked_slot: str | None = None) -> bool:
    from app.services.callback_time import IMMEDIATE_RE
    from app.services.human_style import asks_callback_timing, has_callback_intent, is_meal_type_answer

    if asks_callback_timing(text):
        return False

    if is_meal_type_answer(text) and last_asked_slot != "preferred_callback":
        return False

    t = text.lower()
    if IMMEDIATE_RE.search(t):
        return True
    if re.search(r"@?\s*\d{1,2}\s*(am|pm|:\d{2})", t):
        return True
    if re.search(r"\bin\s+\d+\s*(min|hour)", t):
        return True
    if re.search(r"\b(day after|tea time|weekend|after\s+\d|around\s+\d)\b", t):
        return True
    if re.search(r"\b(today|tomorrow)\s+(morning|afternoon|evening|night)\b", t):
        return True
    if last_asked_slot == "preferred_callback":
        return has_callback_intent(text) or bool(
            re.search(r"\b(morning|afternoon|evening|night|noon|tonight|anytime|whenever)\b", t)
        )
    return has_callback_intent(text) or bool(re.search(r"\btom\w*row\b", t))
