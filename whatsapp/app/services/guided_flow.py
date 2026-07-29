"""Structured WhatsApp enquiry flow before cuisine selection."""

import logging
import random
import re

from app.data.company_knowledge import (
    is_known_event_type,
    match_event_type,
)
from app.schemas import AgentTurnResult, EnquiryFields, MediaAttachment
from app.services.conversation_turns import (
    customer_wants_to_proceed,
    extract_name,
    is_greeting_only,
    natural_continue_hint,
    natural_field_ack,
    record_exchange,
)
from app.services.guided_conversation import (
    answer_details_question,
    answer_showcase_question,
)
from app.services.gemini_conversation import is_likely_field_answer, looks_like_question
from app.services.human_style import (
    acknowledge_opening_without_name,
    ask_move_further_prompt,
    callback_confirmation_reply,
    callback_pivot_prompt,
    catalog_portfolio_reply,
    detail_question,
    immediate_callback_reply,
    is_portfolio_inquiry,
    is_service_topic_reply,
    is_small_talk,
    is_thanks_only,
    is_undecided,
    is_unsupported_event_request,
    looks_like_polite_filler,
    planning_date_prompt,
    small_talk_reply,
    thanks_reply,
    undecided_reply,
    unsupported_event_refusal,
    urgent_timeline_reply,
    wants_discuss_on_call,
    wants_more_info,
    wants_showcase_look,
    wants_straight_to_planning,
    wants_to_move_further,
    warm_enquiry_signoff,
    welcome_message,
)
from app.services.session_store import ConversationSession, GuidedStep
from app.services.event_date import is_urgent_event_date
from app.services.location_normalize import extract_location_entity
from app.services.callback_time import is_immediate_callback, normalize_callback_label
from app.services.entity_extractor import extract_entities
from app.services.memory_manager import hydrate_memory
from app.services.slot_manager import apply_entities, slot_collected
from app.services.transition_engine import advance_from_slots, move_to
from app.services.validation_layer import (
    circuit_breaker_reply,
    clear_slot_failures,
    is_reset_message,
    record_slot_failure,
    repeated_question,
    reset_session_to_greeting,
    should_trip_circuit_breaker,
    slot_fail_count,
    track_question,
)
from app.services.website_gallery import customer_wants_photos, prepare_gallery_photos
from app.services.whatsapp_client import normalize_phone

logger = logging.getLogger(__name__)

DETAIL_KEYS = ("event_date", "guest_count", "event_location", "meal_preference", "preferred_callback")

# Meal lunch/dinner/high-tea picker is only for informal gatherings.
MEAL_PICKER_EVENT_KEYS = ("birthday", "family gathering", "family function", "get together", "get-together")


def should_ask_meal_preference(event_type: str | None) -> bool:
    label = (event_type or "").lower()
    return any(key in label for key in MEAL_PICKER_EVENT_KEYS)


def _skip_inapplicable_fields(session: ConversationSession) -> None:
    """Auto-fill fields that do not apply to this occasion type."""
    if session.fields.meal_preference is None and not should_ask_meal_preference(session.fields.event_type):
        session.fields = EnquiryFields(
            **{**session.fields.model_dump(), "meal_preference": "To be discussed on call"}
        )


