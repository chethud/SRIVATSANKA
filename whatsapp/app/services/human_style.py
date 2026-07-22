"""Human-like WhatsApp consultant voice — short, natural chat copy."""

from __future__ import annotations

import random
import re

from app.data.company_knowledge import COMPANY

# Injected into Gemini system prompts (highest priority for tone + length).
HUMAN_CONSULTANT_STYLE = f"""# SHORT & NATURAL RESPONSE STYLE (HIGHEST PRIORITY)

You are an experienced celebration consultant for {COMPANY['legal_name']} on WhatsApp
(catering, décor, rituals, venues, and guest hospitality).
Always introduce the company using the full name \"Srivatsanka Events & Services\".
Every reply must feel like a real human WhatsApp chat — never a chatbot or support script.

## LENGTH (STRICT)
- Ideal: 1–3 short sentences.
- Most replies: under 40 words.
- Greeting: 10–20 words. Simple answer: 5–20 words. Answer + next question: 15–35 words.
- Longer only if they ask for detailed info (still under ~100 words).
- No long paragraphs. No walls of text. Do not dump lists of services unless asked.

## UNDERSTAND → ACKNOWLEDGE → ANSWER → CONTINUE
1. Read carefully and understand first.
2. Acknowledge what they said (briefly).
3. Answer any questions (if they asked several, answer ALL briefly).
4. Only then continue the enquiry if needed — one short question max.

Never jump to the next question without acknowledging them.
Never re-greet every turn. Never repeat info they already know.
Use "your wedding" (etc.) once known — not generic "event".

## VOICE
Write like WhatsApp: simple everyday language. Vary wording — never the same phrase every turn.
Prefer: Got it. / Sounds good. / Absolutely. / Certainly. / No problem. / Happy to help. /
Of course. / Perfect. / Great. / Thanks for sharing. / I understand. / That sounds wonderful. / No worries.

Never say: "Thank you for contacting…", "Kindly provide", "Your information has been recorded",
"Please wait while I process", "I am an AI", "Input received", "delighted to assist you with your enquiry".

If a short answer is enough, stop. At most one emoji, only if it fits.
Never claim to be a bot or AI.
"""


THANKS_ONLY = frozenset(
    {
        "thanks",
        "thank you",
        "thank u",
        "thx",
        "ty",
        "thankyou",
        "thanks!",
        "thank you!",
    }
)

UNDECIDED_CUES = (
    "still deciding",
    "not sure",
    "not decided",
    "haven't decided",
    "havent decided",
    "maybe later",
    "thinking about",
    "just looking",
    "just browsing",
    "will decide",
    "undecided",
)

SMALL_TALK_CUES = (
    "how are you",
    "how's it going",
    "how r you",
    "good morning",
    "good evening",
    "good afternoon",
)


def is_thanks_only(text: str) -> bool:
    t = text.lower().strip().rstrip("!.,")
    return t in THANKS_ONLY or t.startswith("thank") and len(t) < 24


def is_undecided(text: str) -> bool:
    t = text.lower()
    return any(c in t for c in UNDECIDED_CUES)


def is_small_talk(text: str) -> bool:
    t = text.lower().strip()
    return any(c in t for c in SMALL_TALK_CUES) or t in {"how are you?", "how are you"}


def soft_ack() -> str:
    return random.choice(
        (
            "Got it.",
            "Sounds good.",
            "Absolutely.",
            "Certainly.",
            "Sure.",
            "Of course.",
            "No problem.",
            "Happy to help.",
            "Perfect.",
            "Great.",
            "No worries.",
            "Thanks for sharing.",
            "I understand.",
        )
    )


def thanks_reply() -> str:
    return random.choice(
        (
            "You're welcome!",
            "Anytime 🙂",
            "Happy to help!",
            "My pleasure!",
        )
    )


def undecided_reply() -> str:
    return random.choice(
        (
            "No problem — take your time. Happy to answer any questions.",
            "No rush at all. Ask me anything about our catering.",
            "Of course. We're here whenever you're ready.",
        )
    )


