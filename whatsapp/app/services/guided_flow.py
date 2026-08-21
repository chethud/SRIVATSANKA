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
    clean_person_name,
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
    ask_event_date_only,
    ask_move_further_prompt,
    asks_callback_timing,
    callback_confirmation_reply,
    callback_pivot_prompt,
    callback_timing_reply,
    catalog_portfolio_reply,
    detail_question,
    immediate_callback_reply,
    intent_b_planning_reply,
    is_name_confirm_no,
    is_name_confirm_yes,
    is_portfolio_inquiry,
    customer_says_already_provided,
    is_food_menu_question,
    is_meal_type_answer,
    is_short_planning_ack,
    is_service_topic_reply,
    is_small_talk,
    is_thanks_only,
    is_undecided,
    is_unsupported_event_request,
    looks_like_polite_filler,
    name_confirm_prompt,
    name_confirmed_event_ask,
    name_reask_prompt,
    normalize_meal_label,
    sanitize_customer_reply,
    showcase_followup_date_ask,
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
from app.services.session_store import ConversationSession, GuidedStep, SlotValue
from app.services.event_date import (
    ambiguous_date_confirm_prompt,
    extract_date_snippet,
    has_service_planning_intent,
    is_ambiguous_date_phrase,
    is_urgent_event_date,
    suggest_ambiguous_date,
)
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
    soft_reset_session,
    track_question,
)
from app.services.website_gallery import customer_wants_photos, mark_gallery_sent, prepare_gallery_photos
from app.services.whatsapp_client import normalize_phone
from app.services import reply_pack

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
    data = session.fields.model_dump()
    cname = (data.get("customer_name") or session.pending_name or "").strip().lower()
    loc = str(data.get("event_location") or "").strip()
    if loc and (
        loc.lower() == cname
        or loc.lower() in {"yes", "no", "hey", "hi", "hello"}
        or loc.lower() == str(data.get("event_type") or "").strip().lower()
    ):
        session.fields = EnquiryFields(**{**data, "event_location": None})
        data = session.fields.model_dump()
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
    for key in DETAIL_KEYS:
        value = getattr(session.fields, key)
        if value is None:
            return False
        if key == "preferred_callback" and is_meal_type_answer(str(value)):
            return False
    return True


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
    _fill_pending_for_callback(session)
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
    if is_meal_type_answer(callback_label):
        data = session.fields.model_dump()
        if data.get("meal_preference") in (None, ""):
            data["meal_preference"] = normalize_meal_label(callback_label)
        data["preferred_callback"] = None
        session.fields = EnquiryFields(**data)
        move_to(session, GuidedStep.COLLECT_DETAILS)
        prompt = callback_pivot_prompt(name=session.fields.customer_name)
        reply = f"Perfect. I've noted {data['meal_preference']} for your event.\n\n{prompt}"
        track_question(session, reply, slot_key="preferred_callback")
        record_exchange(session, user_text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
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
    return name_confirmed_event_ask(name)


def _confirm_and_store_name(session: ConversationSession, name: str) -> None:
    cleaned = clean_person_name(name) or (name or "").strip()
    session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": cleaned})
    session.pending_name = None
    session.name_confirmed = True
    clear_slot_failures(session, "customer_name")
    slot = session.slots.setdefault("customer_name", SlotValue())
    slot.value = cleaned
    slot.confidence = 1.0
    slot.collected = True


def _reply_after_name_confirmed(session: ConversationSession, user_text: str) -> AgentTurnResult:
    name = session.fields.customer_name or "there"
    if is_known_event_type(session.fields.event_type):
        move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
        reply = _event_showcase_message(session.fields.event_type, with_images=False)
        session.showcase_prompted = True
    else:
        move_to(session, GuidedStep.AWAIT_EVENT_TYPE)
        reply = name_confirmed_event_ask(name)
    track_question(
        session,
        reply,
        slot_key=None if session.fields.event_type else "event_type",
    )
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields, media=[])