EVENT_PROFILES = {
    "wedding": {
        "validation": "Oh, wonderful! A wedding is such a momentous milestone, full of love, family, and beautiful traditions. You’re in the right hands with us. ❤️",
        "showcase": "From traditional & contemporary mandap decor and stage floral decoration to authentic regional vegetarian feasts (Karnataka, Andhra, Tamil Nadu, Kerala), food and decor are the heart of every event we curate.",
        "pax_question": "And roughly how many guests are you expecting to host? (An estimate works perfectly!)",
    },
    "engagement": {
        "validation": "Congratulations! An engagement is the beautiful beginning of a brand-new journey together. ✨",
        "showcase": "From stage & ring ceremony decor and floral arrangements to custom vegetarian catering, we design every detail to be absolute perfection.",
        "pax_question": "And roughly how many guests are you expecting to host for the engagement? (An estimate works perfectly!)",
    },
    "reception": {
        "validation": "How exciting! A wedding reception is all about hosting your grand circle of family and friends in style. 🌟",
        "showcase": "From premium theme decor and stage illumination to multi-regional buffet feasts, we ensure your guests receive warm, memorable hospitality.",
        "pax_question": "And roughly how many guests are you expecting to host for the reception? (An estimate works perfectly!)",
    },
    "baby shower": {
        "validation": "Ah, what beautiful news! Welcoming new life into the family through Seemantham is such a blessed and joyful occasion. 🙏",
        "showcase": "From traditional Seemantham decor and ritual setup arrangements to authentic festive vegetarian meals, we handle every detail with love.",
        "pax_question": "And roughly how many guests are you expecting to host? (An estimate works perfectly!)",
    },
    "seemantham": {
        "validation": "Ah, what beautiful news! Welcoming new life into the family through Seemantham is such a blessed and joyful occasion. 🙏",
        "showcase": "From traditional Seemantham decor and ritual setup arrangements to authentic festive vegetarian meals, we handle every detail with love.",
        "pax_question": "And roughly how many guests are you expecting to host? (An estimate works perfectly!)",
    },
    "upanayanam": {
        "validation": "Namaste! An Upanayanam is a deeply sacred Vedic milestone, and we take immense pride in supporting authentic ritual setups and pure vegetarian hospitality. 🙏",
        "showcase": "From sacred ceremony & pooja setups and traditional floral decor to sattvic/authentic South Indian feasts, we specialize in pure traditional events.",
        "pax_question": "And roughly how many guests are we expecting for this sacred thread ceremony? (An estimate works perfectly!)",
    },
    "sacred thread ceremony": {
        "validation": "Namaste! An Upanayanam is a deeply sacred Vedic milestone, and we take immense pride in supporting authentic ritual setups and pure vegetarian hospitality. 🙏",
        "showcase": "From sacred ceremony & pooja setups and traditional floral decor to sattvic/authentic South Indian feasts, we specialize in pure traditional events.",
        "pax_question": "And roughly how many guests are we expecting for this sacred thread ceremony? (An estimate works perfectly!)",
    },
    "housewarming": {
        "validation": "Congratulations on your new home! 🏡 Entering a new abode with a sacred Gruhapravesham is a deeply spiritual milestone.",
        "showcase": "From sacred ceremony & pooja arrangements and traditional entrance/floral decor to guest hospitality and homely feasts, we celebrate your new beginning with warm traditions.",
        "pax_question": "And roughly how many guests are you expecting to host? (An estimate works perfectly!)",
    },
    "gruhapravesham": {
        "validation": "Congratulations on your new home! 🏡 Entering a new abode with a sacred Gruhapravesham is a deeply spiritual milestone.",
        "showcase": "From sacred ceremony & pooja arrangements and traditional entrance/floral decor to guest hospitality and homely feasts, we celebrate your new beginning with warm traditions.",
        "pax_question": "And roughly how many guests are you expecting to host? (An estimate works perfectly!)",
    },
    "birthday": {
        "validation": "Awesome! Milestone birthdays deserve a fun, memorable gathering with great food and vibrant decor! 🎉",
        "showcase": "From vibrant theme decoration and stage setups to delicious vegetarian catering & dessert spreads, we make every birthday memorable.",
        "pax_question": "And roughly how many guests are we expecting for the party? (An estimate works perfectly!)",
    },
    "family gathering": {
        "validation": "That sounds lovely! Gathering family together over authentic traditional food and warm hospitality is what we do best. ✨",
        "showcase": "From customized event solutions and traditional decor to authentic regional cuisines, family events are our absolute passion.",
        "pax_question": "And roughly how many family members/guests are you expecting? (An estimate works perfectly!)",
    },
    "traditional ceremony": {
        "validation": "That sounds lovely! Gathering family together over authentic traditional food and warm hospitality is what we do best. ✨",
        "showcase": "From customized event solutions and traditional decor to authentic regional cuisines, family events are our absolute passion.",
        "pax_question": "And roughly how many family members/guests are you expecting? (An estimate works perfectly!)",
    },
}

DEFAULT_PROFILE = {
    "validation": "Oh, wonderful! A celebration is such a momentous milestone, full of love, family, and beautiful traditions. You’re in the right hands with us. ❤️",
    "showcase": "From customized event solutions and traditional decor to authentic regional cuisines, we handle every detail with love.",
    "pax_question": "And roughly how many guests are you expecting to host? (An estimate works perfectly!)",
}