def small_talk_reply(*, event_label: str | None = None) -> str:
    occasion = (event_label or "your celebration").lower()
    return random.choice(
        (
            f"Doing well, thanks! How can I help with {occasion}?",
            f"Great, thanks for asking 🙂 What would you like to know?",
        )
    )


def welcome_message() -> str:
    brand = COMPANY["legal_name"]
    return random.choice(
        (
            f"Hi! Welcome to {brand} 😊\nMay I know your name?",
            f"Hello! You've reached {brand}. What's your name?",
            f"Hi there — {brand} here. Who am I speaking with?",
        )
    )


def acknowledge_opening_without_name(text: str, event_type: str | None) -> str:
    """First message shared occasion/details but no name — short ack, then ask name."""
    from app.data.company_knowledge import is_known_event_type

    brand = COMPANY["legal_name"]
    if is_known_event_type(event_type):
        label = event_type.lower()  # type: ignore[union-attr]
        return random.choice(
            (
                f"That sounds wonderful! Happy to help with your {label}.\nMay I know your name?",
                f"Lovely — we can help with your {label}. What's your name?",
                f"Great! What's your name?",
            )
        )
    return random.choice(
        (
            f"Hi! Welcome to {brand} 🙂 May I know your name?",
            f"Hello from {brand}! What's your name?",
            f"Hi there — {brand} here. Who am I speaking with?",
        )
    )


def detail_question(field_key: str, *, event_type: str | None = None) -> str:
    """Short, varied enquiry questions."""
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"

    if field_key == "event_date":
        return random.choice(
            (
                f"When is your {occasion} planned?",
                f"When's the {occasion}?",
                f"What date works for your {occasion}?",
            )
        )
    if field_key == "event_location":
        return random.choice(
            (
                "Which area in Bengaluru is the venue?",
                "Where in Bengaluru will it be held?",
                "Which part of Bengaluru is the venue in?",
            )
        )
    if field_key == "preferred_callback":
        return random.choice(
            (
                "When's a good time for a quick call?",
                "What time should we call you?",
                "When works for a short callback?",
            )
        )
    return "Could you share a bit more?"


def acknowledge_field(field_key: str, value: str, *, event_type: str | None = None) -> str:
    """Short content-aware acknowledgement."""
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"
    v = value.strip()
    # Keep acknowledgements tiny — often just soft_ack or a few words
    if field_key == "event_date":
        return random.choice(
            (
                "Got it.",
                f"Perfect — {v}.",
                f"Thanks for sharing your {occasion} date.",
                "That sounds wonderful.",
            )
        )
    if field_key == "event_location":
        return random.choice(
            (
                f"Got it — {v}.",
                "Sounds good.",
                f"Perfect, {v}.",
                "Thanks!",
            )
        )
    if field_key == "preferred_callback":
        return random.choice(
            (
                f"Perfect — {v}.",
                "Sounds good.",
                "Absolutely.",
                "Got it.",
            )
        )
    return soft_ack()


def natural_field_ack(
    field_key: str,
    value: str,
    next_prompt: str,
    *,
    event_type: str | None = None,
) -> str:
    ack = acknowledge_field(field_key, value, event_type=event_type)
    if random.random() < 0.5:
        return f"{ack}\n{next_prompt}"
    return f"{ack} {next_prompt}"


def continue_hint(*, event_type: str | None = None) -> str:
    return random.choice(
        (
            "Any questions?",
            "Want to know anything, or shall we note a few details?",
            "Happy to answer questions — or we can continue when you're ready.",
        )
    )


def looks_like_polite_filler(text: str) -> bool:
    t = text.lower().strip().rstrip("!.,")
    return t in {
        "ok",
        "okay",
        "k",
        "kk",
        "sure",
        "fine",
        "alright",
        "all right",
        "cool",
        "great",
        "nice",
        "hmm",
        "hm",
    } or bool(re.fullmatch(r"o+k+", t))
