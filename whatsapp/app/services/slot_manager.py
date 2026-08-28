"""Slot bookkeeping for deterministic enquiry collection."""

from __future__ import annotations

from app.schemas import EnquiryFields
from app.services.conversation_turns import clean_person_name
from app.services.human_style import has_callback_intent, is_meal_type_answer
from app.services.entity_extractor import ExtractedEntities
from app.services.session_store import ConversationSession, GuidedStep, SlotValue


FIELD_KEYS = (
    "customer_name",
    "event_type",
    "event_date",
    "guest_count",
    "event_location",
    "meal_preference",
    "preferred_callback",
)


def sync_slots_from_fields(session: ConversationSession) -> None:
    data = session.fields.model_dump()
    for key in FIELD_KEYS:
        value = data.get(key)
        slot = session.slots.setdefault(key, SlotValue())
        if value not in (None, ""):
            slot.value = value
            slot.confidence = max(slot.confidence, 1.0)
            slot.collected = True


def _allowed_entity_keys(session: ConversationSession, entities: ExtractedEntities) -> set[str]:
    """Gate entity writes by current step so off-topic text cannot fill future slots."""
    step = session.guided_step
    allowed: set[str] = set()
    early_steps = {
        GuidedStep.AWAIT_NAME,
        GuidedStep.AWAIT_NAME_CONFIRM,
        GuidedStep.AWAIT_EVENT_TYPE,
        GuidedStep.AWAIT_OTHER_EVENT,
        GuidedStep.AWAIT_POST_SHOWCASE,
        GuidedStep.PAST_SETUPS,
        GuidedStep.SHOWING_EVENT_INFORMATION,
    }

    if step == GuidedStep.AWAIT_HI:
        return set()
    if step in {GuidedStep.AWAIT_NAME, GuidedStep.AWAIT_NAME_CONFIRM}:
        allowed.add("customer_name")
        allowed.add("event_type")
    elif step == GuidedStep.AWAIT_EVENT_TYPE:
        allowed.add("event_type")
    elif step in {
        GuidedStep.AWAIT_POST_SHOWCASE,
        GuidedStep.PAST_SETUPS,
        GuidedStep.SHOWING_EVENT_INFORMATION,
    }:
        if entities.callback_requested:
            allowed.add("preferred_callback")
        allowed.add("special_requests")
    elif step == GuidedStep.COLLECT_DETAILS:
        asked = session.last_asked_slot
        if asked == "date_status":
            allowed.add("event_date")
        elif asked == "event_date":
            allowed.add("event_date")
        elif asked == "guest_count":
            allowed.add("guest_count")
        elif asked == "event_location":
            allowed.add("event_location")
        elif asked in {"venue_name", "venue_area"}:
            allowed.add("event_location")
        elif asked == "meal_preference":
            allowed.add("meal_preference")
        elif asked in {"special_requirements", "special_requirements_details"}:
            allowed.add("special_requirements")
            allowed.add("special_requests")
        elif asked in {"preferred_callback", "callback_date", "callback_time", "callback_slot", "callback_period"}:
            allowed.add("preferred_callback")
        # Never volunteer a different booking field than the one we asked for.
    elif step == GuidedStep.DONE:
        allowed.add("special_requests")

    # Capture details whenever the customer volunteers them, even before detail collection.
    if step in early_steps and step != GuidedStep.SHOWING_EVENT_INFORMATION:
        if entities.event_date:
            allowed.add("event_date")
        if entities.guest_count is not None:
            allowed.add("guest_count")
        if entities.event_location:
            allowed.add("event_location")
        allowed.add("special_requests")

    # Never overwrite an already-confirmed name/event from noisy later text
    if session.name_confirmed and session.fields.customer_name:
        allowed.discard("customer_name")
    if session.fields.event_type:
        allowed.discard("event_type")

    return allowed