def _start_name_confirmation(
    session: ConversationSession,
    name: str,
    user_text: str,
    *,
    event_type: str | None = None,
) -> AgentTurnResult:
    session.pending_name = clean_person_name(name) or extract_name(user_text) or name.strip()
    session.name_confirmed = False
    # Keep name pending until Yes — do not finalize customer_name yet
    if session.fields.customer_name:
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": None})
    if event_type and is_known_event_type(event_type):
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
    move_to(session, GuidedStep.AWAIT_NAME_CONFIRM)
    reply = name_confirm_prompt(session.pending_name)
    track_question(session, reply, slot_key="customer_name")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _event_showcase_message(event_type: str, *, with_images: bool = False) -> str:
    packed = reply_pack.get_reply("state3.showcase_choice", event_type=event_type)
    if packed:
        return packed
    profile = get_event_profile(event_type)
    validation = profile["validation"]
    return (
        f"{validation}\n\n"
        "Before we start planning the date and venue, do you need any information about us? I can share past setups, signature cuisines, and how we work, or we can go straight to your event details."
    )


def _intent_b_reply(text: str, session: ConversationSession) -> str:
    """State 3 Intent B (direct planning) reply, JSON-first (Kannan.rules.txt)."""
    from app.services.human_style import normalize_customer_text

    t = normalize_customer_text(text)
    name = session.fields.customer_name
    event_type = session.fields.event_type
    if t in {"no", "nope", "skip", "nah"} or t.startswith("no "):
        reply_id = "state3.intent_b_no"
    elif t in {"ok", "okay", "k", "okk", "fine"}:
        reply_id = "state3.intent_b_ok"
    elif (name or "").strip():
        reply_id = "state3.intent_b_named"
    else:
        reply_id = "state3.fallback_intent_b"
    packed = reply_pack.get_reply(reply_id, name=name, event_type=event_type)
    if packed:
        return packed
    return intent_b_planning_reply(text=text, name=name, event_type=event_type)


def _showcase_followup_text(session: ConversationSession) -> str:
    """Follow-up after photos/showcase — never re-ask for a date already provided."""
    if session.fields.event_date:
        next_prompt = _next_detail_prompt(session)
        name = session.fields.customer_name or "there"
        noted = (
            f"Your date of {session.fields.event_date} is already noted, {name}. "
            "Sorry if we asked again."
        )
        return f"{noted}\n\n{next_prompt}" if next_prompt else noted
    return showcase_followup_date_ask(event_type=session.fields.event_type)


def _intent_a_showcase_payload(session: ConversationSession, text: str) -> tuple[str, list]:
    """JSON showcase copy + grouped event photos (Kannan.rules.txt Intent A)."""
    reply = reply_pack.get_reply("state3.intent_a", event_type=session.fields.event_type)
    if not reply:
        profile = get_event_profile(session.fields.event_type)
        reply = (
            f"We’d love to show you! {profile['showcase']}\n\n"
            f"You can explore our portfolio anytime at **srivatsanka.com**.\n\n"
            f"{_showcase_followup_text(session)}"
        )
    elif session.fields.event_date and "tentative date" in reply.lower():
        reply = re.sub(
            r"\n*To help us.*tentative date.*\?",
            f"\n\n{_showcase_followup_text(session)}",
            reply,
            flags=re.I | re.S,
        )
    reply = handle_custom_request(session, text, reply)
    media: list[MediaAttachment] = []
    if not session.sent_gallery_urls or customer_wants_photos(text):
        group_name = reply_pack.get_event_profile(session.fields.event_type).get("media_group")
        media = reply_pack.get_media_group(group_name)
        if media:
            mark_gallery_sent(session, [m.url for m in media])
        else:
            media = prepare_gallery_photos(session, user_text=session.fields.event_type)
    return reply, media


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


def extract_date_entity(text: str) -> str | None:
    return extract_date_snippet(text)