def get_event_profile(event_type: str | None) -> dict:
    if not event_type:
        return DEFAULT_PROFILE
    label = event_type.lower()
    for key, profile in EVENT_PROFILES.items():
        if key in label:
            return profile
    return DEFAULT_PROFILE


SKIP_NAMES = {
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
}


def _event_label(session: ConversationSession) -> str | None:
    et = session.fields.event_type
    if et and et != "General":
        return et
    return None


def _next_detail_key(session: ConversationSession) -> str | None:
    _skip_inapplicable_fields(session)
    for key in DETAIL_KEYS:
        if getattr(session.fields, key) is not None:
            continue
        if key == "meal_preference":
            inferred = infer_meal_preference(session)
            if inferred:
                from app.services.dish_flow import _preferences_to_items
                session.selected_dishes = _preferences_to_items(inferred)
                session.fields.meal_preference = ", ".join(inferred)
                continue
        return key
    return None


def _next_detail_prompt(session: ConversationSession) -> str | None:
    key = _next_detail_key(session)
    if not key:
        return None
    return detail_question(key, event_type=session.fields.event_type)


def _details_complete(session: ConversationSession) -> bool:
    _skip_inapplicable_fields(session)
    return all(getattr(session.fields, key) is not None for key in DETAIL_KEYS)


def _ask_name_again(text: str) -> str:
    if is_greeting_only(text) or text.lower().strip().rstrip("!.,") in SKIP_NAMES:
        return random.choice(
            (
                "No worries 🙂 What's your name?",
                "Sure, who should I say this is from?",
                "Happy to help. May I know your name?",
            )
        )
    return random.choice(
        (
            "Could I get your name?",
            "Mind sharing your name?",
            "One quick one, what's your name?",
        )
    )


def _is_custom_request(text: str) -> bool:
    t = text.lower()
    custom_cues = {
        "italian", "pasta", "pizza", "gelato", "chinese", "north indian",
        "fusion", "fusion food", "fusion foods", "fusion dessert", "custom dessert",
        "fusion payasam", "tender coconut payasam", "live dessert", "live counter",
        "live counters", "bespoke", "interactive counter", "unlisted", "unique setup",
        "custom menu", "custom cuisine", "custom food", "global counter", "mocktail",
        "continental", "pan asian", "multi cuisine",
    }
    if any(cue in t for cue in custom_cues):
        return True
    if re.search(r"\b(can you|can u|could you|do you)\b.*\b(fusion|custom|live|italian|chinese|dessert|counter)", t):
        return True
    return False


def handle_custom_request(session: ConversationSession, text: str, next_reply: str) -> str:
    if _is_custom_request(text):
        current_notes = session.fields.notes or ""
        if text not in current_notes:
            session.fields.notes = f"{current_notes}\n[Custom Request]: {text}".strip()
        preference = "custom culinary experiences"
        lower = text.lower()
        if "fusion" in lower:
            preference = "fusion foods"
        elif "live" in lower and "counter" in lower:
            preference = "interactive live counters"
        elif "italian" in lower:
            preference = "Italian options"
        elif "chinese" in lower or "pan asian" in lower:
            preference = "Pan-Asian / Chinese options"
        elif "custom" in lower:
            preference = "custom menu options"
        ack = (
            "Yes, absolutely! Our chefs love crafting custom culinary experiences "
            "and interactive fusion counters. I've made a special note of your preference "
            f"for {preference} so our senior planner and head chef can walk you through "
            "our menu options during your call."
        )
        if next_reply and next_reply.strip():
            return f"{ack}\n\n{next_reply}"
        return ack
    return next_reply


def _fill_pending_for_callback(session: ConversationSession) -> None:
    """Skip remaining detail fields so we can pivot straight to callback scheduling."""
    data = session.fields.model_dump()
    placeholder = "To be discussed on call"
    for key in DETAIL_KEYS:
        if key == "preferred_callback":
            continue
        if data.get(key) is None:
            data[key] = placeholder
    session.fields = EnquiryFields(**data)


def _venue_help_callback_prompt(location_value: str | None = None) -> str:
    if location_value and location_value != "Venue Selection Needed":
        return (
            f"We'd be happy to help you find the perfect venue in {location_value}! "
            "What would be a good time for a short callback?"
        )
    return (
        "We'd be happy to help you find the perfect venue! "
        "What city or locality are you considering, and when would be a good time for a short callback?"
    )


