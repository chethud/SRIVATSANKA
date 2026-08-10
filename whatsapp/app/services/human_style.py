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
Every reply must feel like a real human WhatsApp chat, never a chatbot or support script.

## LENGTH (STRICT)
- Ideal: 1–3 short sentences.
- Most replies: under 40 words.
- Greeting: 10–20 words. Simple answer: 5–20 words. Answer + next question: 15–35 words.
- Longer only if they ask for detailed info (still under ~100 words).
- No long paragraphs. No walls of text. Do not dump lists of services unless asked.

## UNDERSTAND BEFORE RESPONDING (STRICT)
1. Read the customer's message carefully, including spelling mistakes.
2. Infer what they meant (e.g. "mor3" = more, "forther" = further, "weding" = wedding).
3. Focus only on what they asked, do not jump to a new form question if they asked for information.
4. Acknowledge briefly, answer that point simply, then continue only if needed.
5. Never repeat their message back word-for-word (especially with typos).
6. Keep language simple, not complicated.

## VOICE
Write like WhatsApp: simple everyday language. Vary wording, never the same phrase every turn.
Prefer: Got it. / Sounds good. / Absolutely. / Certainly. / No problem. / Happy to help. /
Of course. / Perfect. / Great. / Thanks for sharing. / I understand. / That sounds wonderful. / No worries.

Never say: "Thank you for contacting…", "Kindly provide", "Your information has been recorded",
"Please wait while I process", "I am an AI", "Input received", "delighted to assist you with your enquiry".

Never use em-dashes (—) or en-dashes (–). Use commas, periods, or plain hyphens only.
Never output robotic numbered pickers such as "1. Lunch 2. Dinner". Ask naturally in prose.

If a short answer is enough, stop. At most one emoji, only if it fits.
Never claim to be a bot or AI.
Never output internal labels, markdown headings, or words like RULES / COMPANY / FAQS / Requirements / Tone.
Never dump lists unless the customer asked for a list.
Never continue a reply with instruction headings, stop after the customer-facing answer.

## FIELD HANDLING (STRICT)
- Guest ranges: if they say "30-50", "200 to 300", or "around 50-70", keep the FULL range in your reply. Never drop to a single number.
- Dates: keep full relative context (e.g. "the 3rd week of next month", "mid-August"). Never echo only "3rd".
- Urgent dates (today, tomorrow, or within 7 days): do not ask meal/theme/extra details. Fast-track to an immediate senior callback.
- Meal type (lunch/dinner/high tea): ask ONLY for birthdays or informal family gatherings. Skip for weddings, engagements, receptions, upanayanam, baby showers, and housewarmings.
- Venue/location: extract the clean place name (e.g. "Hundur"). Never echo filler like "Yes Hundur".
- Custom / fusion / live counters: always respond warmly and say you noted it for the planner/chef call. Never give restrictive rejections.
- If they want to "discuss on call" / "tell me on call": stop collecting more details and immediately ask for the best callback time.
- Callback "now" / "ASAP" / "right away": say the lead planning team will call ASAP. Never invent a calculated timestamp.
- If they choose straight to planning: jump to the date question. Do not dump mandap/floral/menu showcase text.
- Never send dry system text like "We've already got your enquiry". Always close with warm hospitality.
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
    if is_portfolio_inquiry(text):
        return True
    if is_service_topic_reply(text):
        return True
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
        "get more details",
        "can i get more",
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
            "No problem, take your time. Happy to answer any questions.",
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
    return (
        "Hello! Welcome to Srivatsanka Events & Catering. ✨\n\n"
        "Something special is brewing! We’d love to know who we’re chatting with. May I have your name, please?"
    )


def acknowledge_opening_without_name(text: str, event_type: str | None) -> str:
    """First message shared occasion/details but no name; short ack, then ask name."""
    if event_type:
        occasion = event_type.lower()
        return f"We'd love to help with your {occasion}! May I know your name first?"
    return welcome_message()


def wants_discuss_on_call(text: str) -> bool:
    """Customer wants to skip form details and talk on a call instead."""
    t = normalize_customer_text(text)
    cues = (
        "discuss on call",
        "discuss over call",
        "tell me on call",
        "tell on call",
        "talk on call",
        "talk over call",
        "speak on call",
        "on the call",
        "during the call",
        "over a call",
        "over the call",
        "lets discuss on call",
        "let's discuss on call",
        "i'll talk on call",
        "ill talk on call",
        "will talk on call",
        "prefer a call",
        "prefer call",
        "call and discuss",
        "discuss later on call",
    )
    return any(c in t for c in cues)


