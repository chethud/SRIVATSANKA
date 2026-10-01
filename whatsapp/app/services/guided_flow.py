from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
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
    ask_alternative_callback_number,
    ask_move_further_prompt,
    asks_callback_timing,
    callback_confirmation_reply,
    callback_pivot_prompt,
    callback_timing_reply,
    callback_time_prompt,
    catalog_portfolio_reply,
    confirm_noon_prompt,
    confirm_callback_number_prompt,
    continue_event_details_prompt,
    cuisine_options_reply,
    detail_question,
    immediate_callback_reply,
    intent_b_planning_reply,
    help_options_reply,
    event_date_already_over,
    invalid_event_date_clarify,
    is_ambiguous_yes,
    is_food_menu_question,
    is_help_message,
    is_information_done_command,
    is_information_request,
    is_name_confirm_no,
    is_name_confirm_yes,
    is_portfolio_inquiry,
    customer_says_already_provided,
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
    noted_callback_phone_prompt,
    proceed_with_done_prompt,
    sanitize_customer_reply,
    showcase_followup_date_ask,
    small_talk_reply,
    thanks_reply,
    undecided_reply,
    unsupported_event_refusal,
    urgent_timeline_reply,
    showcase_choice_reply,
    wants_cuisine_options,
    wants_discuss_on_call,
    wants_book_again,
    wants_more_info,
    wants_showcase_look,
    wants_straight_to_planning,
    wants_to_move_further,
    venue_area_prompt,
    warm_enquiry_signoff,
    greeting_ask_name,
    welcome_message,
)
from app.services.session_store import ConversationSession, GuidedStep, SlotValue
from app.services.event_date import (
    ambiguous_date_confirm_prompt,
    extract_date_snippet,
    has_service_planning_intent,
    is_ambiguous_date_phrase,
    is_impossible_calendar_date,
    is_urgent_event_date,
    looks_like_event_date,
    suggest_ambiguous_date,
)
from app.services.location_normalize import extract_location_entity
from app.services.callback_time import (
    callback_has_usable_time,
    compose_callback_label,
    is_immediate_callback,
    normalize_callback_label,
    parse_callback_parts,
)
from app.services.date_picker import (
    EVENT_YEAR_HORIZON,
    YEAR_PAGE_SIZE,
    format_event_date,
    parse_day_id,
    parse_month_id,
    parse_year_id,
    event_date_is_past,
    valid_calendar_day,
)
from app.services.message_intent import (
    extract_phone_number,
    uses_this_whatsapp_number,
)
from app.services.entity_extractor import extract_entities
from app.services.memory_manager import hydrate_memory
from app.services.slot_manager import apply_entities, slot_collected
from app.services.transition_engine import advance_from_slots, move_to
from app.services.validation_layer import (
    cancel_to_main_menu,
    clear_slot_failures,
    greeting_reset_reply,
    is_cancel_message,
    is_reset_message,
    record_slot_failure,
    repeated_question,
    slot_fail_count,
    soft_reset_session,
    track_question,
)
from app.services.website_gallery import customer_wants_photos, mark_gallery_sent, prepare_gallery_photos
from app.services.whatsapp_client import normalize_phone
from app.services.whatsapp_interactive import (
    CALLBACK_ID_TO_LABEL,
    CALLBACK_SLOT_IDS,
    CUISINE_ID_TO_VALUE,
    EDIT_ID_TO_SLOT,
    EVENT_ID_TO_TYPE,
    display_event_label,
)
from app.services import reply_pack

logger = logging.getLogger(__name__)

DETAIL_KEYS = (
    "event_date",
    "guest_count",
    "event_location",
    "meal_preference",
    "special_requirements",
    "preferred_callback",
)

# Meal lunch/dinner/high-tea picker is only for informal gatherings.
MEAL_PICKER_EVENT_KEYS = ("birthday", "family gathering", "family function", "get together", "get-together")


def should_ask_meal_preference(event_type: str | None) -> bool:
    label = (event_type or "").lower()
    return any(key in label for key in MEAL_PICKER_EVENT_KEYS)


def _skip_inapplicable_fields(session: ConversationSession) -> None:
    """Cuisine is collected for every event type via buttons."""
    return


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
    "hlo",
    "hloo",
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
        if key == "special_requirements" and session.special_req_done:
            continue
        return key
    return None


def _next_detail_prompt(session: ConversationSession) -> str | None:
    key = _next_detail_key(session)
    if not key:
        return None
    if key == "event_date":
        if not session.fields.date_status:
            return "Is your event date confirmed, or is it still tentative?"
        if not session.pending_event_year and not session.fields.event_year:
            return "Which year is your event?"
        if not session.pending_event_month and not session.fields.event_month:
            return "Which month?"
        return "Please select the event date."
    if key == "event_location" and (
        session.fields.venue_type == "home"
        or (session.fields.venue_status == "fixed" and not (session.fields.venue_area or session.fields.event_location))
        or (session.fields.venue_name and not session.fields.venue_area and not session.fields.event_location)
    ):
        return venue_area_prompt(venue_name=session.fields.venue_name)
    if key == "preferred_callback":
        if session.pending_ampm_hour == 12 and session.pending_callback_phone_confirm:
            return (
                f"{confirm_noon_prompt()} "
                f"{confirm_callback_number_prompt(whatsapp_id=session.whatsapp_id, name=session.fields.customer_name)}"
            )
        if session.pending_callback_phone_confirm:
            return confirm_callback_number_prompt(
                whatsapp_id=session.whatsapp_id, name=session.fields.customer_name
            )
        if session.pending_alt_callback_phone:
            return ask_alternative_callback_number()
        if session.pending_ampm_hour == 12:
            return confirm_noon_prompt()
        if not session.fields.callback_date:
            return "When would you like our senior planner to call you?"
        if not (session.callback_period or session.fields.callback_time_period):
            return "What time would be convenient for you? Morning, Afternoon, or Evening."
        if not session.fields.callback_time:
            return "What time would you prefer?"
        if session.fields.callback_date and not callback_has_usable_time(
            session.fields.preferred_callback,
            time_label=session.fields.callback_time,
            pending_ampm=bool(session.pending_ampm_hour),
        ):
            return callback_time_prompt(date_label=session.fields.callback_date)
    return detail_question(key, event_type=session.fields.event_type)


def _details_complete(session: ConversationSession) -> bool:
    _skip_inapplicable_fields(session)
    data = session.fields.model_dump()
    required = ("event_type", "guest_count", "event_date", "preferred_callback", "meal_preference")
    for key in required:
        if data.get(key) in (None, ""):
            return False
    if data.get("preferred_callback") and is_meal_type_answer(str(data.get("preferred_callback"))):
        return False
    loc = str(data.get("event_location") or "").strip()
    status = data.get("venue_status")
    if not session.special_req_done and not data.get("special_requirements"):
        return False
    if data.get("venue_type") == "home" and not (data.get("venue_area") or loc):
        return False
    if status == "not_fixed" and not loc:
        return False
    if status != "not_fixed" and (
        not loc
        or loc.lower() in {"our house", "my house", "home"}
        or "already fixed" in loc.lower()
    ):
        return False
    if status == "fixed" and not loc:
        return False
    if session.pending_ampm_hour:
        return False
    if session.pending_callback_phone_confirm or session.pending_alt_callback_phone:
        return False
    if not callback_has_usable_time(
        data.get("preferred_callback"),
        time_label=data.get("callback_time"),
        pending_ampm=bool(session.pending_ampm_hour),
    ):
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
    """Fill only optional meal preference. Never invent venue/date/guest data."""
    data = session.fields.model_dump()
    if data.get("meal_preference") in (None, ""):
        data["meal_preference"] = "To be discussed on call"
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


def _booking_summary_text(session: ConversationSession) -> str:
    f = session.fields
    name = f.customer_name or "there"
    event = display_event_label(f.event_type)
    req = f.special_requirements or "None"
    status = (f.date_status or "").replace("confirmed", "Confirmed").replace("tentative", "Tentative") or "—"
    return (
        f"Wonderful, {name}! 😊\n\n"
        "Here are the details we've noted:\n\n"
        f"🎉 Event: {event}\n"
        f"📅 Event Date: {f.event_date or '—'}\n"
        f"📌 Date Status: {status}\n"
        f"👥 Guests: {f.guest_count or '—'}\n"
        f"📍 Venue Area: {f.venue_area or f.event_location or '—'}\n"
        f"🍽️ Catering: {f.meal_preference or '—'}\n"
        f"✨ Special Requirements: {req}\n"
        f"📞 Planner Callback: {f.preferred_callback or '—'}\n\n"
        "Would you like to confirm these details?"
    )