def _complete_enquiry_reply(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
    *,
    lead: str | None = None,
) -> AgentTurnResult:
    phone = normalize_phone(whatsapp_id)
    session.fields = EnquiryFields(
        **{**session.fields.model_dump(), "phone_number": session.fields.phone_number or phone}
    )
    move_to(session, GuidedStep.DONE)
    signoff = warm_enquiry_signoff(
        name=session.fields.customer_name,
        event_type=session.fields.event_type,
    )
    callback_label = (session.fields.preferred_callback or "").strip()
    if lead:
        reply = f"{lead}\n\n{signoff}"
    elif is_immediate_callback(callback_label or user_text):
        reply = (
            f"{immediate_callback_reply(name=session.fields.customer_name)}\n\n{signoff}"
        )
    else:
        reply = f"{callback_confirmation_reply(name=session.fields.customer_name, callback_label=callback_label)}\n\n{signoff}"
    reply = handle_custom_request(session, user_text, reply)
    record_exchange(session, user_text, reply)
    return AgentTurnResult(
        reply=reply,
        fields=session.fields,
        enquiry_fields_complete=True,
    )


def _company_intro_message(name: str) -> str:
    return f"Lovely to connect with you, {name}! 😊 How can we help bring your celebration to life today? Are you planning a wedding, an Upanayanam, a housewarming, or another special occasion?"


def _event_showcase_message(event_type: str, *, with_images: bool = False) -> str:
    profile = get_event_profile(event_type)
    validation = profile["validation"]
    return (
        f"{validation}\n\n"
        "Before we jump into the details, would you like to take a quick look at some of our past setups and signature cuisines, or shall we dive straight into planning your event?"
    )


def _detect_event(text: str, *, name: str | None = None) -> str | None:
    """Return a known occasion from text, never a person's name."""
    et = match_event_type(text)
    if not is_known_event_type(et):
        return None
    if name and et.lower() == name.lower():
        return None
    # Single-word replies that are just the person's name are not occasions
    words = text.strip().split()
    if name and len(words) == 1 and words[0].lower().rstrip(".,!") == name.lower():
        return None
    return et


def extract_date_entity(text: str) -> str:
    raw = text.strip().rstrip(".,!?")
    lower = raw.lower()

    # Prefer full relative timeframe phrases before bare ordinals like "3rd"
    relative_patterns = (
        r"(?:the\s+)?\d+(?:st|nd|rd|th)\s+week\s+of\s+next\s+month",
        r"next\s+month(?:\s+(?:the\s+)?\d+(?:st|nd|rd|th)\s+week)?",
        r"(?:the\s+)?\d+(?:st|nd|rd|th)\s+week\s+of\s+(?:this\s+|next\s+)?\w+",
        r"(?:early|mid|late)[\s-]*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|next\s+month)",
        r"(?:this|next)\s+(?:week|month|weekend|year)",
    )
    for pat in relative_patterns:
        match = re.search(pat, lower, re.I)
        if match:
            return raw[match.start() : match.end()]

    months_pat = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
    days_pat = r"\d+(?:st|nd|rd|th)?"

    match = re.search(rf"\b{months_pat}\s+{days_pat}(?:\s*(?:or|and|to|-)\s*{days_pat})?\b", lower, re.I)
    if match:
        return raw[match.start() : match.end()]

    match = re.search(rf"\b{days_pat}\s+{months_pat}(?:\s+\d{{4}})?\b", lower, re.I)
    if match:
        return raw[match.start() : match.end()]

    match = re.search(rf"\b{months_pat}\b", lower, re.I)
    if match:
        return raw[match.start() : match.end()]

    # Keep richer context when the message is already a short relative date answer
    if re.search(r"\b(week|month|next|early|mid|late)\b", lower):
        words = raw.split()
        if len(words) <= 8:
            return raw

    match = re.search(rf"\b{days_pat}\b", lower, re.I)
    if match:
        return raw[match.start() : match.end()]

    words = raw.split()
    if len(words) <= 4:
        return raw
    return " ".join(words[:3]).strip().rstrip(".,!?")


