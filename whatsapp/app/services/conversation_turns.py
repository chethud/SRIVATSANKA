"""Shared helpers for natural WhatsApp conversation turns."""

import re

from app.services.human_style import (
    continue_hint,
    natural_field_ack,
    soft_ack,
)
from app.services.session_store import ConversationSession

# Re-export for existing imports
__all__ = [
    "GREETING_ONLY",
    "READY_PHRASES",
    "record_exchange",
    "is_greeting_only",
    "customer_wants_to_proceed",
    "clean_person_name",
    "extract_name",
    "natural_field_ack",
    "natural_continue_hint",
    "soft_ack",
]

GREETING_ONLY = frozenset(
    {"hi", "hello", "hey", "hii", "hiii", "namaste", "vanakkam", "start", "help", "good morning", "good evening"}
)

READY_PHRASES = (
    "ok",
    "okay",
    "yes",
    "yeah",
    "yep",
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
    "sure",
    "cool",
    "great",
    "perfect",
    "alright",
    "no doubts",
    "nothing else",
)


def record_exchange(session: ConversationSession, user_text: str, reply: str) -> None:
    """Keep full chat history so Gemini understands prior turns."""
    session.history.append({"role": "user", "content": user_text})
    session.history.append({"role": "assistant", "content": reply})


def is_greeting_only(text: str) -> bool:
    t = text.lower().strip().rstrip("!.,")
    return t in GREETING_ONLY or (len(t) <= 4 and t in {"hi", "hey"})


def customer_wants_to_proceed(text: str) -> bool:
    from app.services.human_style import wants_more_info, wants_to_move_further, normalize_customer_text

    if wants_more_info(text):
        return False
    if wants_to_move_further(text):
        return True
    t = normalize_customer_text(text).rstrip("!.,")
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
            "we can continue",
            "let us continue",
            "share details",
            "move further",
        )
    )


NAME_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "am",
        "call",
        "from",
        "hello",
        "hey",
        "hi",
        "hii",
        "hiii",
        "here",
        "i",
        "im",
        "i'm",
        "is",
        "its",
        "it's",
        "me",
        "my",
        "name",
        "namaste",
        "speaking",
        "the",
        "this",
        "vanakkam",
    }
)

NAME_INTRO_PATTERNS = (
    r"^(?:(?:hi|hello|hey|hii|hiii|namaste|vanakkam)[,!\s]+)+",
    r"^(?:(?:my|the)\s+)?name\s+is\s+",
    r"^(?:i'?m|i am|this is|call me|it'?s|its)\s+",
)

NAME_TRAILING_SPLIT = re.compile(
    r"\b(planning|looking|need|want|for|wedding|engagement|reception|birthday|housewarming|upanayanam|seemantham|baby shower)\b",
    re.I,
)


def clean_person_name(text: str) -> str:
    """Strip intro phrases and stop words; return a title-cased personal name."""
    t = (text or "").strip().strip(".,!?")
    if not t:
        return ""
    for _ in range(4):
        prev = t
        for pat in NAME_INTRO_PATTERNS:
            t = re.sub(pat, "", t, flags=re.I).strip()
        if t == prev:
            break
    t = NAME_TRAILING_SPLIT.split(t, maxsplit=1)[0].strip(" ,.-")
    words = [w.strip(".,!'\"()") for w in t.split() if w.strip(".,!'\"()")]
    words = [w for w in words if w.lower() not in NAME_STOP_WORDS]
    if not words:
        return ""
    if len(words) > 4:
        words = words[:4]
    return " ".join(words).title()[:80]