def extract_guest_count(text: str) -> str | int:
    """Preserve guest ranges like 30-50 / 200 to 300; otherwise store a single number."""
    raw = text.strip()
    people_match = re.search(r"(\d+)\s*(?:guests?|people|pax)\b", raw, re.I)
    if people_match:
        return int(people_match.group(1))
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
        if not value:
            return False
        if is_ambiguous_date_phrase(str(value)):
            session.pending_date_confirm = str(value)
            return False
    if key == "guest_count":
        value = extract_guest_count(user_text)
        if isinstance(value, str) and len(value.split()) > 6:
            return False
    if key == "meal_preference":
        if is_meal_type_answer(user_text):
            value = normalize_meal_label(user_text)
        else:
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
        if is_meal_type_answer(str(value)):
            return False
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
    text = sanitize_customer_reply(user_text, last_bot_message=session.last_assistant_question)
    hydrate_memory(session)
    before_fields = session.fields.model_dump()

    # 1) RECOVERY CHECK (Kannan.rules.txt Global FSM + State 5 circuit breaker)
    if is_reset_message(text):
        reply = soft_reset_session(session)
        track_question(session, reply, slot_key="customer_name" if not session.name_confirmed else "event_type")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if should_trip_circuit_breaker(session):
        reset_session_to_greeting(session)
        reply = circuit_breaker_reply()
        track_question(session, reply, slot_key="customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if session.pending_date_confirm and is_name_confirm_yes(text):
        confirmed = suggest_ambiguous_date(session.pending_date_confirm) or session.pending_date_confirm
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_date": confirmed})
        session.pending_date_confirm = None
        clear_slot_failures(session, "event_date")
        next_prompt = _next_detail_prompt(session)
        name = session.fields.customer_name or "there"
        reply = f"Perfect, {name}. I've noted {confirmed}."
        if next_prompt:
            reply = f"{reply}\n\n{next_prompt}"
        track_question(session, reply, slot_key=_next_detail_key(session))
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

        if name or session.pending_name:
            return _start_name_confirmation(
                session,
                name or session.pending_name,
                text,
                event_type=event_type,
            )
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

    if step == GuidedStep.AWAIT_NAME_CONFIRM:
        candidate = (session.pending_name or "").strip()
        typed_name = extract_name(text)

        # Message that just provided the candidate name → ask Yes/No
        if candidate and typed_name and typed_name.lower() == candidate.lower():
            reply = name_confirm_prompt(candidate)
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if candidate and is_name_confirm_yes(text) and not (
            typed_name and typed_name.lower() != candidate.lower()
        ):
            _confirm_and_store_name(session, candidate)
            return _reply_after_name_confirmed(session, text)

        if is_name_confirm_no(text):
            if typed_name and (not candidate or typed_name.lower() != candidate.lower()):
                session.pending_name = typed_name
                session.name_confirmed = False
                reply = name_confirm_prompt(typed_name)
                track_question(session, reply, slot_key="customer_name")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            session.pending_name = None
            session.name_confirmed = False
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": None})
            move_to(session, GuidedStep.AWAIT_NAME, force=True)
            reply = name_reask_prompt()
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if typed_name and typed_name.lower() not in SKIP_NAMES:
            session.pending_name = typed_name
            session.name_confirmed = False
            reply = name_confirm_prompt(typed_name)
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if not candidate:
            move_to(session, GuidedStep.AWAIT_NAME, force=True)
            reply = name_reask_prompt()
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        reply = name_confirm_prompt(candidate)
        track_question(session, reply, slot_key="customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_NAME:
        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_greeting_only(text):
            # Warm re-greeting — do not burn the loop budget before the user shares a name.
            reply = welcome_message()
            session.last_assistant_question = reply
            session.last_asked_slot = "customer_name"
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

        name = extract_name(text) or (session.pending_name or "")
        if not name or name.lower() in SKIP_NAMES:
            record_slot_failure(session, slot_key="customer_name")
            if session.fields.event_type:
                reply = acknowledge_opening_without_name(text, session.fields.event_type)
            else:
                reply = _ask_name_again(text)
            track_question(session, reply, slot_key="customer_name")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Clear bogus event types that were actually someone's name
        stored = session.fields.event_type
        if stored and (not is_known_event_type(stored) or stored.lower() == name.lower()):
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": None})

        maybe_event = _detect_event(text, name=name)
        return _start_name_confirmation(session, name, text, event_type=maybe_event)

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
        if (
            session.fields.event_type
            and event_type
            and event_type.lower() != session.fields.event_type.lower()
            and not session.pending_event_type_switch
        ):
            session.pending_event_type_switch = event_type
            reply = (
                f"Of course. Just to confirm, is this a new enquiry for {event_type.lower()} "
                f"instead of the {session.fields.event_type.lower()} enquiry you mentioned earlier?"
            )
            track_question(session, reply, slot_key="event_type")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if session.pending_event_type_switch and is_name_confirm_yes(text):
            event_type = session.pending_event_type_switch
            session.pending_event_type_switch = None
            clear_slot_failures(session, "event_type")
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
            move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
            reply = _event_showcase_message(event_type, with_images=False)
            session.showcase_prompted = True
            track_question(session, reply)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields, media=[])

        if not event_type:
            record_slot_failure(session, slot_key="event_type")
            fails = slot_fail_count(session, "event_type")
            if fails >= 2:
                move_to(session, GuidedStep.COLLECT_DETAILS)
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
            reply = callback_pivot_prompt(name=session.fields.customer_name)
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Intent A first: Yes / Sure / show photos → past setups (Kannan.rules.txt)
        if wants_showcase_look(text) or customer_wants_photos(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            reply, media = _intent_a_showcase_payload(session, text)
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields, media=media)

        if customer_says_already_provided(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            name = session.fields.customer_name or "there"
            if session.fields.event_date:
                reply = (
                    f"You're right, {name}. You already mentioned {session.fields.event_date}. "
                    "Sorry about that — I've noted it and won't ask again."
                )
                next_prompt = _next_detail_prompt(session)
                if next_prompt:
                    reply = f"{reply}\n\n{next_prompt}"
            else:
                reply = f"Sorry about that, {name}. Could you share your tentative date once more?"
            if wants_showcase_look(text) or customer_wants_photos(text):
                showcase_reply, media = _intent_a_showcase_payload(session, text)
                reply = f"{reply}\n\n{showcase_reply}"
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_straight_to_planning(text) or wants_to_move_further(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            reply = _intent_b_reply(text, session)
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Info / "more details" / topic asks → answer once (no second question), then date
        move_to(session, GuidedStep.COLLECT_DETAILS)
        date_ask = "" if session.fields.event_date else ask_event_date_only(event_type=session.fields.event_type)
        if (
            looks_like_question(text)
            or wants_more_info(text)
            or is_service_topic_reply(text)
            or _is_custom_request(text)
        ):
            if wants_showcase_look(text) or customer_wants_photos(text):
                reply, media = _intent_a_showcase_payload(session, text)
                track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)
            if wants_more_info(text) and not is_service_topic_reply(text):
                # Broad "more details" → Intent A style summary, then date (rules State 3)
                profile = get_event_profile(session.fields.event_type)
                answered = (
                    f"Absolutely! {profile['showcase']} "
                    f"You can also browse menus and setups at **srivatsanka.com**."
                )
                date_ask = _showcase_followup_text(session) if session.fields.event_date else showcase_followup_date_ask(
                    event_type=session.fields.event_type
                )
            else:
                answered = await answer_showcase_question(session, text)
            if _is_custom_request(text):
                answered = handle_custom_request(session, text, answered)
            reply = f"{answered}\n\n{date_ask}".strip() if date_ask else answered
        else:
            # Intent B fallback (ok / emoji / unclassifiable) — one reply only, JSON-first
            reply = _intent_b_reply(text, session)
            reply = handle_custom_request(session, text, reply)
        track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
        if not repeated_question(session, reply):
            record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)



    if step == GuidedStep.COLLECT_DETAILS:
        _skip_inapplicable_fields(session)

        if asks_callback_timing(text):
            reply = callback_timing_reply(
                preferred_callback=session.fields.preferred_callback,
                name=session.fields.customer_name,
            )
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if customer_says_already_provided(text):
            name = session.fields.customer_name or "there"
            if session.fields.event_date:
                reply = (
                    f"You're right, {name}. You already mentioned {session.fields.event_date}. "
                    "Sorry about that — I've noted it."
                )
                next_prompt = _next_detail_prompt(session)
                if next_prompt:
                    reply = f"{reply}\n\n{next_prompt}"
            else:
                reply = f"Sorry about that, {name}. Could you share your tentative date once more?"
            if wants_showcase_look(text) or customer_wants_photos(text):
                showcase_reply, media = _intent_a_showcase_payload(session, text)
                reply = f"{reply}\n\n{showcase_reply}"
                track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_short_planning_ack(text):
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = next_prompt
                clear_slot_failures(session, _next_detail_key(session))
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        from app.services.human_style import normalize_customer_text

        if normalize_customer_text(text) in {"no", "nope", "nah"}:
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = f"Sure, no problem. {next_prompt}"
                clear_slot_failures(session, _next_detail_key(session))
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if session.pending_date_confirm is None and is_ambiguous_date_phrase(text) and _next_detail_key(session) == "event_date":
            session.pending_date_confirm = text.strip()
            reply = ambiguous_date_confirm_prompt(text, event_type=session.fields.event_type)
            track_question(session, reply, slot_key="event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_food_menu_question(text):
            pending = _next_detail_prompt(session)
            answered = await answer_details_question(session, text, None)
            reply = f"{answered}\n\n{pending}".strip() if pending else answered
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if has_service_planning_intent(text):
            pending = _next_detail_prompt(session)
            reply = (
                "Got it — we'll focus on catering and decorations for you, and you can manage the venue side."
            )
            reply = handle_custom_request(session, text, reply)
            if pending:
                reply = f"{reply}\n\n{pending}"
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_showcase_look(text) or customer_wants_photos(text):
            reply, media = _intent_a_showcase_payload(session, text)
            pending = _next_detail_prompt(session)
            if pending and session.fields.event_date:
                reply = handle_custom_request(session, text, f"{reply}\n\n{pending}")
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields, media=media)

        if "event_date" in newly_collected and "guest_count" not in newly_collected:
            if is_urgent_event_date(str(session.fields.event_date or text)):
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

        # Entity sweep already captured guest count this turn — ack and ask venue (do not also
        # treat the same message as a location).
        if "guest_count" in newly_collected and "event_location" not in newly_collected:
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = natural_field_ack(
                    "guest_count",
                    str(session.fields.guest_count),
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
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = natural_field_ack(
                    "event_location",
                    location_value,
                    next_prompt,
                    event_type=session.fields.event_type,
                )
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if "meal_preference" in newly_collected and "preferred_callback" not in newly_collected:
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = natural_field_ack(
                    "meal_preference",
                    str(session.fields.meal_preference or text),
                    next_prompt,
                    event_type=session.fields.event_type,
                )
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_discuss_on_call(text) and session.fields.preferred_callback is None:
            reply = callback_pivot_prompt(name=session.fields.customer_name)
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if "preferred_callback" in newly_collected:
            next_prompt = _next_detail_prompt(session)
            callback_label = str(session.fields.preferred_callback or text)
            if next_prompt:
                reply = f"Noted! I've noted your callback preference as {callback_label}.\n\n{next_prompt}"
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            return _complete_enquiry_reply(session, whatsapp_id, text)

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
                or (looks_like_question(text) and not is_likely_field_answer(text, key, last_asked_slot=session.last_asked_slot))
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

            if not is_likely_field_answer(text, key, last_asked_slot=session.last_asked_slot):
                # Meal answers must never fill the callback slot.
                if key == "preferred_callback" and is_meal_type_answer(text):
                    if session.fields.meal_preference is None:
                        _store_detail_field(session, "meal_preference", text)
                    next_prompt = callback_pivot_prompt(name=session.fields.customer_name)
                    meal = session.fields.meal_preference or normalize_meal_label(text)
                    reply = f"Perfect. I've noted {meal} for your event.\n\n{next_prompt}"
                    track_question(session, reply, slot_key="preferred_callback")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
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