def extract_guest_count(text: str) -> str | int:
    """Preserve guest ranges like 30-50 / 200 to 300; otherwise store a single number."""
    raw = text.strip()
    scoped_range = re.search(
        r"(\d+)\s*(?:-|–|—|to|and)\s*(\d+)\s*(?:guests?|people|pax)",
        raw,
        re.I,
    )
    if scoped_range:
        return f"{scoped_range.group(1)} to {scoped_range.group(2)}"
    scoped_single = re.search(r"(\d+)\s*(?:guests?|people|pax)\b", raw, re.I)
    if scoped_single:
        return int(scoped_single.group(1))
    range_match = re.search(
        r"(?:around\s+|about\s+|approx(?:imately)?\s+|roughly\s+)?"
        r"(\d+)\s*(?:-|–|—|to|and)\s*(\d+)",
        raw,
        re.I,
    )
    if range_match:
        low, high = range_match.group(1), range_match.group(2)
        return f"{low} to {high}"
    single = re.search(r"(\d+)", raw)
    if single:
        return int(single.group(1))
    return raw[:60] if raw else 100


def infer_meal_preference(session: ConversationSession) -> list[str] | None:
    all_text = " ".join([m["content"] for m in session.history if m["role"] == "user"]).lower()
    inferred = []
    if "dinner" in all_text:
        inferred.append("Dinner")
        inferred.append("Dessert")
    elif "lunch" in all_text:
        inferred.append("Lunch")
    elif "breakfast" in all_text:
        inferred.append("Breakfast")
    elif "snacks" in all_text or "high tea" in all_text or "tea time" in all_text or "tea" in all_text:
        inferred.append("Snacks")
        inferred.append("Tea")
    return inferred if inferred else None


def _store_detail_field(session: ConversationSession, key: str, user_text: str) -> bool:
    from app.services.dish_flow import _preferences_to_items

    value: str | int | None = user_text.strip()
    if not value:
        return False
    if key == "event_date":
        value = extract_date_entity(user_text)
    if key == "guest_count":
        value = extract_guest_count(user_text)
    if key == "meal_preference":
        lower = user_text.lower()
        selected = []
        if "dinner" in lower:
            selected.append("Dinner")
            selected.append("Dessert")
        if "lunch" in lower:
            selected.append("Lunch")
        if "breakfast" in lower:
            selected.append("Breakfast")
        if "snacks" in lower or "tea" in lower or "coffee" in lower:
            selected.append("Snacks")
            selected.append("Tea")
        if not selected:
            selected = ["Lunch", "Dinner"]
        session.selected_dishes = _preferences_to_items(selected)
        value = ", ".join(selected)
    if key == "event_location":
        value = extract_location_entity(str(value))
    if key == "preferred_callback":
        value = normalize_callback_label(str(value))
    session.fields = EnquiryFields(**{**session.fields.model_dump(), key: value})
    return True


def _last_bot_asked_move_further(session: ConversationSession) -> bool:
    for msg in reversed(session.history):
        if msg.get("role") == "assistant":
            return "move further" in (msg.get("content") or "").lower()
        if msg.get("role") == "user":
            break
    return False


def _start_detail_collection(session: ConversationSession, user_text: str) -> AgentTurnResult:
    move_to(session, GuidedStep.COLLECT_DETAILS)
    first_prompt = _next_detail_prompt(session)
    name = session.fields.customer_name or "there"
    occasion = (_event_label(session) or "celebration").lower()
    # Prefer natural "When is your wedding?" style openers
    reply = random.choice(
        (
            f"Sure, {name}! {first_prompt}",
            f"Sounds good. {first_prompt}",
            f"Perfect. {first_prompt}",
            first_prompt or f"When is your {occasion}?",
        )
    )
    track_question(session, reply, slot_key=_next_detail_key(session))
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