def wants_straight_to_planning(text: str) -> bool:
    """Customer wants to skip gallery/showcase and start collecting details."""
    t = normalize_customer_text(text)
    cues = (
        "straight to planning",
        "straight into planning",
        "dive straight",
        "dive into planning",
        "dive into",
        "start planning",
        "lets plan",
        "let's plan",
        "begin planning",
        "move further",
        "move forward",
        "go further",
        "go ahead",
        "continue",
        "proceed",
        "take details",
        "note the",
    )
    if any(c in t for c in cues):
        return True
    if "planning" in t and any(w in t for w in ("straight", "dive", "start", "lets", "let's", "into")):
        return True
    return t in {"planning", "plan", "further", "move", "yes move", "yes further", "yes continue", "dive"}


def wants_showcase_look(text: str) -> bool:
    """Customer wants to see past setups / photos / cuisines first."""
    t = normalize_customer_text(text)
    cues = (
        "look",
        "photo",
        "photos",
        "pic",
        "pics",
        "showcase",
        "past setup",
        "past setups",
        "signature cuisine",
        "show me",
        "see some",
        "gallery",
        "examples",
        "menu",
        "cuisine",
    )
    return any(c in t for c in cues)


def warm_enquiry_signoff(*, name: str | None = None, event_type: str | None = None) -> str:
    """Signature hospitality close for completed / already-saved enquiries."""
    who = (name or "there").strip() or "there"
    return (
        f"Thank you so much, {who}! It was an absolute pleasure chatting with you. "
        "We’re excited to make your celebration truly unforgettable. ✨\n\n"
        "Have a wonderful rest of your day, and talk to you soon!"
    )


def urgent_timeline_reply() -> str:
    return (
        "Got it! Since your celebration is right around the corner, we are prioritizing your inquiry! "
        "Our senior event executive will call you immediately to confirm availability and discuss setups."
    )


def immediate_callback_reply(*, name: str | None = None) -> str:
    who = (name or "there").strip() or "there"
    return f"Got it, {who}! We have notified our lead planning team to give you a callback as soon as possible on this number. 📱"


def ask_event_date_only(*, event_type: str | None = None) -> str:
    """Date question only (no planning preamble). Use after an ack or showcase summary."""
    occasion = (event_type or "celebration").strip().lower()
    if not occasion or occasion == "general":
        occasion = "celebration"
    return f"What is your tentative date or month for the {occasion}?"


def planning_date_prompt(*, event_type: str | None = None) -> str:
    """Intent B default: one ack + date ask (never stack another planning preamble on top)."""
    return (
        "Perfect! Let's get right down to planning. 🗓️\n\n"
        f"{ask_event_date_only(event_type=event_type)}"
    )


def showcase_followup_date_ask(*, event_type: str | None = None) -> str:
    """Intent A close after portfolio/showcase summary — date ask only."""
    occasion = (event_type or "celebration").strip().lower()
    if not occasion or occasion == "general":
        occasion = "celebration"
    if occasion == "wedding":
        return (
            "To help us check availability for your big day, "
            f"what is your tentative date or month for the {occasion}?"
        )
    return (
        "To help us check venue and catering availability for your grand day, "
        f"what is your tentative date or month for the {occasion}?"
    )


def intent_b_planning_reply(
    *,
    text: str = "",
    name: str | None = None,
    event_type: str | None = None,
) -> str:
    """
    Single State-3→4 Intent B reply (Kannan.rules.txt).
    Must not prepend/append another planning_date_prompt — that caused duplicate copy.
    """
    t = normalize_customer_text(text)
    date_q = ask_event_date_only(event_type=event_type)
    who = (name or "").strip()

    if t in {"no", "nope", "skip", "nah"} or t.startswith("no "):
        return f"Got it! Let's jump straight into the planning details.\n\n{date_q}"
    if t in {"ok", "okay", "k", "okk", "fine", "yes"}:
        return f"Wonderful! Let's jump straight into the details.\n\n{date_q}"
    if who:
        return f"Perfect, {who}! Let's get right down to planning. 🗓️\n\n{date_q}"
    return planning_date_prompt(event_type=event_type)


def callback_confirmation_reply(*, name: str | None = None, callback_label: str | None = None) -> str:
    who = (name or "there").strip() or "there"
    label = (callback_label or "").strip().lower()
    if not label or label in {"anytime", "whenever", "you decide", "when free", "any time today"}:
        return f"Sounds great, {who}! Our senior event planner will give you a call during business hours today on this number."
    if "today evening after 7" in label:
        slot = "today after 7:00 PM"
    elif "tomorrow morning around 11" in label:
        slot = "tomorrow around 11:00 AM"
    elif "day after around tea time" in label or "day after tea time" in label:
        slot = "day after tomorrow between 4:00 PM and 5:00 PM"
    elif "weekend morning" in label:
        slot = "this weekend morning"
    else:
        slot = callback_label or "the requested time"
    return f"Noted, {who}! We have scheduled your callback for {slot}. Our senior event planner will reach out to you on this number. 🗓️"