def _finalize_booking_reply(session: ConversationSession, user_text: str) -> AgentTurnResult:
    name = session.fields.customer_name or "there"
    move_to(session, GuidedStep.DONE)
    reply = (
        f"Thank you, {name}! 😊\n\n"
        "We've received your event inquiry and noted all the details.\n\n"
        "Our senior event planner will contact you at your selected callback time.\n\n"
        "We look forward to helping you make your celebration special! ✨"
    )
    record_exchange(session, user_text, reply)
    return AgentTurnResult(
        reply=reply,
        fields=session.fields,
        enquiry_fields_complete=True,
        is_complete=True,
    )


def _reask_current_slot(session: ConversationSession, user_text: str, asked: str) -> AgentTurnResult:
    if asked in {"callback_date", "preferred_callback"} and not session.fields.callback_date:
        reply = "When would you like our senior planner to call you?"
        track_question(session, reply, slot_key="callback_date")
    elif asked in {"callback_period", "preferred_callback"} and not (
        session.callback_period or session.fields.callback_time_period
    ):
        reply = "What time would be convenient for you? Morning, Afternoon, or Evening."
        track_question(session, reply, slot_key="callback_period")
    elif asked in {"callback_slot", "callback_time"}:
        reply = "What time would you prefer?"
        track_question(session, reply, slot_key="callback_slot")
    else:
        reply = _next_detail_prompt(session) or "Please continue with the date selection."
        track_question(session, reply, slot_key=asked)
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _complete_enquiry_reply(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
    *,
    lead: str | None = None,
) -> AgentTurnResult:
    asked = session.last_asked_slot
    if asked in {
        "event_year",
        "event_month",
        "event_day",
        "event_date_confirm",
        "date_status",
    }:
        return _reask_current_slot(session, user_text, asked)
    _fill_pending_for_callback(session)
    if not _details_complete(session):
        key = _next_detail_key(session) or session.last_asked_slot
        if not key:
            move_to(session, GuidedStep.AWAIT_BOOKING_CONFIRM)
            summary = _booking_summary_text(session)
            track_question(session, summary)
            record_exchange(session, user_text, summary)
            return AgentTurnResult(reply=summary, fields=session.fields)
        next_prompt = _next_detail_prompt(session) or detail_question(
            key,
            event_type=session.fields.event_type,
        )
        track_question(session, next_prompt, slot_key=key)
        record_exchange(session, user_text, next_prompt)
        return AgentTurnResult(reply=next_prompt, fields=session.fields)
    phone = normalize_phone(session.fields.callback_phone or session.fields.phone_number or whatsapp_id)
    session.fields = EnquiryFields(
        **{**session.fields.model_dump(), "phone_number": session.fields.phone_number or phone}
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
    move_to(session, GuidedStep.AWAIT_BOOKING_CONFIRM)
    summary = _booking_summary_text(session)
    reply = f"{lead}\n\n{summary}" if lead else summary
    reply = handle_custom_request(session, user_text, reply)
    track_question(session, reply)
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _send_initial_greeting(session: ConversationSession, user_text: str) -> AgentTurnResult:
    """First inbound message is greeting-only. Never extract or save a name."""
    session.pending_name = None
    session.name_confirmed = False
    if session.fields.customer_name:
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": None})
    move_to(session, GuidedStep.AWAIT_NAME)
    reply = greeting_ask_name()
    track_question(session, reply, slot_key="customer_name")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


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


def _name_is_confident(user_text: str, name: str) -> bool:
    t = (user_text or "").strip()
    if not name or not t:
        return False
    if re.search(r"\b((my\s+)?name\s+is|i\s+am|i'm|\bim\b|this\s+is)\b", t, re.I):
        return True
    cleaned = clean_person_name(t)
    return bool(cleaned) and cleaned.lower() == name.lower() and len(t.split()) <= 3 and not is_greeting_only(t)


def _reply_after_name_confirmed(session: ConversationSession, user_text: str) -> AgentTurnResult:
    name = session.fields.customer_name or "there"
    if is_known_event_type(session.fields.event_type):
        move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
        label = display_event_label(session.fields.event_type)
        reply = f"Would you like to know more about our {label} event services and options?"
        session.showcase_prompted = True
        track_question(session, reply)
    else:
        move_to(session, GuidedStep.AWAIT_EVENT_TYPE)
        reply = name_confirmed_event_ask(name)
        track_question(session, reply, slot_key="event_type")
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


def _strip_event_date_asks(reply: str) -> str:
    text = reply or ""
    text = re.sub(
        r"\n*To help us[^\n]*tentative date[^\n]*\??",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\n*What is your tentative date or month[^\n]*\??",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _with_plan_next(reply: str) -> str:
    cleaned = _strip_event_date_asks(reply)
    lower = cleaned.lower()
    if "plan my event" in lower or "what would you like to do next" in lower:
        return cleaned
    return f"{cleaned}\n\nReady to plan your event?".strip()


def _enter_showing_event_information(session: ConversationSession, reply: str) -> str:
    move_to(session, GuidedStep.SHOWING_EVENT_INFORMATION)
    return _with_plan_next(reply)


def _begin_event_details_after_information(session: ConversationSession) -> str:
    move_to(session, GuidedStep.COLLECT_DETAILS)
    if session.fields.event_date:
        return _next_detail_prompt(session) or ask_event_date_only(
            event_type=session.fields.event_type
        )
    return "Is your event date confirmed, or is it still tentative?"


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


def _with_event_details_option(reply: str) -> str:
    return _with_plan_next(reply)


async def _intent_a_showcase_payload(session: ConversationSession, text: str) -> tuple[str, list]:
    """JSON showcase copy + event photos (uploaded album first, Kannan.rules.txt Intent A)."""
    reply = reply_pack.get_reply("state3.intent_a", event_type=session.fields.event_type)
    if not reply:
        profile = get_event_profile(session.fields.event_type)
        reply = (
            f"We’d love to show you! {profile['showcase']}\n\n"
            f"You can explore our portfolio anytime at **srivatsanka.com**."
        )
    reply = _strip_event_date_asks(reply)
    reply = re.sub(r"\n*Type \*?DONE\*? to proceed\.?\s*", "", reply, flags=re.I).strip()
    reply = handle_custom_request(session, text, reply)
    media: list[MediaAttachment] = []
    if not session.sent_gallery_urls or customer_wants_photos(text):
        media = await prepare_gallery_photos(
            session,
            user_text=text,
            event_type=session.fields.event_type,
        )
        if not media:
            group_name = reply_pack.get_event_profile(session.fields.event_type).get("media_group")
            media = reply_pack.get_media_group(group_name)
            if media:
                mark_gallery_sent(session, [m.url for m in media])
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
        if is_impossible_calendar_date(user_text):
            return False
        value = extract_date_entity(user_text)
        if not value:
            return False
        if is_impossible_calendar_date(str(value)):
            return False
        if is_ambiguous_date_phrase(str(value)):
            session.pending_date_confirm = str(value)
            return False
    if key == "guest_count":
        value = extract_guest_count(user_text)
        if isinstance(value, str) and len(value.split()) > 6:
            return False
    if key == "meal_preference":
        title = user_text.strip()
        mapped = CUISINE_ID_TO_VALUE.get(title)
        if mapped:
            value = mapped
        elif title in set(CUISINE_ID_TO_VALUE.values()):
            value = title
        elif re.search(r"traditional|south indian|north indian|custom menu|not sure|vegetarian", title, re.I):
            value = title
        elif is_meal_type_answer(user_text):
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
            if selected:
                session.selected_dishes = _preferences_to_items(selected)
                value = ", ".join(selected)
            else:
                value = title
    if key == "special_requirements":
        session.special_req_done = True
        session.awaiting_special_req_text = False
        value = user_text.strip()[:500]
    if key == "event_location":
        from app.services.venue_parser import parse_venue_reply

        parsed = parse_venue_reply(user_text)
        data = session.fields.model_dump()
        if parsed.status:
            data["venue_status"] = parsed.status
        if parsed.is_home:
            data["venue_type"] = "home"
            data["venue_name"] = parsed.venue_name or "customer's house"
        if parsed.status == "fixed" and not parsed.location:
            session.fields = EnquiryFields(**data)
            return False
        if not parsed.location:
            session.fields = EnquiryFields(**data)
            return False
        data["venue_area"] = parsed.location
        if data.get("venue_name"):
            value = f"{data['venue_name']}, {parsed.location}"
        else:
            value = parsed.location
        session.fields = EnquiryFields(**{**data, "event_location": value})
        return True
    if key == "preferred_callback":
        if is_meal_type_answer(str(value)):
            return False
        parts = parse_callback_parts(str(value))
        data = session.fields.model_dump()
        if parts.date_label:
            data["callback_date"] = parts.date_label
        if parts.uses_this_number:
            session.pending_callback_phone_confirm = True
            session.pending_alt_callback_phone = False
        if parts.ambiguous_noon:
            session.pending_ampm_hour = 12
            session.fields = EnquiryFields(**data)
            return False
        if parts.time_label:
            data["callback_time"] = parts.time_label
        if parts.immediate:
            data["preferred_callback"] = "Immediately"
            session.fields = EnquiryFields(**data)
            return True
        composed = compose_callback_label(
            date_label=data.get("callback_date"),
            time_label=data.get("callback_time"),
            immediate=False,
        )
        if not callback_has_usable_time(composed, time_label=data.get("callback_time")):
            session.fields = EnquiryFields(**data)
            return False
        data["preferred_callback"] = composed
        session.fields = EnquiryFields(**data)
        return True
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
    if not session.fields.event_date and not session.fields.date_status:
        reply = "Is your event date confirmed, or is it still tentative?"
        track_question(session, reply, slot_key="date_status")
        record_exchange(session, user_text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    first_prompt = _next_detail_prompt(session)
    name = session.fields.customer_name or "there"
    occasion = (_event_label(session) or "celebration").lower()
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


def _edit_distance(left: str, right: str) -> int:
    a, b = left.lower(), right.lower()
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _is_empty_requirement(text: str) -> bool:
    t = re.sub(r"[^a-z]+", " ", (text or "").lower()).strip()
    if not t:
        return True
    if t in {
        "no",
        "n",
        "nope",
        "nah",
        "none",
        "nothing",
        "nil",
        "na",
        "n a",
        "nope nothing",
        "nothing special",
        "no special",
        "no specials",
        "no requirement",
        "no requirements",
        "no special requirement",
        "no special requirements",
        "nothing extra",
    }:
        return True
    return _edit_distance(t.replace(" ", ""), "nothing") <= 2 and len(t) >= 4


def _advance_after_special_requirements(
    session: ConversationSession,
    user_text: str,
    *,
    stored: str,
) -> AgentTurnResult:
    session.special_req_done = True
    session.awaiting_special_req_text = False
    session.fields = EnquiryFields(**{**session.fields.model_dump(), "special_requirements": stored})
    empty = stored.strip().lower() in {"none", "nothing"}
    note = (
        "Thanks! I've noted that you don't have any special requirements. 😊"
        if empty
        else "Thanks! I've noted your requirements."
    )
    reply = f"{note}\n\nWhen would you like our senior planner to call you?"
    track_question(session, reply, slot_key="callback_date")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _set_event_type(session: ConversationSession, event_type: str) -> None:
    session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
    slot = session.slots.setdefault("event_type", SlotValue())
    slot.value = event_type
    slot.confidence = 1.0
    slot.collected = True
    session.showcase_prompted = False
    clear_slot_failures(session, "event_type")


def _ist_today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def _reset_date_picker(session: ConversationSession) -> None:
    session.pending_event_year = None
    session.pending_event_month = None
    session.pending_event_day = None
    session.year_list_offset = 0
    session.month_list_page = 0
    session.day_list_page = 0
    session.pending_date_confirm = None


def _ask_event_year(session: ConversationSession, user_text: str) -> AgentTurnResult:
    tentative = session.fields.date_status == "tentative"
    reply = (
        "Which year are you considering for the event?"
        if tentative
        else "Which year is your event?"
    )
    track_question(session, reply, slot_key="event_year")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _ask_event_month(session: ConversationSession, user_text: str) -> AgentTurnResult:
    tentative = session.fields.date_status == "tentative"
    reply = "Which month are you considering?" if tentative else "Which month?"
    track_question(session, reply, slot_key="event_month")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _ask_event_day(session: ConversationSession, user_text: str) -> AgentTurnResult:
    from calendar import month_name

    year = int(session.pending_event_year or 0)
    month = int(str(session.pending_event_month or "0").split("-")[-1] or 0)
    reply = f"Please select the event date in {month_name[month]} {year}."
    track_question(session, reply, slot_key="event_day")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _past_event_date_turn(
    session: ConversationSession,
    user_text: str,
    *,
    slot_key: str = "event_day",
) -> AgentTurnResult:
    reply = event_date_already_over()
    track_question(session, reply, slot_key=slot_key)
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _ask_confirm_event_date(
    session: ConversationSession,
    user_text: str,
    *,
    year: int,
    month: int,
    day: int,
) -> AgentTurnResult:
    if event_date_is_past(year, month, day):
        return _past_event_date_turn(session, user_text, slot_key="event_day")
    label = format_event_date(year, month, day)
    session.pending_event_year = year
    session.pending_event_month = f"{year:04d}-{month:02d}"
    session.pending_event_day = day
    session.fields = EnquiryFields(
        **{
            **session.fields.model_dump(),
            "event_year": year,
            "event_month": month,
            "event_date": label,
        }
    )
    reply = f"Just to confirm, your event date is {label}."
    track_question(session, reply, slot_key="event_date_confirm")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _continue_after_event_date(session: ConversationSession, user_text: str) -> AgentTurnResult:
    year = int(session.pending_event_year or session.fields.event_year or 0)
    month = int(session.fields.event_month or str(session.pending_event_month or "0").split("-")[-1] or 0)
    day = int(session.pending_event_day or 0)
    if year and month and day and event_date_is_past(year, month, day):
        return _past_event_date_turn(session, user_text, slot_key="event_date_confirm")
    next_prompt = _next_detail_prompt(session)
    label = session.fields.event_date
    reply = f"Perfect. I've noted {label}."
    if next_prompt:
        reply = f"{reply}\n\n{next_prompt}"
    track_question(session, reply, slot_key=_next_detail_key(session))
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _callback_time_from_text(text: str, *, period: str | None = None) -> str | None:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return None
    compact = raw.lower().replace(".", "")
    if re.fullmatch(r"\d{1,2}", raw):
        hour = int(raw)
        if hour == 12:
            return "12 PM"
        if 13 <= hour <= 23:
            return f"{hour - 12} PM"
        if 1 <= hour <= 11:
            if (period or "").lower() == "morning":
                return f"{hour} AM"
            return f"{hour} PM"
        return None
    from app.services.callback_time import parse_callback_parts

    parts = parse_callback_parts(raw)
    if parts.time_label:
        return parts.time_label
    if re.search(r"\b\d{1,2}\s*(am|pm)\b", compact):
        return raw.upper().replace("AM", "AM").replace("PM", "PM")
    return None


def _finish_callback(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
    time_label: str,
) -> AgentTurnResult:
    date_label = session.fields.callback_date or "the selected day"
    period = session.callback_period or session.fields.callback_time_period
    composed = compose_callback_label(date_label=date_label, time_label=time_label) or time_label
    phone = normalize_phone(session.fields.callback_phone or session.fields.phone_number or whatsapp_id)
    session.fields = EnquiryFields(
        **{
            **session.fields.model_dump(),
            "callback_time": time_label,
            "callback_time_period": period,
            "preferred_callback": composed,
            "phone_number": session.fields.phone_number or phone,
        }
    )
    move_to(session, GuidedStep.AWAIT_BOOKING_CONFIRM)
    reply = (
        "Perfect! We've noted your preferred callback time. 😊\n\n"
        f"📅 Callback: {date_label}\n"
        f"⏰ Time: {time_label}\n\n"
        "Our senior event planner will call you on this number.\n\n"
        "Would you like to confirm these details?"
    )
    track_question(session, reply)
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _set_callback_date_and_ask_period(session: ConversationSession, user_text: str, day) -> AgentTurnResult:
    pretty = day.strftime("%d %B %Y") if hasattr(day, "strftime") else str(day)
    session.fields = EnquiryFields(
        **{
            **session.fields.model_dump(),
            "callback_date": pretty,
        }
    )
    session.callback_period = None
    reply = "What time would be convenient for you? Morning, Afternoon, or Evening."
    track_question(session, reply, slot_key="callback_period")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _lock_callback_slot(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
    slot_label: str,
) -> AgentTurnResult:
    return _finish_callback(session, whatsapp_id, user_text, slot_label)


def _is_full_event_date_phrase(text: str) -> bool:
    """True only for day+month (and optional year), never a bare year or day number."""
    raw = (text or "").strip()
    if not raw or re.fullmatch(r"20\d{2}", raw) or re.fullmatch(r"\d{1,2}", raw):
        return False
    if not looks_like_event_date(raw):
        return False
    if re.search(r"\b\d{1,2}[./\-]\d{1,2}(?:[./\-]\d{2,4})?\b", raw):
        return True
    from app.services.event_date import MONTHS

    low = raw.lower()
    has_month = any(re.search(rf"\b{re.escape(name)}\b", low) for name in MONTHS)
    has_day = bool(re.search(r"\b\d{1,2}(st|nd|rd|th)?\b", low))
    return bool(has_month and has_day)


def _ymd_from_text(text: str) -> tuple[int, int, int] | None:
    from app.services.event_date import parse_event_date

    raw = (text or "").strip()
    if not raw or is_impossible_calendar_date(raw):
        return None
    try:
        parsed = parse_event_date(raw)
    except Exception:
        return None
    if not parsed:
        return None
    return parsed.year, parsed.month, parsed.day


def _parse_picker_or_nl_date(session: ConversationSession, text: str) -> AgentTurnResult | None:
    ymd = _ymd_from_text(text)
    if not ymd:
        return None
    year, month, day = ymd
    if not valid_calendar_day(year, month, day):
        return None
    if not session.fields.date_status:
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "date_status": "tentative"})
    return _ask_confirm_event_date(session, text, year=year, month=month, day=day)


async def _handle_event_date_turn(
    session: ConversationSession,
    whatsapp_id: str,
    text: str,
    asked: str,
) -> AgentTurnResult | None:
    from calendar import month_name as cal_month_name

    if asked == "event_date_confirm":
        if is_name_confirm_yes(text) or text.lower().strip() in {"confirm", "ok", "okay"}:
            year = int(session.pending_event_year or session.fields.event_year or 0)
            month = int(session.fields.event_month or str(session.pending_event_month or "0").split("-")[-1] or 0)
            day = int(session.pending_event_day or 0)
            if year and month and day and event_date_is_past(year, month, day):
                return _past_event_date_turn(session, text, slot_key="event_date_confirm")
            return _continue_after_event_date(session, text)
        if is_name_confirm_no(text) or "change" in text.lower():
            data = session.fields.model_dump()
            data["event_date"] = None
            data["event_year"] = None
            data["event_month"] = None
            session.fields = EnquiryFields(**data)
            _reset_date_picker(session)
            return _ask_event_year(session, text)
        return _ask_confirm_event_date(
            session,
            text,
            year=int(session.pending_event_year or session.fields.event_year or 0),
            month=int(session.fields.event_month or str(session.pending_event_month or "0").split("-")[-1] or 0),
            day=int(session.pending_event_day or 1),
        )

    nl = None
    if _is_full_event_date_phrase(text):
        nl = _parse_picker_or_nl_date(session, text)
        if nl is not None:
            return nl

    if asked == "event_year":
        if re.fullmatch(r"20\d{2}", text.strip()):
            year = int(text.strip())
            current = _ist_today().year
            if current <= year <= current + EVENT_YEAR_HORIZON:
                session.pending_event_year = year
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_year": year})
                if session.fields.event_month:
                    session.pending_event_month = f"{year:04d}-{int(session.fields.event_month):02d}"
                    session.day_list_page = 0
                    return _ask_event_day(session, text)
                return _ask_event_month(session, text)
        reply = "Please select a year from the list."
        track_question(session, reply, slot_key="event_year")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if asked == "event_month":
        low = text.strip().lower()
        from app.services.event_date import MONTHS

        month = MONTHS.get(low) or MONTHS.get(low[:3])
        if month and session.pending_event_year:
            year = int(session.pending_event_year)
            session.pending_event_month = f"{year:04d}-{int(month):02d}"
            session.fields = EnquiryFields(
                **{**session.fields.model_dump(), "event_year": year, "event_month": int(month)}
            )
            session.day_list_page = 0
            return _ask_event_day(session, text)
        reply = "Please select a month from the list."
        track_question(session, reply, slot_key="event_month")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if asked == "event_day":
        if re.fullmatch(r"\d{1,2}", text.strip()):
            day = int(text.strip())
            year = int(session.pending_event_year or 0)
            month = int(str(session.pending_event_month or "0").split("-")[-1] or 0)
            if valid_calendar_day(year, month, day):
                return _ask_confirm_event_date(session, text, year=year, month=month, day=day)
            reply = invalid_event_date_clarify()
            track_question(session, reply, slot_key="event_day")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)
        reply = f"Please select a date in {cal_month_name[int(str(session.pending_event_month or '1').split('-')[-1] or 1)]}."
        track_question(session, reply, slot_key="event_day")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if asked == "event_date":
        if not session.pending_event_year:
            return _ask_event_year(session, text)
        if not session.pending_event_month:
            return _ask_event_month(session, text)
        return _ask_event_day(session, text)
    return None


