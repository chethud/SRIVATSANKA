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


def extract_name(text: str) -> str:
    """Pull a name from casual WhatsApp phrasing."""
    t = text.strip()
    for pat in (
        r"(?:i'?m|i am|my name is|this is|call me|it's|its)\s+([A-Za-z][A-Za-z\s'.-]{0,40})",
        r"^(?:hi|hello|hey|hii)[,!\s]+(?:i'?m|i am|this is)?\s*([A-Za-z][A-Za-z'.-]{1,30}(?:\s+[A-Za-z][A-Za-z'.-]{1,30})?)",
        r"^([A-Za-z][A-Za-z\s'.-]{1,40}),?\s+(?:here|speaking)",
    ):
        m = re.search(pat, t, re.I)
        if m:
            name = m.group(1).strip().strip(".,").title()
            if name.lower() not in GREETING_ONLY and len(name) >= 2:
                return name[:80]
    words = [w.strip(".,!") for w in t.split() if w.strip(".,!")]
    if 1 <= len(words) <= 3 and all(w.isalpha() or "'" in w for w in words):
        joined = " ".join(words)
        if joined.lower() not in GREETING_ONLY and not is_greeting_only(joined):
            return joined.title()[:80]
    if len(words) == 1 and len(t) >= 2 and t.lower() not in GREETING_ONLY:
        return t[:80]
    return ""


def natural_continue_hint(*, event_type: str | None = None) -> str:
    return continue_hint(event_type=event_type)