def callback_pivot_prompt(*, name: str | None = None) -> str:
    who = (name or "there").strip() or "there"
    return (
        f"Of course, {who}! We can discuss all the details directly on call. "
        "When would be the best time to give you a quick call?"
    )


def detail_question(field_key: str, *, event_type: str | None = None) -> str:
    """Short, varied enquiry questions."""
    occasion = (event_type or "celebration").lower()
    if occasion == "general":
        occasion = "celebration"

    if field_key == "event_date":
        # Re-ask / mid-collection: date only (preamble already used leaving State 3).
        return ask_event_date_only(event_type=event_type)
    if field_key == "guest_count":
        from app.services.guided_flow import get_event_profile
        profile = get_event_profile(event_type)
        return profile["pax_question"]
    if field_key == "event_location":
        return random.choice(
            (
                "Do you already have a venue booked for the celebration, or are you looking for help with venue selection? If it is fixed, please share the venue name and area. If not, just let us know your preferred city or locality.",
                f"For your {occasion}, is the venue already fixed? If yes, please share the venue name and area. If not yet, just tell us your preferred city or locality and we can help from there.",
            )
        )
    if field_key == "preferred_callback":
        return random.choice(
            (
                "We’d love to connect you with our senior planner so we can share custom proposals and discuss venues and menu tastings.\n\nWhen would be the best time to give you a quick call? (e.g., today evening, tomorrow after 6 PM, or weekend morning?)",
                "When works for a short callback?",
            )
        )
    if field_key == "meal_preference":
        return "Are you planning a lunch feast, an evening dinner, or high tea snacks?"
    return "Could you share a bit more?"


def acknowledge_field(field_key: str, value: str, *, event_type: str | None = None) -> str:
    """Short acknowledgement, avoid echoing long/messy customer text."""
    v = (value or "").strip()
    if len(v) > 20 or len(v.split()) > 3 or re.search(r"[?]|(need|more|detail|know|tell)", v, re.I):
        return soft_ack()
    if field_key == "event_date":
        return random.choice(("Got it.", "Perfect.", "Thanks!", "Noted."))
    if field_key == "guest_count":
        return random.choice(("Got it.", "Perfect.", "Thanks!", "Noted."))
    if field_key == "meal_preference":
        return random.choice(("Got it.", "Perfect.", "Sounds good."))
    if field_key == "event_location":
        return f"Got it, {v}! We have noted down the location."
    if field_key == "preferred_callback":
        return random.choice(("Perfect.", "Sounds good.", "Absolutely.", "Got it."))
    return soft_ack()


def _occasion_phrase(event_type: str | None) -> str:
    occasion = (event_type or "celebration").strip().lower()
    if not occasion or occasion == "general":
        return "a celebration"
    article = "an" if occasion[0] in "aeiou" else "a"
    return f"{article} {occasion} celebration"


def natural_field_ack(
    field_key: str,
    value: str,
    next_prompt: str,
    *,
    event_type: str | None = None,
) -> str:
    if field_key == "event_date":
        display = (value or "").strip()
        if re.match(r"^\d", display):
            display = f"The {display}"
        elif display and display[0].islower():
            display = display[0].upper() + display[1:]
        return f"{display} is a wonderful time for {_occasion_phrase(event_type)}!\n\n{next_prompt}"
    if field_key == "guest_count":
        display = re.sub(r"\s*[-–—]\s*", " to ", str(value).strip(), count=1)
        display = re.sub(r"\s+", " ", display)
        low_match = re.search(r"(\d+)", display)
        low = int(low_match.group(1)) if low_match else 100
        style = "intimate celebration" if low <= 80 else "celebration"
        article = "An" if style.startswith("intimate") else "A"
        return f"Got it! {article} {style} with {display} guests sounds wonderful.\n\n{next_prompt}"
    if field_key == "event_location":
        place = (value or "").strip()
        return f"Got it, {place}! We have noted down the location.\n\n{next_prompt}"
    if field_key == "meal_preference":
        return f"Got it! We'll plan for the {value} service.\n\n{next_prompt}"
    ack = acknowledge_field(field_key, value, event_type=event_type)
    if random.random() < 0.5:
        return f"{ack}\n{next_prompt}"
    return f"{ack} {next_prompt}"