def extract_name(text: str) -> str:
    """Pull a name from casual WhatsApp phrasing. Never treat questions as names."""
    from app.services.gemini_conversation import looks_like_question
    from app.services.human_style import wants_more_info

    t = text.strip()
    if not t:
        return ""
    if looks_like_question(t) or wants_more_info(t):
        return ""
    if "?" in t:
        return ""

    # Never treat polite fillers / intents as a personal name
    reject_names = {
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "namaste",
        "vanakkam",
        "start",
        "help",
        "yes",
        "ok",
        "okay",
        "sure",
        "no",
        "skip",
        "none",
        "new",
        "reset",
        "restart",
        "thanks",
        "thank you",
        "good morning",
        "good evening",
        "good afternoon",
        "see",
        "pics",
        "pic",
        "photo",
        "photos",
        "pictures",
        "picture",
        "gallery",
        "images",
        "image",
        "showcase",
        "setups",
        "portfolio",
        "samples",
        "plan",
        "planning",
    }
    for pat in (
        r"(?:my\s+)?name\s+is\s+([A-Za-z][A-Za-z'.-]{1,30}(?:\s+[A-Za-z][A-Za-z'.-]{1,30}){0,2})",
        r"(?:i'?m|i am|this is|call me|it'?s|its)\s+([A-Za-z][A-Za-z'.-]{1,30}(?:\s+[A-Za-z][A-Za-z'.-]{1,30}){0,2})",
        r"^(?:hi|hello|hey|hii)[,!\s]+(?:my\s+)?name\s+is\s+([A-Za-z][A-Za-z'.-]{1,30}(?:\s+[A-Za-z][A-Za-z'.-]{1,30}){0,2})",
        r"^(?:hi|hello|hey|hii)[,!\s]+(?:i'?m|i am|this is|call me)\s+([A-Za-z][A-Za-z'.-]{1,30}(?:\s+[A-Za-z][A-Za-z'.-]{1,30}){0,2})",
        r"^([A-Za-z][A-Za-z'.-]{1,30}(?:\s+[A-Za-z][A-Za-z'.-]{1,30}){0,2}),?\s+(?:here|speaking)",
    ):
        m = re.search(pat, t, re.I)
        if m:
            name = clean_person_name(m.group(1))
            if name and name.lower() not in GREETING_ONLY and name.lower() not in reject_names and len(name) >= 2:
                return name

    if re.search(r"\b(my\s+name\s+is|name\s+is|i\s+am|i'?m|this\s+is|call\s+me)\b", t, re.I):
        name = clean_person_name(t)
        if name and name.lower() not in GREETING_ONLY and name.lower() not in reject_names and len(name) >= 2:
            return name

    words = [w.strip(".,!") for w in t.split() if w.strip(".,!")]
    # Reject sentence-like or intent-heavy messages
    intent_words = {
        "planning",
        "looking",
        "need",
        "want",
        "wedding",
        "birthday",
        "catering",
        "decor",
        "venue",
        "price",
        "cost",
        "menu",
        "food",
        "events",
        "services",
        "pics",
        "pic",
        "photos",
        "photo",
        "pictures",
        "gallery",
        "images",
        "showcase",
        "portfolio",
        "setups",
        "see",
    }
    if any(w.lower() in intent_words for w in words):
        # Still allow "I am Tejasvi planning a wedding" via regex above
        if not re.search(r"\b(i'?m|i am|my name is|name is|this is|call me)\b", t, re.I):
            return ""
    filtered = [w for w in words if w.lower() not in NAME_STOP_WORDS]
    if 1 <= len(filtered) <= 3 and all(w.isalpha() or "'" in w for w in filtered):
        joined = clean_person_name(" ".join(filtered))
        if (
            joined
            and joined.lower() not in GREETING_ONLY
            and joined.lower() not in reject_names
            and not is_greeting_only(joined)
        ):
            return joined
    if len(filtered) == 1 and len(filtered[0]) >= 2 and filtered[0].lower() not in GREETING_ONLY and filtered[0].lower() not in reject_names:
        if filtered[0].isdigit():
            return ""
        return clean_person_name(filtered[0])
    return ""


def natural_continue_hint(*, event_type: str | None = None) -> str:
    return continue_hint(event_type=event_type)
