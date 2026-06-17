"""Shared helpers for natural WhatsApp conversation turns."""

import random
import re

from app.services.session_store import ConversationSession

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
            "we can continue",
            "let us continue",
            "share details",
        )
    )


def extract_name(text: str) -> str:
    """Pull a name from casual WhatsApp phrasing."""
    t = text.strip()
    for pat in (
        r"(?:i'?m|i am|my name is|this is|call me|it's|its)\s+([A-Za-z][A-Za-z\s'.-]{0,40})",
        r"^([A-Za-z][A-Za-z\s'.-]{1,40}),?\s+(?:here|speaking)",
    ):
        m = re.search(pat, t, re.I)
        if m:
            name = m.group(1).strip().strip(".,").title()
            if name.lower() not in GREETING_ONLY and len(name) >= 2:
                return name[:80]
    words = t.split()
    if len(words) == 1 and len(t) >= 2 and t.lower() not in GREETING_ONLY:
        return t[:80]
    return ""


def natural_field_ack(next_prompt: str) -> str:
    """Vary confirmations so replies feel human, not scripted."""
    lead = random.choice(
        (
            "Got it 👍",
            "Perfect, thanks.",
            "Noted —",
            "Sure thing.",
            "Thanks!",
        )
    )
    return f"{lead} {next_prompt}"


def natural_continue_hint() -> str:
    return random.choice(
        (
            "Ask me anything, or just say when you're ready to share the date and venue.",
            "Happy to answer questions — or tell me when you'd like to continue.",
            "Feel free to ask more, or we can move on to date & location whenever you're ready.",
        )
    )