async def process_guided_flow(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
) -> AgentTurnResult | None:
    text = user_text.strip()
    hydrate_memory(session)
    before_fields = session.fields.model_dump()

    # 1) RECOVERY CHECK (Kannan.rules.txt Global FSM + State 5 circuit breaker)
    if is_reset_message(text) or should_trip_circuit_breaker(session):
        reset_session_to_greeting(session)
        reply = circuit_breaker_reply()
        track_question(session, reply, slot_key="customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if is_unsupported_event_request(text):
        reply = unsupported_event_refusal(customer_name=session.fields.customer_name)
        move_to(session, GuidedStep.DONE)
        session.completed = True
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    extracted = extract_entities(text, session)
    apply_entities(session, extracted)
    advance_from_slots(session)
    step = session.guided_step
    newly_collected = [
        key for key, value in session.fields.model_dump().items()
        if before_fields.get(key) in (None, "") and value not in (None, "")
    ]

    if step == GuidedStep.DONE:
        return None

    if step == GuidedStep.AWAIT_HI:
        name = extract_name(text)
        event_type = _detect_event(text, name=name)

        if name:
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
            if event_type:
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
                move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
                reply = _event_showcase_message(event_type, with_images=False)
            else:
                move_to(session, GuidedStep.AWAIT_EVENT_TYPE)
                reply = _company_intro_message(name)
        elif is_greeting_only(text):
            move_to(session, GuidedStep.AWAIT_NAME)
            reply = welcome_message()
        elif looks_like_question(text) or wants_more_info(text) or is_portfolio_inquiry(text):
            move_to(session, GuidedStep.AWAIT_NAME)
            if is_portfolio_inquiry(text):
                reply = f"{catalog_portfolio_reply()}\n\n{_ask_name_again(text)}"
            else:
                reply = (
                    "Happy to help with that. "
                    f"{_ask_name_again(text)}"
                )
            record_slot_failure(session, slot_key="customer_name")
        else:
            if event_type:
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
            move_to(session, GuidedStep.AWAIT_NAME)
            reply = acknowledge_opening_without_name(text, event_type)

        track_question(session, reply, slot_key="customer_name" if session.guided_step == GuidedStep.AWAIT_NAME else None)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_NAME:
        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_greeting_only(text):
            reply = welcome_message()
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Never treat questions / portfolio asks as a name (Fix 5)
        if looks_like_question(text) or wants_more_info(text) or is_portfolio_inquiry(text):
            record_slot_failure(session, slot_key="customer_name")
            if is_portfolio_inquiry(text):
                reply = f"{catalog_portfolio_reply()}\n\n{_ask_name_again(text)}"
            else:
                reply = f"Happy to help. {_ask_name_again(text)}"
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        name = extract_name(text)
        if not name or name.lower() in SKIP_NAMES:
            record_slot_failure(session, slot_key="customer_name")
            reply = _ask_name_again(text)
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        clear_slot_failures(session, "customer_name")

        # Clear bogus event types that were actually someone's name
        stored = session.fields.event_type
        if stored and (not is_known_event_type(stored) or stored.lower() == name.lower()):
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": None})

        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
        maybe_event = _detect_event(text, name=name)

        if is_known_event_type(session.fields.event_type):
            move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
            showcase = _event_showcase_message(session.fields.event_type, with_images=False)
            reply = f"Lovely to connect with you, {name}! 😊\n\n{showcase}"
        elif maybe_event:
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": maybe_event})
            move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
            showcase = _event_showcase_message(maybe_event, with_images=False)
            reply = f"Lovely to connect with you, {name}! 😊\n\n{showcase}"
        else:
            move_to(session, GuidedStep.AWAIT_EVENT_TYPE)
            reply = _company_intro_message(name)
        track_question(session, reply, slot_key="event_type" if session.guided_step == GuidedStep.AWAIT_EVENT_TYPE else None)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_EVENT_TYPE:
        if is_greeting_only(text) and session.fields.customer_name:
            reply = (
                f"Hello {session.fields.customer_name}! 😊 How can we help bring your celebration to life today? "
                "Are you planning a wedding, an Upanayanam, a housewarming, or another special occasion?"
            )
            track_question(session, reply, slot_key="event_type")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_undecided(text):
            reply = undecided_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_small_talk(text):
            reply = small_talk_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Fix 2: catalog / portfolio stay in State 2
        if is_portfolio_inquiry(text) or (wants_more_info(text) and not _detect_event(text, name=session.fields.customer_name)):
            reply = catalog_portfolio_reply(customer_name=session.fields.customer_name)
            # Answered successfully — do not burn the loop / failure budget
            session.consecutive_loop_count = 0
            session.last_asked_slot = "event_type"
            session.last_assistant_question = reply
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if looks_like_polite_filler(text) or customer_wants_to_proceed(text) or len(text.strip()) < 3:
            reply = random.choice(
                (
                    "Sure, wedding, house warming, birthday, or something else?",
                    "What type of event are you planning?",
                    "Is it a wedding or something else?",
                )
            )
            track_question(session, reply, slot_key="event_type")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        event_type = _detect_event(text, name=session.fields.customer_name)
        if not event_type:
            record_slot_failure(session, slot_key="event_type")
            fails = slot_fail_count(session, "event_type")
            if fails >= 2:
                move_to(session, GuidedStep.COLLECT_DETAILS)
                _fill_pending_for_callback(session)
                reply = callback_pivot_prompt(name=session.fields.customer_name)
            else:
                reply = random.choice(
                    (
                        "Got it, is it a wedding, house warming, birthday, or something else?",
                        "What celebration is this for?",
                    )
                )
            track_question(session, reply, slot_key="event_type" if fails < 2 else "preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        clear_slot_failures(session, "event_type")
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
        move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
        reply = _event_showcase_message(event_type, with_images=False)
        session.showcase_prompted = True
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields, media=[])

    if step == GuidedStep.AWAIT_POST_SHOWCASE:
        # Entity sweep may have just filled event_type and advanced here — still show showcase once.
        if "event_type" in newly_collected and not session.showcase_prompted:
            session.showcase_prompted = True
            reply = _event_showcase_message(session.fields.event_type, with_images=False)
            track_question(session, reply)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields, media=[])

        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_undecided(text):
            reply = undecided_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_small_talk(text):
            reply = small_talk_reply(event_label=_event_label(session))
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_discuss_on_call(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            _fill_pending_for_callback(session)
            reply = callback_pivot_prompt(name=session.fields.customer_name)
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_straight_to_planning(text) or wants_to_move_further(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            reply = planning_date_prompt()
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_showcase_look(text) or customer_wants_photos(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            profile = get_event_profile(session.fields.event_type)
            showcase = profile["showcase"]
            reply = (
                f"We’d love to show you! {showcase}\n\n"
                f"You can explore our portfolio anytime at **srivatsanka.com**.\n\n"
                f"{planning_date_prompt()}"
            )
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Info / "more details" / topic asks → answer once (no second question), then date
        move_to(session, GuidedStep.COLLECT_DETAILS)
        date_ask = planning_date_prompt()
        if (
            looks_like_question(text)
            or wants_more_info(text)
            or is_service_topic_reply(text)
            or _is_custom_request(text)
        ):
            if wants_more_info(text) and not is_service_topic_reply(text):
                # Broad "more details" → Intent A style summary, then date (rules State 3)
                profile = get_event_profile(session.fields.event_type)
                answered = (
                    f"Absolutely! {profile['showcase']} "
                    f"You can also browse menus and setups at **srivatsanka.com**."
                )
            else:
                answered = await answer_showcase_question(session, text)
            if _is_custom_request(text):
                answered = handle_custom_request(session, text, answered)
            reply = f"{answered}\n\n{date_ask}"
        else:
            reply = (
                f"Got it! Let's jump straight into the planning details.\n\n{date_ask}"
            )
            reply = handle_custom_request(session, text, reply)
        track_question(session, reply, slot_key="event_date")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)



    if step == GuidedStep.COLLECT_DETAILS:
        _skip_inapplicable_fields(session)

        if "event_date" in newly_collected and "guest_count" not in newly_collected:
            if is_urgent_event_date(str(session.fields.event_date or text)):
                _fill_pending_for_callback(session)
                session.fields = EnquiryFields(
                    **{**session.fields.model_dump(), "preferred_callback": "Immediately"}
                )
                return _complete_enquiry_reply(
                    session,
                    whatsapp_id,
                    text,
                    lead=urgent_timeline_reply(),
                )
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = natural_field_ack(
                    "event_date",
                    str(session.fields.event_date),
                    next_prompt,
                    event_type=session.fields.event_type,
                )
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if "event_location" in newly_collected and "preferred_callback" not in newly_collected:
            location_value = str(session.fields.event_location or "")
            if "Venue Selection Needed" in location_value:
                reply = _venue_help_callback_prompt(location_value.replace(" (Venue Selection Needed)", ""))
                session.fields = EnquiryFields(
                    **{**session.fields.model_dump(), "preferred_callback": None}
                )
                track_question(session, reply, slot_key="preferred_callback")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_discuss_on_call(text) and session.fields.preferred_callback is None:
            _fill_pending_for_callback(session)
            reply = callback_pivot_prompt(name=session.fields.customer_name)
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        for key in DETAIL_KEYS:
            if getattr(session.fields, key) is not None:
                continue

            prompt = detail_question(key, event_type=session.fields.event_type)

            if is_thanks_only(text):
                reply = f"{thanks_reply()} {prompt}"
                reply = handle_custom_request(session, text, reply)
                track_question(session, reply, slot_key=key)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if is_undecided(text):
                reply = f"{undecided_reply()} {prompt}"
                reply = handle_custom_request(session, text, reply)
                track_question(session, reply, slot_key=key)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if is_small_talk(text):
                reply = f"{small_talk_reply(event_label=_event_label(session))} {prompt}"
                reply = handle_custom_request(session, text, reply)
                track_question(session, reply, slot_key=key)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            # Info / topic replies first (e.g. "food") — never treat as a failed date/slot.
            if (
                wants_more_info(text)
                or is_service_topic_reply(text)
                or (looks_like_question(text) and not is_likely_field_answer(text, key))
                or _is_custom_request(text)
            ):
                if _is_custom_request(text):
                    answered = handle_custom_request(session, text, "")
                    reply = f"{answered}\n\n{prompt}".strip() if answered else prompt
                else:
                    answered = await answer_details_question(session, text, None)
                    # Answer the topic, then re-ask the pending field once (no "share that again")
                    reply = f"{answered}\n\n{prompt}"
                session.consecutive_loop_count = 0
                session.last_asked_slot = key
                session.last_assistant_question = reply
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not is_likely_field_answer(text, key):
                # Fix 6: clarify once → callback offer → circuit breaker (via failed_turns >= 3)
                fails = record_slot_failure(session, slot_key=key)
                slot_fails = slot_fail_count(session, key)
                if fails >= 3 or should_trip_circuit_breaker(session):
                    reset_session_to_greeting(session)
                    reply = circuit_breaker_reply()
                    track_question(session, reply, slot_key="customer_name")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                if slot_fails >= 2:
                    _fill_pending_for_callback(session)
                    reply = callback_pivot_prompt(name=session.fields.customer_name)
                    reply = handle_custom_request(session, text, reply)
                    track_question(session, reply, slot_key="preferred_callback")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                reply = f"Could you share that again? {prompt}"
                reply = handle_custom_request(session, text, reply)
                if repeated_question(session, reply):
                    reply = f"No worries, take your time. {prompt}"
                track_question(session, reply, slot_key=key)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not _store_detail_field(session, key, text):
                fails = record_slot_failure(session, slot_key=key)
                if fails >= 3 or should_trip_circuit_breaker(session):
                    reset_session_to_greeting(session)
                    reply = circuit_breaker_reply()
                    track_question(session, reply, slot_key="customer_name")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                if slot_fail_count(session, key) >= 2:
                    _fill_pending_for_callback(session)
                    reply = callback_pivot_prompt(name=session.fields.customer_name)
                    track_question(session, reply, slot_key="preferred_callback")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                reply = f"Could you share that again? {prompt}"
                reply = handle_custom_request(session, text, reply)
                track_question(session, reply, slot_key=key)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            clear_slot_failures(session, key)
            # Urgent timeline: skip remaining details and complete with immediate callback
            if key == "event_date" and is_urgent_event_date(str(session.fields.event_date or text)):
                _fill_pending_for_callback(session)
                session.fields = EnquiryFields(
                    **{**session.fields.model_dump(), "preferred_callback": "Immediately"}
                )
                return _complete_enquiry_reply(
                    session,
                    whatsapp_id,
                    text,
                    lead=urgent_timeline_reply(),
                )

            _skip_inapplicable_fields(session)
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                stored = getattr(session.fields, key) or text
                reply = natural_field_ack(
                    key,
                    str(stored),
                    next_prompt,
                    event_type=session.fields.event_type,
                )
                reply = handle_custom_request(session, text, reply)
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            break

        if not _details_complete(session):
            prompt = _next_detail_prompt(session)
            reply = prompt or "Could you share a bit more?"
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key=_next_detail_key(session))
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        return _complete_enquiry_reply(session, whatsapp_id, text)

    return None