def continue_hint(*, event_type: str | None = None) -> str:
    return random.choice(
        (
            "Any questions, or can we move further?",
            "Want to know anything, or can we move further?",
            "Happy to answer questions, or can we move further?",
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


def is_service_topic_reply(text: str) -> bool:
    """Short topic picks like 'food' / 'decor' after the bot offered service areas."""
    t = normalize_customer_text(text).strip().rstrip("?.!")
    topics = {
        "food",
        "menu",
        "cuisine",
        "cuisines",
        "catering",
        "cater",
        "decor",
        "décor",
        "decoration",
        "decorations",
        "pooja",
        "ritual",
        "rituals",
        "venue",
        "venues",
        "hospitality",
        "photos",
        "photo",
        "portfolio",
        "gallery",
    }
    if t in topics:
        return True
    words = t.split()
    if 1 <= len(words) <= 3 and any(w in topics for w in words):
        return True
    return False


def is_portfolio_inquiry(text: str) -> bool:
    """State 2 catalog / portfolio questions from Kannan.rules.txt §4."""
    t = normalize_customer_text(text)
    cues = (
        "what events",
        "what event",
        "events do you",
        "what do you cater",
        "what do you offer",
        "what services",
        "services do you",
        "what have you done",
        "events have you done",
        "until today",
        "i want to know what you do",
        "know what you do",
        "what do you do",
        "tell me what you do",
        "your portfolio",
        "show portfolio",
        "types of events",
        "kind of events",
        "list of events",
        "what all events",
        "what all do you",
    )
    if any(c in t for c in cues):
        return True
    if re.search(r"\b(what|which)\b.*\b(events?|services?|offerings?)\b", t):
        return True
    if re.search(r"\b(do you|can you)\b.*\b(cater|handle|cover|organize|organise)\b", t) and "?" in text:
        return True
    return False


def catalog_portfolio_reply(*, customer_name: str | None = None) -> str:
    """Exact catalog variants from Kannan.rules.txt State 2 §4."""
    name = (customer_name or "").strip() or "there"
    variant_a = (
        "We specialize in crafting authentic, unforgettable traditional celebrations! 🌟\n\n"
        "Here are the key events we cater to:\n"
        "✨ **Weddings, Engagements & Receptions**\n"
        "🍃 **Upanayanam, Housewarmings & Baby Showers (Seemantham)**\n"
        "🎉 **Birthdays, Anniversaries & Family Gatherings**\n"
        "🙏 **Traditional Ceremonies & Religious Poojas**\n\n"
        "Our core expertise spans **Pure Vegetarian South Indian Catering** "
        "(Karnataka, Andhra, Tamil Nadu & Kerala cuisines), **Stage & Theme Floral Decor**, "
        "**Pooja Setups**, and **End-to-End Event Planning**.\n\n"
        f"Which of these special occasions are you planning today, {name}?"
    )
    variant_b = (
        "We’d love to share! Srivatsanka provides complete end-to-end event solutions "
        "tailored to your family's traditions. ✨\n\n"
        "**Our Core Services Include:**\n"
        "🍱 **Pure Vegetarian Regional Catering:** Authentic South Indian feasts across "
        "Karnataka, Andhra, Tamil Nadu & Kerala recipes.\n"
        "🌸 **Bespoke Decor:** Stage, floral, mandap, and theme setups.\n"
        "🪔 **Ritual & Pooja Support:** Traditional pooja arrangements, sacred ceremony setups, "
        "and ritual coordination.\n"
        "🏰 **Venue & Hospitality:** Venue selection, venue planning, and guest management.\n\n"
        "Are you looking for full event planning or specific catering/decor services for your "
        "upcoming celebration?"
    )
    return random.choice((variant_a, variant_b))


def is_unsupported_event_request(text: str) -> bool:
    """Cocktail / alcohol / expo / conference — Kannan.rules.txt unsupported list."""
    t = normalize_customer_text(text)
    if re.search(r"\b(cocktail|cocktails|alcohol|alcoholic|bar party|booze|liquor|hard drinks?)\b", t):
        return True
    if re.search(r"\b(exhibition|expo|conference|conferences|trade show|tradeshow)\b", t):
        return True
    return False


def unsupported_event_refusal(*, customer_name: str | None = None) -> str:
    name = (customer_name or "").strip() or "there"
    return (
        f"Thank you for reaching out, {name}! At Srivatsanka, we specialize exclusively in "
        "traditional, family, and cultural celebrations. We will notify the team to confirm "
        "regarding your request. Thank you and have a nice day!! ✨"
    )
