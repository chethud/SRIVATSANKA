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
Never output internal labels, markdown headings, or words like RULES / COMPANY / FAQS / Requirements / Tone.
Never dump lists unless the customer asked for a list.
Never continue a reply with instruction headings — stop after the customer-facing answer.
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
    replacements = (
        (r"\bmor3\b", "more"),
        (r"\bm0re\b", "more"),
        (r"\bmoree\b", "more"),
        (r"\bdetials\b", "details"),
        (r"\bdetial\b", "detail"),
        (r"\bdetals\b", "details"),
        (r"\bderails\b", "details"),
        (r"\bderail\b", "detail"),
        (r"\bdetaills\b", "details"),
        (r"\bforther\b", "further"),
        (r"\bfurthur\b", "further"),
        (r"\bfurtherr\b", "further"),
        (r"\bweding\b", "wedding"),
        (r"\bweddign\b", "wedding"),
        (r"\bmarraige\b", "marriage"),
        (r"\bfoof\b", "food"),
        (r"\bfod\b", "food"),
        (r"\bfoood\b", "food"),
        (r"\bmenue\b", "menu"),
        (r"\bpls\b", "please"),
        (r"\bplz\b", "please"),
        (r"\bkno\b", "know"),
        (r"\binfo+m?ation\b", "information"),
        (r"\bphtos\b", "photos"),
        (r"\bphto\b", "photo"),
        (r"\bpics?\b", "photos"),
        (r"\bimideatly\b", "immediately"),
        (r"\bimediately\b", "immediately"),
        (r"\bimmediatly\b", "immediately"),
        (r"\bimidiately\b", "immediately"),
    )
    for pat, repl in replacements:
        t = re.sub(pat, repl, t)
    t = re.sub(r"\bmor3\s*", "more ", t)
    # Fuzzy near-misses for details/food on single tokens
    fixed: list[str] = []
    for word in t.split():
        if word in {"details", "detail", "food", "more", "further", "wedding", "immediately"}:
            fixed.append(word)
            continue
        if _near(word, ("details", "detail", "derails")):
            fixed.append("details")
        elif _near(word, ("food", "foof", "menu")):
            fixed.append("food")
        else:
            fixed.append(word)
    return re.sub(r"\s+", " ", " ".join(fixed)).strip()


def _near(word: str, options: tuple[str, ...], cutoff: float = 0.75) -> bool:
    import difflib

    if len(word) < 3:
        return False
    return bool(difflib.get_close_matches(word, list(options), n=1, cutoff=cutoff))


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
        "about food",
        "about menu",
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
    if re.search(r"\b(need|want|give|share|tell|just)\b.*\b(more|detail|info|information|food|menu)\b", t):
        return True
    if re.search(r"\b(about|just)\s+(food|menu|decor|décor|pooja|venue)", t):
        return True
    return False


def wants_to_move_further(text: str) -> bool:
    """Customer clearly wants to continue collecting enquiry details."""
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
        "next step",
        "note the",
        "take details",
        "take my detail",
        "share my detail",
        "lets continue",
        "let's continue",
        "we can continue",
        "no more questions",
        "no questions",
        "nothing else",
        "that's all",
        "thats all",
        "i am ready",
        "im ready",
        "ready to share",
    )
    if any(c in t for c in cues):
        return True
    # Exact short confirms that mean "let's proceed" after we already asked move-further
    return t in {"further", "move", "yes move", "yes further", "yes continue"}



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
                f"When is your {occasion}?",
                f"When’s your {occasion} planned?",
                f"What date is your {occasion}?",
                f"When are you planning your {occasion}?",
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
                "When’s a good time for a quick call?",
                "What time should we call you?",
                "When works for a short callback?",
            )
        )
    return "Could you share a bit more?"


def acknowledge_field(field_key: str, value: str, *, event_type: str | None = None) -> str:
    """Short acknowledgement — avoid echoing long/messy customer text."""
    v = (value or "").strip()
    if len(v) > 20 or len(v.split()) > 3 or re.search(r"[?]|(need|more|detail|know|tell)", v, re.I):
        return soft_ack()
    if field_key == "event_date":
        return random.choice(("Got it.", "Perfect.", "Thanks!", "Noted."))
    if field_key == "event_location":
        return random.choice((f"Got it — {v}.", "Sounds good.", "Perfect.", "Thanks!"))
    if field_key == "preferred_callback":
        return random.choice(("Perfect.", "Sounds good.", "Absolutely.", "Got it."))
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


def ask_move_further_prompt() -> str:
    """After answering questions — check before collecting enquiry details."""
    return random.choice(
        (
            "Do you still need more information, or can we move further?",
            "Would you like more information, or can we move further?",
            "Any more questions, or can we move further?",
            "Do you need anything else, or can we move further?",
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