async def _handle_callback_turn(
    session: ConversationSession,
    whatsapp_id: str,
    text: str,
    asked: str,
) -> AgentTurnResult:
    raw = (text or "").strip()
    low = raw.lower()
    slot = asked
    if asked == "preferred_callback":
        slot = "callback_date" if not session.fields.callback_date else (
            "callback_period" if not session.callback_period else "callback_slot"
        )

    if uses_this_whatsapp_number(text) or "this number" in low:
        parts = parse_callback_parts(text)
        if parts.ambiguous_noon:
            session.pending_ampm_hour = 12
        session.pending_callback_phone_confirm = True
        reply = confirm_callback_number_prompt(
            whatsapp_id=whatsapp_id, name=session.fields.customer_name
        )
        if session.pending_ampm_hour == 12:
            reply = f"{confirm_noon_prompt()} {reply}"
        track_question(session, reply, slot_key=slot)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if slot == "callback_date":
        if session.fields.callback_date:
            reply = "What time would be convenient for you? Morning, Afternoon, or Evening."
            track_question(session, reply, slot_key="callback_period")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)
        if "today" in low:
            return await _handle_stable_button(session, whatsapp_id, text, "callback_today")
        if "tomorrow" in low or "tommorow" in low:
            return await _handle_stable_button(session, whatsapp_id, text, "callback_tomorrow")
        if looks_like_event_date(text) and not is_impossible_calendar_date(text):
            ymd = _ymd_from_text(text)
            if ymd:
                from datetime import date as date_cls

                return _set_callback_date_and_ask_period(session, text, date_cls(ymd[0], ymd[1], ymd[2]))
            snippet = extract_date_snippet(text) or text.strip()
            return _set_callback_date_and_ask_period(session, text, snippet)
        reply = "When would you like our senior planner to call you?"
        track_question(session, reply, slot_key="callback_date")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if slot == "callback_period":
        for cid, period in CALLBACK_ID_TO_LABEL.items():
            if period in low and "callback_" not in low:
                return await _handle_stable_button(session, whatsapp_id, text, cid)
        if "exact" in low:
            return await _handle_stable_button(session, whatsapp_id, text, "callback_exact_time")
        if not re.fullmatch(r"\d{1,2}", raw):
            typed = _callback_time_from_text(text, period=session.callback_period)
            if typed:
                return _finish_callback(session, whatsapp_id, text, typed)
        reply = "What time would be convenient for you? Morning, Afternoon, or Evening."
        track_question(session, reply, slot_key="callback_period")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if slot in {"callback_slot", "callback_time"}:
        for cid, label in CALLBACK_SLOT_IDS.items():
            if label.lower().replace("–", "-") in low.replace("–", "-"):
                return await _handle_stable_button(session, whatsapp_id, text, cid)
        typed = _callback_time_from_text(text, period=session.callback_period)
        if typed:
            return _finish_callback(session, whatsapp_id, text, typed)
        reply = "What time would you prefer?"
        track_question(session, reply, slot_key="callback_slot")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    reply = "When would you like our senior planner to call you?"
    track_question(session, reply, slot_key="callback_date")
    record_exchange(session, text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _offer_info_yes_no(session: ConversationSession, user_text: str) -> AgentTurnResult:
    move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
    label = display_event_label(session.fields.event_type)
    reply = f"Would you like to know more about our {label} event services and options?"
    session.showcase_prompted = True
    track_question(session, reply)
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _ask_other_event_name(session: ConversationSession, user_text: str) -> AgentTurnResult:
    move_to(session, GuidedStep.AWAIT_OTHER_EVENT, force=True)
    reply = (
        "Of course! 😊\n\n"
        "What type of event are you planning?\n"
        "Please tell us the name of the event."
    )
    track_question(session, reply, slot_key="event_type")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


def _show_event_type_list(session: ConversationSession, user_text: str, *, extra: str | None = None) -> AgentTurnResult:
    session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": None})
    move_to(session, GuidedStep.AWAIT_EVENT_TYPE, force=True)
    name = session.fields.customer_name or "there"
    reply = extra or f"What type of event are you planning, {name}?"
    track_question(session, reply, slot_key="event_type")
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


async def _handle_stable_button(
    session: ConversationSession,
    whatsapp_id: str,
    text: str,
    button_id: str,
) -> AgentTurnResult | None:
    bid = (button_id or "").strip()
    if not bid:
        return None

    if bid in EVENT_ID_TO_TYPE:
        _set_event_type(session, EVENT_ID_TO_TYPE[bid])
        return _offer_info_yes_no(session, text)
    if bid == "event_other":
        return _ask_other_event_name(session, text)
    if bid in {"name_yes", "info_yes"} and session.guided_step == GuidedStep.AWAIT_NAME_CONFIRM:
        candidate = (session.pending_name or "").strip()
        if candidate:
            _confirm_and_store_name(session, candidate)
            return _reply_after_name_confirmed(session, text)
    if bid == "name_no" and session.guided_step == GuidedStep.AWAIT_NAME_CONFIRM:
        session.pending_name = None
        session.name_confirmed = False
        move_to(session, GuidedStep.AWAIT_NAME, force=True)
        reply = name_reask_prompt()
        track_question(session, reply, slot_key="customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "info_yes":
        reply, media = await _intent_a_showcase_payload(session, text)
        reply = _enter_showing_event_information(session, reply)
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields, media=media)
    if bid == "info_no":
        return _start_detail_collection(session, text)
    if bid == "plan_event":
        return _start_detail_collection(session, text)
    if bid == "back_to_events":
        return _show_event_type_list(session, text)
    if bid == "venue_fixed":
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "venue_status": "fixed"})
        reply = "Please share the venue name."
        track_question(session, reply, slot_key="venue_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "venue_help":
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "venue_status": "not_fixed"})
        reply = "Which city or locality would you prefer for the event?"
        track_question(session, reply, slot_key="venue_area")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid in CUISINE_ID_TO_VALUE:
        value = CUISINE_ID_TO_VALUE[bid]
        if bid == "cuisine_unsure":
            value = "To be discussed"
        _store_detail_field(session, "meal_preference", value)
        if bid == "cuisine_unsure":
            reply = (
                "Perfect! I've noted that you'd like our planner to help you choose.\n\n"
                "Do you have any special requirements or preferences for the event?"
            )
            track_question(session, reply, slot_key="special_requirements")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)
        next_prompt = _next_detail_prompt(session)
        reply = f"Perfect. I've noted {value}."
        if next_prompt:
            reply = f"{reply}\n\n{next_prompt}"
        track_question(session, reply, slot_key=_next_detail_key(session))
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "req_yes":
        session.awaiting_special_req_text = True
        reply = "Please tell us about your requirements or preferences."
        track_question(session, reply, slot_key="special_requirements_details")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "req_no":
        return _advance_after_special_requirements(session, text, stored="None")
    if bid == "date_confirmed":
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "date_status": "confirmed"})
        _reset_date_picker(session)
        return _ask_event_year(session, text)
    if bid == "date_tentative":
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "date_status": "tentative"})
        _reset_date_picker(session)
        return _ask_event_year(session, text)
    if bid == "event_year_more":
        session.year_list_offset = int(session.year_list_offset or 0) + YEAR_PAGE_SIZE
        return _ask_event_year(session, text)
    year_picked = parse_year_id(bid)
    if year_picked is not None:
        session.pending_event_year = year_picked
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_year": year_picked})
        session.month_list_page = 0
        if session.fields.event_month:
            session.pending_event_month = f"{year_picked:04d}-{int(session.fields.event_month):02d}"
            session.day_list_page = 0
            return _ask_event_day(session, text)
        return _ask_event_month(session, text)
    if bid == "cal_month_more":
        session.month_list_page = 1
        return _ask_event_month(session, text)
    month_picked = parse_month_id(bid)
    if month_picked is not None:
        year = int(session.pending_event_year or 0)
        if bid.startswith("month_") and bid.count("_") == 2:
            try:
                year = int(bid.split("_")[1])
                session.pending_event_year = year
            except ValueError:
                pass
        if not year:
            return _ask_event_year(session, text)
        session.pending_event_month = f"{year:04d}-{month_picked:02d}"
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_year": year, "event_month": month_picked})
        session.day_list_page = 0
        return _ask_event_day(session, text)
    if bid == "event_day_more":
        session.day_list_page = int(session.day_list_page or 0) + 1
        return _ask_event_day(session, text)
    day_picked = parse_day_id(bid) if bid.startswith("event_day_") else None
    if day_picked is not None:
        year = int(session.pending_event_year or 0)
        month = int(str(session.pending_event_month or "0").split("-")[-1] or 0)
        if not valid_calendar_day(year, month, day_picked):
            reply = invalid_event_date_clarify()
            track_question(session, reply, slot_key="event_day")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)
        return _ask_confirm_event_date(session, text, year=year, month=month, day=day_picked)
    if bid == "event_date_confirm":
        return _continue_after_event_date(session, text)
    if bid == "event_date_change":
        data = session.fields.model_dump()
        data["event_date"] = None
        data["event_year"] = None
        data["event_month"] = None
        session.fields = EnquiryFields(**data)
        _reset_date_picker(session)
        return _ask_event_year(session, text)
    if bid.startswith("month_") and bid != "month_other":
        month_picked = parse_month_id(bid)
        if month_picked:
            try:
                year = int(bid.split("_")[1])
            except (IndexError, ValueError):
                year = int(session.pending_event_year or 0)
            if not year:
                return _ask_event_year(session, text)
            session.pending_event_year = year
            session.pending_event_month = f"{year:04d}-{month_picked:02d}"
            session.day_list_page = 0
            return _ask_event_day(session, text)
    if bid == "month_other":
        return _ask_event_year(session, text)
    if bid == "callback_today":
        return _set_callback_date_and_ask_period(session, text, _ist_today())
    if bid == "callback_tomorrow":
        return _set_callback_date_and_ask_period(session, text, _ist_today() + timedelta(days=1))
    if bid == "callback_choose_date":
        reply = "Please share the date you'd like us to call."
        track_question(session, reply, slot_key="callback_date")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid in CALLBACK_ID_TO_LABEL:
        session.callback_period = CALLBACK_ID_TO_LABEL[bid]
        session.fields = EnquiryFields(
            **{**session.fields.model_dump(), "callback_time_period": session.callback_period}
        )
        reply = "What time would you prefer?"
        track_question(session, reply, slot_key="callback_slot")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid in CALLBACK_SLOT_IDS:
        slot_label = CALLBACK_SLOT_IDS[bid]
        return _lock_callback_slot(session, whatsapp_id, text, slot_label)
    if bid in {"callback_exact", "callback_exact_time"}:
        if session.last_asked_slot == "callback_period" or not session.callback_period:
            session.callback_period = "exact"
        reply = "Please send the exact time (for example 10:30 AM)."
        track_question(session, reply, slot_key="callback_time")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "callback_change":
        data = session.fields.model_dump()
        data["callback_date"] = None
        data["callback_time"] = None
        data["callback_time_period"] = None
        data["preferred_callback"] = None
        session.fields = EnquiryFields(**data)
        session.callback_period = None
        move_to(session, GuidedStep.COLLECT_DETAILS, force=True)
        reply = "When would you like our senior planner to call you?"
        track_question(session, reply, slot_key="callback_date")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "callback_other":
        reply = "Please tell us a convenient day and time for the call."
        track_question(session, reply, slot_key="preferred_callback")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "booking_confirm":
        return _finalize_booking_reply(session, text)
    if bid == "booking_edit":
        move_to(session, GuidedStep.AWAIT_EDIT_FIELD, force=True)
        reply = "What would you like to change?"
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "booking_cancel":
        move_to(session, GuidedStep.AWAIT_CANCEL_CONFIRM, force=True)
        reply = "Would you like to cancel this planning session?"
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "cancel_yes":
        reply = cancel_to_main_menu(session)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid == "cancel_no":
        move_to(session, GuidedStep.AWAIT_BOOKING_CONFIRM, force=True)
        reply = _booking_summary_text(session)
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    if bid in EDIT_ID_TO_SLOT:
        slot = EDIT_ID_TO_SLOT[bid]
        if slot == "event_type":
            return _show_event_type_list(session, text, extra="What type of event are you planning?")
        data = session.fields.model_dump()
        if slot == "special_requirements":
            session.special_req_done = False
            session.awaiting_special_req_text = False
        if slot == "event_location":
            data["venue_status"] = None
            data["venue_area"] = None
            data["venue_name"] = None
            data["venue_type"] = None
        data[slot] = None
        if slot == "preferred_callback":
            data["callback_date"] = None
            data["callback_time"] = None
        session.fields = EnquiryFields(**data)
        move_to(session, GuidedStep.COLLECT_DETAILS, force=True)
        prompt = _next_detail_prompt(session) or detail_question(slot, event_type=session.fields.event_type)
        reply = prompt
        track_question(session, reply, slot_key=slot)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)
    return None


