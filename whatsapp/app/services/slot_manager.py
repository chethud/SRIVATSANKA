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
        GuidedStep.AWAIT_HI,
        GuidedStep.AWAIT_NAME,
        GuidedStep.AWAIT_NAME_CONFIRM,
        GuidedStep.AWAIT_EVENT_TYPE,
        GuidedStep.AWAIT_POST_SHOWCASE,
    }

    if step in {GuidedStep.AWAIT_HI, GuidedStep.AWAIT_NAME, GuidedStep.AWAIT_NAME_CONFIRM}:
        allowed.add("customer_name")
        allowed.add("event_type")
    elif step == GuidedStep.AWAIT_EVENT_TYPE:
        allowed.add("event_type")
    elif step == GuidedStep.AWAIT_POST_SHOWCASE:
        if entities.callback_requested:
            allowed.add("preferred_callback")
        allowed.add("special_requests")
    elif step == GuidedStep.COLLECT_DETAILS:
        data = session.fields.model_dump()
        for key in (
            "event_date",
            "guest_count",
            "event_location",
            "meal_preference",
            "preferred_callback",
        ):
            if data.get(key) in (None, ""):
                allowed.add(key)
        allowed.add("special_requests")
        if entities.callback_requested:
            allowed.add("preferred_callback")
    elif step == GuidedStep.DONE:
        allowed.add("special_requests")

    # Capture details whenever the customer volunteers them, even before detail collection.
    if step in early_steps:
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
            if not (
                entities.callback_requested
                or session.last_asked_slot == "preferred_callback"
                or has_callback_intent(str(value))
            ):
                continue
            if session.guided_step not in {
                GuidedStep.COLLECT_DETAILS,
                GuidedStep.AWAIT_POST_SHOWCASE,
            } and not entities.callback_requested:
                continue
        # Name stays pending until Yes confirmation (STATE 1.2)
        if key == "customer_name" and not session.name_confirmed:
            session.pending_name = clean_person_name(str(value)) or str(value).strip()
            continue
        if key == "event_location":
            cname = (data.get("customer_name") or session.pending_name or "").strip().lower()
            etype = (data.get("event_type") or "").strip().lower()
            val = str(value).strip().lower()
            if (cname and val == cname) or (etype and val == etype):
                continue
        if data.get(key) in (None, ""):
            data[key] = value
        slot = session.slots.setdefault(key, SlotValue())
        slot.value = data[key]
        slot.confidence = max(slot.confidence, 0.85)
        slot.collected = True

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
