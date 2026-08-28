"""Deterministic entity extraction helpers for the guided FSM."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.company_knowledge import is_known_event_type, match_event_type
from app.services.callback_time import compose_callback_label, parse_callback_parts
from app.services.conversation_turns import clean_person_name, extract_name
from app.services.event_date import (
    extract_date_snippet,
    has_service_planning_intent,
    is_ambiguous_date_phrase,
    is_impossible_calendar_date,
    is_urgent_event_date,
    looks_like_event_date,
)
from app.services.human_style import is_meal_type_answer, normalize_meal_label, wants_discuss_on_call
from app.services.location_normalize import extract_location_entity
from app.services.message_intent import (
    MessageKind,
    classify_message,
    extract_phone_number,
    uses_this_whatsapp_number,
)
from app.services.session_store import ConversationSession, GuidedStep


RESET_WORDS = {"reset", "restart", "start over", "begin again"}


@dataclass
class ExtractedEntities:
    customer_name: str | None = None
    event_type: str | None = None
    event_date: str | None = None
    guest_count: str | int | None = None
    event_location: str | None = None
    venue_status: str | None = None
    venue_name: str | None = None
    venue_area: str | None = None
    venue_type: str | None = None
    meal_preference: str | None = None
    preferred_callback: str | None = None
    callback_date: str | None = None
    callback_time: str | None = None
    callback_phone: str | None = None
    callback_ambiguous_noon: bool = False
    uses_this_number: bool = False
    special_requests: str | None = None
    reset_requested: bool = False
    callback_requested: bool = False
    urgent_date: bool = False


def _extract_event(text: str, name: str | None) -> str | None:
    event_type = match_event_type(text)
    if not is_known_event_type(event_type):
        return None
    if name and event_type.lower() == name.lower():
        return None
    return event_type


def _sanitize_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = clean_person_name(name)
    if not cleaned:
        return None
    reject = {
        "hi",
        "hello",
        "hey",
        "yes",
        "ok",
        "okay",
        "sure",
        "no",
        "skip",
        "none",
        "thanks",
        "thank you",
        "new",
        "reset",
        "restart",
    }
    if cleaned.lower() in reject:
        return None
    return cleaned


def _extract_date_entity(text: str) -> str | None:
    return extract_date_snippet(text)


def _extract_guest_count(text: str) -> str | int:
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
        r"(?:around\s+|about\s+|approx(?:imately)?\s+|roughly\s+)?(\d+)\s*(?:-|–|—|to|and)\s*(\d+)",
        raw,
        re.I,
    )
    if range_match:
        return f"{range_match.group(1)} to {range_match.group(2)}"
    single = re.search(r"(\d+)", raw)
    if single:
        return int(single.group(1))
    return raw[:60] if raw else 100


def _extract_meal_from_text(text: str) -> str | None:
    if is_meal_type_answer(text):
        return normalize_meal_label(text)
    lower = text.lower()
    selected: list[str] = []
    if "breakfast" in lower:
        selected.append("Breakfast")
    if "lunch" in lower:
        selected.append("Lunch")
    if "dinner" in lower:
        selected.append("Dinner")
    if "snacks" in lower or "high tea" in lower:
        selected.append("Snacks")
    if "tea" in lower or "coffee" in lower:
        if "Snacks" not in selected:
            selected.append("Snacks")
        selected.append("Tea")
    return ", ".join(selected) if selected else None


def extract_entities(text: str, session: ConversationSession) -> ExtractedEntities:
    raw = (text or "").strip()
    lower = raw.lower()
    name = _sanitize_name(extract_name(raw) or None)
    if session.guided_step == GuidedStep.AWAIT_HI:
        name = None
    event_type = _extract_event(raw, name)

    entities = ExtractedEntities(
        customer_name=name,
        event_type=event_type,
        reset_requested=lower in RESET_WORDS,
        callback_requested=wants_discuss_on_call(raw),
    )

    # Date words often appear in callback phrases — do not treat those as event_date.
    from app.services.human_style import wants_showcase_look
    from app.services.website_gallery import customer_wants_photos
    from app.services.venue_parser import parse_venue_reply

    kind = classify_message(raw, session)
    phone = extract_phone_number(raw)
    if phone:
        entities.callback_phone = phone
    if uses_this_whatsapp_number(raw):
        entities.uses_this_number = True

    callbackish = bool(
        wants_discuss_on_call(raw)
        or re.search(r"\b(call|callback|ring me|speak|talk)\b", lower)
        or kind
        in {
            MessageKind.CALLBACK_DATE,
            MessageKind.CALLBACK_TIME,
            MessageKind.CALLBACK_COMBO,
        }
    )
    photoish = wants_showcase_look(raw) or customer_wants_photos(raw)

    if (
        kind not in {MessageKind.CALLBACK_DATE, MessageKind.CALLBACK_TIME, MessageKind.CALLBACK_COMBO, MessageKind.PHONE_NUMBER, MessageKind.VENUE_AREA, MessageKind.VENUE_HOME}
        and (not callbackish)
        and looks_like_event_date(raw)
        and session.last_asked_slot != "preferred_callback"
    ):
        date_entity = _extract_date_entity(raw)
        if date_entity and not is_ambiguous_date_phrase(date_entity) and not is_impossible_calendar_date(raw):
            entities.event_date = date_entity
            if is_urgent_event_date(raw):
                entities.urgent_date = True

    if kind == MessageKind.GUEST_COUNT or re.search(r"\b(guests?|people|pax)\b", lower):
        entities.guest_count = _extract_guest_count(raw)
    elif re.search(r"\bfor\s+\d+\b", lower) and looks_like_event_date(raw) and not callbackish:
        entities.guest_count = _extract_guest_count(raw)

    if has_service_planning_intent(raw) and session.last_asked_slot in {
        "event_location",
        "venue_name",
        "venue_area",
    }:
        entities.event_location = "Customer managed venue"
        if re.search(r"\b(catering|decor|decoration)\b", lower):
            entities.special_requests = raw

    venue = parse_venue_reply(raw)
    asking_venue = session.last_asked_slot in {"event_location", "venue_name", "venue_area"}
    if asking_venue and (
        kind in {MessageKind.VENUE_HOME, MessageKind.VENUE_STATUS, MessageKind.VENUE_AREA}
        or venue.status
        or venue.location
        or venue.is_home
    ):
        if venue.status:
            entities.venue_status = venue.status
        if venue.is_home:
            entities.venue_type = "home"
            entities.venue_name = venue.venue_name or "customer's house"
            entities.venue_status = "fixed"
        if venue.location:
            entities.venue_area = venue.location
            if entities.venue_name:
                entities.event_location = f"{entities.venue_name}, {venue.location}"
            else:
                entities.event_location = venue.location
        elif venue.is_home:
            # Home without area is not a complete location.
            entities.event_location = None
        elif re.search(
            r"\b(venue|location|hall|area|city|locality|mysore|mysuru|bangalore|bengaluru|benglore|banglore|bengalore|hunsur|hundur)\b",
            lower,
        ) and not venue.status:
            loc = extract_location_entity(raw)
            if loc:
                entities.event_location = loc
                entities.venue_area = loc

    asking_meal = session.last_asked_slot == "meal_preference"
    if asking_meal:
        meal = _extract_meal_from_text(raw)
        if meal:
            entities.meal_preference = meal
        if is_meal_type_answer(raw):
            entities.meal_preference = normalize_meal_label(raw)

    parts = parse_callback_parts(raw)
    callback_kind = kind in {
        MessageKind.CALLBACK_DATE,
        MessageKind.CALLBACK_TIME,
        MessageKind.CALLBACK_COMBO,
        MessageKind.PHONE_NUMBER,
    }
    asking_callback = session.last_asked_slot == "preferred_callback"
    if callback_kind or (asking_callback and (parts.date_label or parts.time_label or parts.immediate) and kind != MessageKind.VENUE_AREA):
        if parts.date_label:
            entities.callback_date = parts.date_label
        if parts.time_label:
            entities.callback_time = parts.time_label
        entities.callback_ambiguous_noon = parts.ambiguous_noon
        if parts.immediate:
            entities.preferred_callback = "Immediately"
        else:
            composed = compose_callback_label(
                date_label=parts.date_label or session.fields.callback_date,
                time_label=None if parts.ambiguous_noon else (parts.time_label or session.fields.callback_time),
                immediate=False,
            )
            # Date-only must not close the callback slot.
            if composed and (parts.time_label or parts.period) and not parts.ambiguous_noon:
                entities.preferred_callback = composed
            elif asking_callback and parts.time_label and not parts.ambiguous_noon and not parts.date_label:
                entities.preferred_callback = compose_callback_label(
                    date_label=session.fields.callback_date,
                    time_label=parts.time_label,
                )
        if parts.uses_this_number:
            entities.uses_this_number = True

    if re.search(r"\b(fusion|custom|italian|chinese|dessert|live counter|pan asian|mocktail|gelato)\b", lower):
        if not re.search(r"\b(cocktail party|alcohol|alcoholic|conference|exhibition|expo)\b", lower):
            entities.special_requests = raw

    if re.search(r"\b(pure\s*veg|pure\s*vegetarian|vegetarian catering|veg only|sattvic|satvik)\b", lower):
        entities.special_requests = (entities.special_requests or "Pure vegetarian catering").strip()

    if entities.event_location:
        cname = (entities.customer_name or session.fields.customer_name or session.pending_name or "").strip().lower()
        if cname and entities.event_location.strip().lower() == cname:
            entities.event_location = None
        etype = (entities.event_type or session.fields.event_type or "").strip().lower()
        if etype and (entities.event_location or "").strip().lower() == etype:
            entities.event_location = None

    return entities