async def _maybe_information_interrupt(
    session: ConversationSession,
    text: str,
) -> AgentTurnResult | None:
    """Answer a question without advancing booking state."""
    step = session.guided_step
    if step in {GuidedStep.AWAIT_HI, GuidedStep.AWAIT_NAME, GuidedStep.AWAIT_NAME_CONFIRM}:
        return None
    if wants_book_again(text) or wants_straight_to_planning(text) or wants_to_move_further(text):
        if not is_food_menu_question(text) and not wants_cuisine_options(text):
            return None
    if session.guided_step in {
        GuidedStep.SHOWING_EVENT_INFORMATION,
        GuidedStep.PAST_SETUPS,
    } and is_information_done_command(text):
        return None
    if wants_showcase_look(text) or customer_wants_photos(text):
        return None
    if is_ambiguous_yes(text):
        return None

    expected = session.last_asked_slot or _next_detail_key(session)
    if expected and is_likely_field_answer(text, expected, last_asked_slot=session.last_asked_slot):
        return None
    if not is_information_request(text) and not is_food_menu_question(text) and not wants_cuisine_options(text):
        return None

    if (
        (is_food_menu_question(text) or wants_cuisine_options(text))
        and step == GuidedStep.AWAIT_POST_SHOWCASE
        and not looks_like_question(text)
    ):
        return None

    if is_food_menu_question(text) or wants_cuisine_options(text):
        answered = cuisine_options_reply(event_type=session.fields.event_type)
    else:
        answered = await answer_details_question(session, text, None)

    pending = None
    if step in {GuidedStep.SHOWING_EVENT_INFORMATION, GuidedStep.PAST_SETUPS}:
        pending = proceed_with_done_prompt()
    elif step == GuidedStep.AWAIT_POST_SHOWCASE:
        pending = (
            f"Would you like to know more about our "
            f"{display_event_label(session.fields.event_type)} event services and options?"
        )
    elif step == GuidedStep.COLLECT_DETAILS:
        pending = _next_detail_prompt(session)
    elif step == GuidedStep.AWAIT_EVENT_TYPE:
        pending = "What celebration would you like to plan?"
    if pending:
        reply = f"{answered}\n\nComing back to your booking: {pending}"
    else:
        reply = answered
    track_question(session, reply, slot_key=expected)
    record_exchange(session, text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


async def process_guided_flow(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
    *,
    button_id: str | None = None,
) -> AgentTurnResult | None:
    text = sanitize_customer_reply(user_text, last_bot_message=session.last_assistant_question)
    hydrate_memory(session)
    before_fields = session.fields.model_dump()

    # First customer message is greeting-only. Ignore name/event extraction entirely.
    if session.guided_step == GuidedStep.AWAIT_HI:
        return _send_initial_greeting(session, text)

    if button_id:
        handled = await _handle_stable_button(session, whatsapp_id, text or button_id, button_id)
        if handled is not None:
            return handled

    # Global commands — never fall through to completion
    if wants_book_again(text):
        reply = soft_reset_session(session)
        track_question(session, reply, slot_key="event_type" if session.fields.event_type else "customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if is_reset_message(text):
        reply = greeting_reset_reply(session)
        track_question(session, reply, slot_key="customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if is_cancel_message(text) and session.guided_step not in {
        GuidedStep.AWAIT_BOOKING_CONFIRM,
        GuidedStep.AWAIT_CANCEL_CONFIRM,
    }:
        reply = cancel_to_main_menu(session)
        track_question(session, reply, slot_key="event_type" if session.name_confirmed else "customer_name")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if is_help_message(text) and session.guided_step != GuidedStep.AWAIT_HI:
        reply = help_options_reply()
        pending = session.last_assistant_question
        if pending and "past setups" not in reply.lower():
            reply = f"{reply}\n\n{pending}"
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    info_interrupt = await _maybe_information_interrupt(session, text)
    if info_interrupt is not None:
        return info_interrupt

    def _lock_callback_phone(number: str) -> None:
        data = session.fields.model_dump()
        data["callback_phone"] = number
        data["phone_number"] = number
        session.fields = EnquiryFields(**data)
        session.pending_callback_phone_confirm = False
        session.pending_alt_callback_phone = False

    def _lock_noon(meridiem: str) -> None:
        data = session.fields.model_dump()
        data["callback_time"] = "12:00 PM" if meridiem == "pm" else "12:00 AM"
        data["preferred_callback"] = compose_callback_label(
            date_label=data.get("callback_date"),
            time_label=data["callback_time"],
        )
        session.pending_ampm_hour = None
        session.fields = EnquiryFields(**data)

    waiting_phone = session.pending_callback_phone_confirm or session.pending_alt_callback_phone
    typed_phone = extract_phone_number(text)
    if waiting_phone and typed_phone:
        _lock_callback_phone(typed_phone)
        if session.pending_ampm_hour == 12:
            reply = confirm_noon_prompt()
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)
        return _complete_enquiry_reply(session, whatsapp_id, text)

    if session.pending_callback_phone_confirm and is_name_confirm_no(text):
        session.pending_callback_phone_confirm = False
        session.pending_alt_callback_phone = True
        reply = ask_alternative_callback_number()
        track_question(session, reply, slot_key="preferred_callback")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if session.pending_callback_phone_confirm and is_name_confirm_yes(text):
        _lock_callback_phone(normalize_phone(whatsapp_id))
        if session.pending_ampm_hour == 12:
            _lock_noon("pm")
        return _complete_enquiry_reply(session, whatsapp_id, text)

    if session.pending_alt_callback_phone and not typed_phone:
        reply = ask_alternative_callback_number()
        track_question(session, reply, slot_key="preferred_callback")
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if session.pending_ampm_hour == 12 and is_name_confirm_yes(text):
        _lock_noon("pm")
        return _complete_enquiry_reply(session, whatsapp_id, text)

    if session.pending_ampm_hour == 12 and re.search(r"\b(pm|p\.m|noon|afternoon)\b", text, re.I):
        _lock_noon("pm")
        return _complete_enquiry_reply(session, whatsapp_id, text)

    if session.pending_ampm_hour == 12 and re.search(r"\b(am|a\.m|midnight)\b", text, re.I):
        _lock_noon("am")
        return _complete_enquiry_reply(session, whatsapp_id, text)

    if session.guided_step not in {GuidedStep.AWAIT_HI, GuidedStep.AWAIT_NAME} and typed_phone:
        _lock_callback_phone(typed_phone)
        if session.guided_step == GuidedStep.COLLECT_DETAILS:
            next_prompt = _next_detail_prompt(session) or callback_time_prompt(
                date_label=session.fields.callback_date
            )
            reply = noted_callback_phone_prompt() if not session.fields.callback_time else next_prompt
            if session.fields.callback_time or session.fields.preferred_callback:
                return _complete_enquiry_reply(session, whatsapp_id, text)
            track_question(session, reply, slot_key="preferred_callback")
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

    asked_now = session.last_asked_slot
    if session.guided_step == GuidedStep.COLLECT_DETAILS and asked_now in {
        "special_requirements",
        "special_requirements_details",
        "callback_date",
        "callback_period",
        "callback_slot",
        "callback_time",
        "preferred_callback",
        "venue_name",
        "event_year",
        "event_month",
        "event_day",
        "event_date_confirm",
    }:
        newly_collected = []
    else:
        extracted = extract_entities(text, session)
        apply_entities(session, extracted)
        newly_collected = [
            key for key, value in session.fields.model_dump().items()
            if before_fields.get(key) in (None, "") and value not in (None, "")
        ]
    advance_from_slots(session)
    session.conversation_version = int(session.conversation_version or 0) + 1
    step = session.guided_step
    if not newly_collected:
        newly_collected = [
            key for key, value in session.fields.model_dump().items()
            if before_fields.get(key) in (None, "") and value not in (None, "")
        ]

    if step == GuidedStep.DONE:
        return None

    if step == GuidedStep.AWAIT_OTHER_EVENT:
        custom = text.strip()[:80]
        if len(custom) < 2 or is_greeting_only(text) or looks_like_question(text):
            return _ask_other_event_name(session, text)
        _set_event_type(session, custom.title())
        return _offer_info_yes_no(session, text)

    if step == GuidedStep.AWAIT_BOOKING_CONFIRM:
        low = text.strip().lower()
        if is_name_confirm_yes(text) or low in {"confirm", "proceed", "ok confirm"}:
            return _finalize_booking_reply(session, text)
        if "change callback" in low:
            return await _handle_stable_button(session, whatsapp_id, text, "callback_change")
        if "edit" in low:
            return await _handle_stable_button(session, whatsapp_id, text, "booking_edit")
        if is_cancel_message(text) or low in {"cancel"}:
            return await _handle_stable_button(session, whatsapp_id, text, "booking_cancel")
        reply = _booking_summary_text(session)
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_EDIT_FIELD:
        low = text.strip().lower()
        mapping = {
            "event": "edit_event",
            "date": "edit_date",
            "guest": "edit_guests",
            "guests": "edit_guests",
            "venue": "edit_venue",
            "catering": "edit_catering",
            "cuisine": "edit_catering",
            "requirement": "edit_requirements",
            "callback": "edit_callback",
        }
        for key, bid in mapping.items():
            if key in low:
                return await _handle_stable_button(session, whatsapp_id, text, bid)
        reply = "What would you like to change?"
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_CANCEL_CONFIRM:
        if is_name_confirm_yes(text) or "cancel" in text.lower():
            return await _handle_stable_button(session, whatsapp_id, text, "cancel_yes")
        if is_name_confirm_no(text) or "continue" in text.lower():
            return await _handle_stable_button(session, whatsapp_id, text, "cancel_no")
        return await _handle_stable_button(session, whatsapp_id, text, "booking_cancel")

    if step == GuidedStep.AWAIT_HI:
        return _send_initial_greeting(session, text)

    if step == GuidedStep.AWAIT_NAME_CONFIRM:
        candidate = (session.pending_name or "").strip()
        typed_name = extract_name(text)

        # Message that just provided the candidate name → keep asking Yes/No
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
            reply = greeting_ask_name()
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
            lowered = text.strip().lower()
            if lowered in {"other", "something else", "something other"}:
                return _ask_other_event_name(session, text)
            custom = text.strip()[:80]
            if len(custom.split()) <= 6 and not looks_like_question(text):
                _set_event_type(session, custom.title())
                return _offer_info_yes_no(session, text)
            return _show_event_type_list(session, text, extra="Please select an event below, or choose Other.")

        clear_slot_failures(session, "event_type")
        _set_event_type(session, event_type)
        return _offer_info_yes_no(session, text)

    if step == GuidedStep.AWAIT_POST_SHOWCASE:
        # Entity sweep may have just filled event_type and advanced here — still show showcase once.
        if "event_type" in newly_collected and not session.showcase_prompted:
            return _offer_info_yes_no(session, text)

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

        from app.services.human_style import normalize_customer_text as _norm_choice

        choice = _norm_choice(text)
        if is_ambiguous_yes(text) or is_name_confirm_yes(text) or choice in {"yes"}:
            handled = await _handle_stable_button(session, whatsapp_id, text, "info_yes")
            return handled

        if is_name_confirm_no(text) or choice in {"no", "nope"}:
            handled = await _handle_stable_button(session, whatsapp_id, text, "info_no")
            return handled

        if wants_cuisine_options(text) or choice in {"cuisine options", "cuisines"}:
            reply = _enter_showing_event_information(
                session,
                cuisine_options_reply(event_type=session.fields.event_type),
            )
            track_question(session, reply)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if choice in {"2", "3"}:
            move_to(session, GuidedStep.COLLECT_DETAILS)
            reply = _intent_b_reply(text, session)
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Intent A: past setups / photos — then wait for DONE
        if wants_showcase_look(text) or customer_wants_photos(text) or choice in {"1"}:
            reply, media = await _intent_a_showcase_payload(session, text)
            reply = _enter_showing_event_information(session, reply)
            track_question(session, reply)
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
                showcase_reply, media = await _intent_a_showcase_payload(session, text)
                reply = _enter_showing_event_information(session, f"{reply}\n\n{showcase_reply}")
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

        # Info / topic asks → show information, then Type DONE (do not ask date yet)
        if (
            looks_like_question(text)
            or wants_more_info(text)
            or is_service_topic_reply(text)
            or _is_custom_request(text)
        ):
            if wants_showcase_look(text) or customer_wants_photos(text):
                reply, media = await _intent_a_showcase_payload(session, text)
                reply = _enter_showing_event_information(session, reply)
                track_question(session, reply)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)
            if wants_more_info(text) and not is_service_topic_reply(text):
                profile = get_event_profile(session.fields.event_type)
                answered = (
                    f"Absolutely! {profile['showcase']} "
                    f"You can also browse menus and setups at **srivatsanka.com**."
                )
            else:
                answered = await answer_showcase_question(session, text)
            if _is_custom_request(text):
                answered = handle_custom_request(session, text, answered)
            reply = _enter_showing_event_information(session, answered)
            track_question(session, reply)
            if not repeated_question(session, reply):
                record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Stay on Yes/No — never auto-start planning from unclassifiable text
        return _offer_info_yes_no(session, text)

    if step in {GuidedStep.PAST_SETUPS, GuidedStep.SHOWING_EVENT_INFORMATION}:
        if (
            is_information_done_command(text)
            or wants_straight_to_planning(text)
            or "plan my event" in text.lower()
        ):
            reply = _begin_event_details_after_information(session)
            slot = "date_status" if not session.fields.event_date else (_next_detail_key(session) or "event_date")
            track_question(session, reply, slot_key=slot)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)
        if "back" in text.lower() and "event" in text.lower():
            return _show_event_type_list(session, text)

        if wants_discuss_on_call(text):
            move_to(session, GuidedStep.COLLECT_DETAILS)
            reply = callback_pivot_prompt(name=session.fields.customer_name)
            reply = handle_custom_request(session, text, reply)
            track_question(session, reply, slot_key="preferred_callback")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_cuisine_options(text) or is_food_menu_question(text):
            reply = _enter_showing_event_information(
                session,
                cuisine_options_reply(event_type=session.fields.event_type),
            )
            track_question(session, reply)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if wants_showcase_look(text) or customer_wants_photos(text):
            reply, media = await _intent_a_showcase_payload(session, text)
            reply = _enter_showing_event_information(session, reply)
            track_question(session, reply)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields, media=media)

        if is_thanks_only(text):
            reply = f"{thanks_reply()}\n\n{proceed_with_done_prompt()}"
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        reply = proceed_with_done_prompt()
        track_question(session, reply)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.COLLECT_DETAILS:
        _skip_inapplicable_fields(session)
        asked = session.last_asked_slot or _next_detail_key(session)
        spec_slots = {"special_requirements", "special_requirements_details"}

        if asked in spec_slots:
            if not session.awaiting_special_req_text and asked == "special_requirements":
                if is_name_confirm_yes(text):
                    return await _handle_stable_button(session, whatsapp_id, text, "req_yes")
                if is_name_confirm_no(text) or _is_empty_requirement(text):
                    return _advance_after_special_requirements(session, text, stored="None")
            if _is_empty_requirement(text):
                return _advance_after_special_requirements(session, text, stored="None")
            return _advance_after_special_requirements(session, text, stored=text.strip()[:500] or "None")

        if asked == "date_status":
            if is_impossible_calendar_date(text):
                reply = invalid_event_date_clarify()
                track_question(session, reply, slot_key="date_status")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            if looks_like_event_date(text) and _is_full_event_date_phrase(text) and not is_impossible_calendar_date(text):
                parsed = _parse_picker_or_nl_date(session, text)
                if parsed:
                    return parsed
            if not looks_like_event_date(text) or not _is_full_event_date_phrase(text):
                low = text.lower()
                if "tentat" in low:
                    return await _handle_stable_button(session, whatsapp_id, text, "date_tentative")
                if "confirm" in low or is_name_confirm_yes(text):
                    return await _handle_stable_button(session, whatsapp_id, text, "date_confirmed")
                from app.services.event_date import MONTHS as _MONTHS

                month_only = _MONTHS.get(text.strip().lower()) or _MONTHS.get(text.strip().lower()[:3])
                if month_only and re.fullmatch(r"[A-Za-z]+", text.strip()):
                    session.fields = EnquiryFields(
                        **{
                            **session.fields.model_dump(),
                            "date_status": session.fields.date_status or "tentative",
                            "event_month": int(month_only),
                        }
                    )
                    return _ask_event_year(session, text)
            reply = "Is your event date confirmed, or is it still tentative?"
            track_question(session, reply, slot_key="date_status")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if asked in {"event_year", "event_month", "event_day", "event_date_confirm", "event_date"}:
            handled_date = await _handle_event_date_turn(session, whatsapp_id, text, asked)
            if handled_date is not None:
                return handled_date

        if asked in {"callback_date", "callback_period", "callback_slot", "callback_time"} or (
            asked == "preferred_callback"
        ):
            return await _handle_callback_turn(session, whatsapp_id, text, asked)

        if asked == "venue_name":
            name = text.strip()[:160]
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "venue_name": name})
            reply = "What is the area or locality?"
            track_question(session, reply, slot_key="venue_area")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if asked == "venue_area":
            area = text.strip()[:160]
            data = session.fields.model_dump()
            data["venue_area"] = area
            if data.get("venue_name"):
                data["event_location"] = f"{data['venue_name']}, {area}"
            else:
                data["event_location"] = area
            session.fields = EnquiryFields(**data)
            next_prompt = _next_detail_prompt(session)
            reply = f"Thanks! I've noted {area} as the venue area."
            if next_prompt:
                reply = f"{reply}\n\n{next_prompt}"
            track_question(session, reply, slot_key=_next_detail_key(session))
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if asked == "event_location" and not session.fields.venue_status:
            low = text.lower()
            if "not" in low and ("fixed" in low or "yet" in low or "help" in low):
                return await _handle_stable_button(session, whatsapp_id, text, "venue_help")
            if is_name_confirm_no(text) or "help" in low:
                return await _handle_stable_button(session, whatsapp_id, text, "venue_help")
            if (is_name_confirm_yes(text) and "help" not in low) or (
                "fixed" in low and "not" not in low
            ):
                return await _handle_stable_button(session, whatsapp_id, text, "venue_fixed")
        if asked == "meal_preference":
            low = text.lower().strip()
            if low in {"not sure", "unsure", "don't know", "dont know"}:
                return await _handle_stable_button(session, whatsapp_id, text, "cuisine_unsure")
            for cid, label in CUISINE_ID_TO_VALUE.items():
                if low == label.lower() or label.lower() in low:
                    return await _handle_stable_button(session, whatsapp_id, text, cid)

        if is_information_done_command(text):
            prompt = _next_detail_prompt(session) or ask_event_date_only(
                event_type=session.fields.event_type
            )
            reply = prompt
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        from app.services.venue_parser import parse_venue_reply

        venue = parse_venue_reply(text)
        location_turn = session.last_asked_slot in {"event_location", "venue_area"}
        if location_turn and not (is_information_request(text) and looks_like_question(text)):
            data = session.fields.model_dump()
            if venue.status:
                data["venue_status"] = venue.status
            if venue.is_home:
                data["venue_type"] = "home"
                data["venue_name"] = venue.venue_name or "customer's house"
                data["venue_status"] = "fixed"
            if venue.location:
                data["venue_area"] = venue.location
                if data.get("venue_name"):
                    data["event_location"] = f"{data['venue_name']}, {venue.location}"
                else:
                    data["event_location"] = venue.location
                session.fields = EnquiryFields(**data)
                next_prompt = _next_detail_prompt(session)
                reply = f"Thanks! I've noted {venue.location} as the venue area."
                if next_prompt:
                    reply = f"{reply}\n\n{next_prompt}"
                track_question(session, reply, slot_key=_next_detail_key(session) or "preferred_callback")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            session.fields = EnquiryFields(**data)
            if venue.is_home or (venue.status == "fixed" and not venue.location):
                reply = venue_area_prompt(venue_name=session.fields.venue_name)
                if venue.status == "fixed" and not venue.is_home:
                    reply = (
                        "Understood, your venue is already fixed. "
                        "Please share the venue name."
                    )
                    track_question(session, reply, slot_key="venue_name")
                else:
                    track_question(session, reply, slot_key="venue_area")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            if venue.status == "not_fixed" and not venue.location:
                reply = (
                    "No problem if the venue is not fixed yet. "
                    "Which city or locality should we plan around?"
                )
                track_question(session, reply, slot_key="venue_area")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if asked in {"callback_date", "callback_period", "callback_slot", "callback_time", "preferred_callback"}:
            if asks_callback_timing(text):
                reply = callback_timing_reply(
                    preferred_callback=session.fields.preferred_callback,
                    name=session.fields.customer_name,
                )
                track_question(session, reply, slot_key=asked)
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
                showcase_reply, media = await _intent_a_showcase_payload(session, text)
                reply = f"{reply}\n\n{showcase_reply}"
                track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_short_planning_ack(text) and asked not in spec_slots:
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = next_prompt
                clear_slot_failures(session, _next_detail_key(session))
                track_question(session, reply, slot_key=_next_detail_key(session))
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

        if session.pending_date_confirm is None and is_ambiguous_date_phrase(text) and asked in {"event_date", "date_status"}:
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
            reply, media = await _intent_a_showcase_payload(session, text)
            pending = _next_detail_prompt(session)
            if pending and session.fields.event_date:
                reply = handle_custom_request(session, text, f"{reply}\n\n{pending}")
            track_question(session, reply, slot_key=_next_detail_key(session) or "event_date")
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields, media=media)

        if "event_date" in newly_collected and "guest_count" not in newly_collected:
            if not session.fields.date_status:
                session.fields = EnquiryFields(
                    **{**session.fields.model_dump(), "date_status": "tentative"}
                )
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

        expected = session.last_asked_slot
        if expected in {"venue_name", "venue_area"}:
            expected = "event_location"
        elif expected in {"callback_date", "callback_period", "callback_slot", "callback_time"}:
            expected = "preferred_callback"
        elif expected in {"event_year", "event_month", "event_day", "event_date_confirm", "date_status"}:
            expected = "event_date"
        elif expected == "special_requirements_details":
            expected = "special_requirements"

        for key in DETAIL_KEYS:
            if expected and key != expected:
                continue
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

            if key == "event_date" and is_impossible_calendar_date(text):
                reply = invalid_event_date_clarify()
                track_question(session, reply, slot_key="event_date")
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
                record_slot_failure(session, slot_key=key)
                if key == "event_date":
                    reply = invalid_event_date_clarify()
                    track_question(session, reply, slot_key="event_date")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                reply = prompt
                if key == "preferred_callback" and session.fields.callback_date:
                    reply = callback_time_prompt(date_label=session.fields.callback_date)
                if key == "event_location" and session.fields.venue_name:
                    reply = venue_area_prompt(venue_name=session.fields.venue_name)
                reply = handle_custom_request(session, text, reply)
                track_question(session, reply, slot_key=key)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not _store_detail_field(session, key, text):
                record_slot_failure(session, slot_key=key)
                if key == "event_date":
                    reply = invalid_event_date_clarify()
                    track_question(session, reply, slot_key="event_date")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                if key == "event_location":
                    reply = venue_area_prompt(venue_name=session.fields.venue_name)
                    track_question(session, reply, slot_key="event_location")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                if key == "preferred_callback":
                    reply = _next_detail_prompt(session) or prompt
                    track_question(session, reply, slot_key="preferred_callback")
                    record_exchange(session, text, reply)
                    return AgentTurnResult(reply=reply, fields=session.fields)
                reply = prompt
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