def apply_entities(session: ConversationSession, entities: ExtractedEntities) -> None:
    data = session.fields.model_dump()
    allowed = _allowed_entity_keys(session, entities)

    for key in FIELD_KEYS:
        if key not in allowed:
            continue
        value = getattr(entities, key, None)
        if value in (None, ""):
            continue
        if key == "preferred_callback":
            if is_meal_type_answer(str(value)):
                continue
            from app.services.callback_time import callback_has_usable_time

            if not callback_has_usable_time(str(value), pending_ampm=bool(session.pending_ampm_hour)):
                continue
            if not (
                entities.callback_requested
                or session.last_asked_slot == "preferred_callback"
                or has_callback_intent(str(value))
                or getattr(entities, "callback_time", None)
                or getattr(entities, "callback_date", None)
            ):
                continue
            if session.guided_step not in {
                GuidedStep.COLLECT_DETAILS,
                GuidedStep.AWAIT_POST_SHOWCASE,
                GuidedStep.PAST_SETUPS,
                GuidedStep.SHOWING_EVENT_INFORMATION,
            } and not entities.callback_requested:
                continue
        # Name stays pending until Yes confirmation (STATE 1.2)
        if key == "customer_name" and not session.name_confirmed:
            session.pending_name = clean_person_name(str(value)) or str(value).strip()
            continue
        if key == "event_date":
            from app.services.event_date import is_impossible_calendar_date

            if is_impossible_calendar_date(str(value)):
                continue
        if key == "event_location":
            cname = (data.get("customer_name") or session.pending_name or "").strip().lower()
            etype = (data.get("event_type") or "").strip().lower()
            val = str(value).strip().lower()
            if (cname and val == cname) or (etype and val == etype):
                continue
            if val in {"our house", "my house", "home", "at home"}:
                continue
        if data.get(key) in (None, ""):
            data[key] = value
        slot = session.slots.setdefault(key, SlotValue())
        slot.value = data[key]
        slot.confidence = max(slot.confidence, 0.85)
        slot.collected = True

    asked = session.last_asked_slot
    venue_ok = session.guided_step != GuidedStep.COLLECT_DETAILS or asked in {
        "event_location",
        "venue_name",
        "venue_area",
    }
    if venue_ok:
        if getattr(entities, "venue_status", None):
            data["venue_status"] = entities.venue_status
        if getattr(entities, "venue_name", None):
            data["venue_name"] = entities.venue_name
        if getattr(entities, "venue_area", None):
            data["venue_area"] = entities.venue_area
        if getattr(entities, "venue_type", None):
            data["venue_type"] = entities.venue_type
    callback_ok = session.guided_step != GuidedStep.COLLECT_DETAILS or asked in {
        "preferred_callback",
        "callback_date",
        "callback_time",
        "callback_slot",
        "callback_period",
    }
    if callback_ok:
        if getattr(entities, "callback_date", None):
            data["callback_date"] = entities.callback_date
        if getattr(entities, "callback_time", None) and not getattr(entities, "callback_ambiguous_noon", False):
            data["callback_time"] = entities.callback_time
        if getattr(entities, "callback_phone", None):
            data["callback_phone"] = entities.callback_phone
            session.pending_callback_phone_confirm = False
            session.pending_alt_callback_phone = False
        elif getattr(entities, "uses_this_number", False):
            session.pending_callback_phone_confirm = True
            session.pending_alt_callback_phone = False
        if getattr(entities, "callback_ambiguous_noon", False):
            session.pending_ampm_hour = 12

    if venue_ok and data.get("venue_type") == "home" and not data.get("venue_area"):
        data["event_location"] = None
        loc_slot = session.slots.get("event_location")
        if loc_slot:
            loc_slot.collected = False
            loc_slot.value = None

    if entities.special_requests and "special_requests" in allowed:
        notes = data.get("notes") or ""
        marker = f"[Custom Request]: {entities.special_requests}"
        if marker not in notes:
            data["notes"] = f"{notes}\n{marker}".strip()
        slot = session.slots.setdefault("special_requests", SlotValue())
        slot.value = entities.special_requests
        slot.confidence = max(slot.confidence, 0.9)
        slot.collected = True

    session.fields = EnquiryFields(**data)
    sync_slots_from_fields(session)


def slot_collected(session: ConversationSession, key: str) -> bool:
    return session.slots.get(key, SlotValue()).collected
