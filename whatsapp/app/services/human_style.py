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

## UNDERSTAND BEFORE RESPONDING (STRICT)
1. Read the customer's message carefully — including spelling mistakes.
2. Infer what they meant (e.g. "mor3" = more, "forther" = further, "weding" = wedding).
3. Focus only on what they asked — do not jump to a new form question if they asked for information.
4. Acknowledge briefly, answer that point simply, then continue only if needed.
5. Never repeat their message back word-for-word (especially with typos).
6. Keep language simple — not complicated.

## VOICE
Write like WhatsApp: simple everyday language. Vary wording — never the same phrase every turn.
Prefer: Got it. / Sounds good. / Absolutely. / Certainly. / No problem. / Happy to help. /
Of course. / Perfect. / Great. / Thanks for sharing. / I understand. / That sounds wonderful. / No worries.

Never say: "Thank you for contacting…", "Kindly provide", "Your information has been recorded",
"Please wait while I process", "I am an AI", "Input received", "delighted to assist you with your enquiry".

If a short answer is enough, stop. At most one emoji, only if it fits.
Never claim to be a bot or AI.
Never output internal labels, markdown headings, or words like RULES / COMPANY / FAQS.
Never dump lists unless the customer asked for a list.
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


def normalize_customer_text(text: str) -> str:
    """Fix common WhatsApp typos before understanding intent."""
    t = (text or "").lower().strip()
    # digit-for-letter typos: mor3 -> more, forther already text
    replacements = (
        (r"\bmor3\b", "more"),
        (r"\bm0re\b", "more"),
        (r"\bmoree\b", "more"),
        (r"\bdetials\b", "details"),
        (r"\bdetial\b", "detail"),
        (r"\bdetals\b", "details"),
        (r"\bforther\b", "further"),
        (r"\bfurthur\b", "further"),
        (r"\bfurtherr\b", "further"),
        (r"\bweding\b", "wedding"),
        (r"\bweddign\b", "wedding"),
        (r"\bmarraige\b", "marriage"),
        (r"\bpls\b", "please"),
        (r"\bplz\b", "please"),
        (r"\bkno\b", "know"),
        (r"\b kno w\b", " know "),
        (r"\binfo+m?ation\b", "information"),
        (r"\bphtos\b", "photos"),
        (r"\bphto\b", "photo"),
        (r"\bpics?\b", "photos"),
    )
    for pat, repl in replacements:
        t = re.sub(pat, repl, t)
    # mor3details / moredetails glued
    t = re.sub(r"\bmor3\s*", "more ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def wants_more_info(text: str) -> bool:
    """Customer wants information — not ready to fill the next form field."""
    t = normalize_customer_text(text)
    cues = (
        "know more",
        "need more",
        "more detail",
        "more details",
        "tell me more",
        "share more",
        "more info",
        "more information",
        "about your",
        "about the",
        "about event",
        "about events",
        "explain",
        "what all",
        "what do you include",
        "what do you offer",
        "what services",
        "details",
        "information",
    )
    if any(c in t for c in cues):
        return True
    # "yeah i need more" / "i want details"
    if re.search(r"\b(need|want|give|share|tell)\b.*\b(more|detail|info|information)\b", t):
        return True
    return False


def wants_to_move_further(text: str) -> bool:
    """Customer agrees to continue collecting enquiry details."""
    t = normalize_customer_text(text)
    if wants_more_info(text):
        return False
    cues = (
        "move further",
        "move forward",
        "go further",
        "go ahead",
        "continue",
        "proceed",
        "next",
        "note the",
        "take details",
        "share details",
        "lets continue",
        "let's continue",
    )
    if any(c in t for c in cues):
        return True
    return False



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
    """Short content-aware acknowledgement — never echo long / messy customer text."""
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"
    v = (value or "").strip()
    # Don't repeat sentences, typos, or long dumps back to the customer
    if len(v) > 28 or len(v.split()) > 4 or re.search(r"[?]|(need|more|detail|know|tell)", v, re.I):
        return soft_ack()

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
            "Any questions, or can we move further?",
            "Want to know anything, or can we move further?",
            "Happy to answer questions — or can we move further?",
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
