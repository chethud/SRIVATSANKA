"""Human-like WhatsApp consultant voice — shared rules + copy helpers."""

from __future__ import annotations

import random
import re

from app.data.company_knowledge import COMPANY

# Injected into Gemini system prompts (highest priority for tone).
HUMAN_CONSULTANT_STYLE = f"""# HUMAN-LIKE CONVERSATION (HIGHEST PRIORITY)

You are an experienced catering consultant for {COMPANY['brand_name']} on WhatsApp.
The customer must feel they are chatting with a real Srivatsanka team member — never a chatbot.

Write naturally, like a real person. Avoid robotic or scripted wording.
Never repeat the same sentence structure every turn. Every reply should feel unique.

## UNDERSTAND BEFORE RESPONDING
For every message:
1. Read carefully.
2. Understand the meaning.
3. Identify all information they shared.
4. Answer any questions (if they asked 2–3, answer ALL first).
5. Show understanding / acknowledge what they said.
6. Only then continue the enquiry naturally.

Never jump to the next enquiry question without acknowledging what they said.
Never ignore what they just told you.

## ACTIVE LISTENING
Acknowledge specifics: dates, occasions, areas, names, concerns.
Use details already shared (say "your wedding" not "your event" when you know it's a wedding).

## CONVERSATION FLOW
Do NOT make every response follow Answer → Question.
Sometimes: Acknowledgement → Answer → short conversational line → Question.
Not every message must advance the enquiry — if they small-talk, respond warmly, then gently continue.
If they are undecided or browsing, be patient — do not pressure for details.

## EMPATHY & MIRRORING
Match excitement, reassure worry, explain patiently if confused, keep it short if they seem busy.
If they write briefly, reply briefly. If detailed, reply with similar detail.
Casual ↔ politely casual. Formal ↔ formal.

## NEVER SOUND LIKE A FORM OR BOT
Never say: "I have recorded your response", "I am processing", "According to the system",
"Please provide the required information", "I am an AI", "Input received", "Kindly".
Prefer: Thank you for sharing that / Got it / That helps / I understand / Certainly / Happy to help.

## LENGTH
Most replies 20–70 words. Short sentences. No walls of text. At most one emoji, only if natural.
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
            "Certainly.",
            "Sounds good.",
            "Absolutely.",
            "Sure.",
            "Of course.",
            "No worries.",
            "Happy to help.",
            "That works.",
            "Great.",
            "Perfect.",
            "Thank you for letting me know.",
        )
    )


def thanks_reply() -> str:
    return random.choice(
        (
            "You're most welcome! Let me know if there's anything else I can help you with.",
            "My pleasure! Happy to help anytime.",
            "You're welcome — reach out whenever you need us.",
        )
    )


def undecided_reply() -> str:
    return random.choice(
        (
            "No problem at all. Take your time. If there's anything you'd like to know about our catering, I'm happy to help.",
            "That's completely fine — no rush. Feel free to ask about our menus, experience, or anything else.",
            "Of course. Whenever you're ready, we're here. Happy to answer any questions in the meantime.",
        )
    )


def small_talk_reply(*, event_label: str | None = None) -> str:
    occasion = event_label or "your celebration"
    return random.choice(
        (
            f"I'm doing well, thank you for asking! I hope you're having a good day too.\n\nHow can I help with {occasion} today?",
            f"Doing great, thanks! Hope you are too 🌿\n\nWhat would you like to know about {occasion}?",
        )
    )


def welcome_message() -> str:
    brand = COMPANY["brand_name"]
    return random.choice(
        (
            f"Hello! Welcome to *{brand}*. I'm happy to assist you today.\nMay I know your name?",
            f"Hi there! Welcome to *{brand}* 🌿 Happy to help you plan your celebration.\nMay I know your name?",
            f"Hello! Thanks for messaging *{brand}*.\nWho am I speaking with today?",
        )
    )


def acknowledge_opening_without_name(text: str, event_type: str | None) -> str:
    """First message shared occasion/details but no name — acknowledge, then ask name."""
    brand = COMPANY["brand_name"]
    lower = text.lower()
    if event_type and event_type != "General":
        label = event_type.lower()
        if "december" in lower or "wedding" in lower:
            return random.choice(
                (
                    f"That sounds wonderful! We'd be happy to help make your {label} special.\nMay I know your name?",
                    f"Lovely — a {label} is such a special occasion. We're glad you reached out to *{brand}*.\nMay I know your name?",
                )
            )
        return random.choice(
            (
                f"Wonderful! We'd love to help with your {label}.\nMay I know your name?",
                f"That sounds great — happy to assist with your {label}.\nCould I have your name, please?",
            )
        )
    return random.choice(
        (
            f"Hi! Welcome to *{brand}* 🌿 Happy to help.\nMay I know your name?",
            f"Hello! Thanks for reaching out to *{brand}*.\nWho am I speaking with?",
        )
    )


def detail_question(field_key: str, *, event_type: str | None = None) -> str:
    """Varied, non-form questions for enquiry fields."""
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"

    if field_key == "event_date":
        return random.choice(
            (
                f"May I know when your {occasion} is planned?",
                f"When is the {occasion} scheduled?",
                f"Could you tell me the date for your {occasion}?",
                f"When are you planning the {occasion}?",
            )
        )
    if field_key == "event_location":
        return random.choice(
            (
                "May I know which area in Bengaluru the venue will be in?",
                "Which part of Bengaluru will the function be held?",
                "Could you share the venue area in Bengaluru?",
                "Where in Bengaluru is the celebration taking place?",
            )
        )
    if field_key == "preferred_callback":
        return random.choice(
            (
                "When would be a good time for our team to give you a quick call?",
                "What time works best for a short call from our team?",
                "When should we ring you to discuss the details?",
                "When's convenient for a quick callback?",
            )
        )
    return "Could you share a bit more when you have a moment?"


def acknowledge_field(field_key: str, value: str, *, event_type: str | None = None) -> str:
    """Content-aware acknowledgement before the next question."""
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"
    v = value.strip()

    if field_key == "event_date":
        return random.choice(
            (
                f"Wonderful, thank you for sharing your {occasion} date.",
                f"Perfect — noted for {v}.",
                f"Thank you for letting me know about {v}.",
                f"That helps — {v} sounds lovely.",
            )
        )
    if field_key == "event_location":
        return random.choice(
            (
                f"Got it — {v} works well for us.",
                f"Thank you for sharing the venue area ({v}).",
                f"Understood, {v}. That helps.",
                f"Perfect, noted {v}.",
            )
        )
    if field_key == "preferred_callback":
        return random.choice(
            (
                f"Certainly — we'll aim for {v}.",
                f"Sounds good, thank you for letting me know ({v}).",
                f"Perfect, we'll call around then.",
                f"Absolutely — noted for {v}.",
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
    # Vary structure: sometimes one line, sometimes two.
    if random.random() < 0.45:
        return f"{ack}\n\n{next_prompt}"
    return f"{ack} {next_prompt}"


def continue_hint(*, event_type: str | None = None) -> str:
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"
    return random.choice(
        (
            f"Ask me anything about our catering, or say when you're ready to share the date and venue for your {occasion}.",
            "Happy to answer questions — or we can note the date and location whenever you're ready.",
            f"Feel free to ask more about your {occasion}, or we can continue with a couple of quick details.",
            "Any questions at all? Or shall we note the date and venue next?",
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
