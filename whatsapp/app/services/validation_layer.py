"""Validation and loop guard helpers for the guided FSM.

Source of truth: D:\\Kannan.rules.txt — Global FSM recovery + State 5 circuit breaker.
"""

from __future__ import annotations

from app.schemas import EnquiryFields
from app.services.session_store import (
    ConversationPhase,
    ConversationSession,
    ConversationState,
    GuidedStep,
)

RESET_PHRASES = frozenset(
    {
        "reset",
        "restart",
        "start over",
        "start again",
        "begin again",
    }
)

CIRCUIT_BREAKER_REPLY = (
    "It looks like we got a little tangled up! Let's start fresh. 🌿\n\n"
    "You can type **RESTART** at any time to kickstart our conversation from the beginning.\n\n"
    "Hello! Welcome to Srivatsanka Events and Services. ✨ May I have your name, please?"
)


def is_reset_message(text: str) -> bool:
    return text.strip().lower().rstrip("!.") in RESET_PHRASES


def is_cancel_message(text: str) -> bool:
    t = text.strip().lower().rstrip("!.")
    return t in {"cancel", "stop", "never mind", "nevermind", "not now"}


def track_question(session: ConversationSession, reply: str, *, slot_key: str | None = None) -> None:
    """Track asked slots for loop detection.

    Count by *slot* (not exact reply wording) so randomized prompts still trip the breaker.
    Streak starts at 1 on a new slot ask; a second ask of the same slot reaches 2.
    """
    if slot_key and session.last_asked_slot == slot_key:
        session.consecutive_loop_count += 1
    elif (
        not slot_key
        and session.last_assistant_question
        and session.last_assistant_question.strip() == reply.strip()
    ):
        session.consecutive_loop_count += 1
    else:
        session.consecutive_loop_count = 1 if slot_key else 0
    session.last_assistant_question = reply
    session.last_asked_slot = slot_key


def repeated_question(session: ConversationSession, reply: str) -> bool:
    return bool(
        session.last_assistant_question and session.last_assistant_question.strip() == reply.strip()
    )


def record_slot_failure(session: ConversationSession, *, slot_key: str | None = None) -> int:
    """Count failed collection attempts in the current guided step. Returns new fail count."""
    session.failed_turns_in_state += 1
    if slot_key:
        counts = dict(session.slot_fail_counts)
        counts[slot_key] = counts.get(slot_key, 0) + 1
        session.slot_fail_counts = counts
    return session.failed_turns_in_state


def slot_fail_count(session: ConversationSession, slot_key: str) -> int:
    return int(session.slot_fail_counts.get(slot_key, 0))


def clear_slot_failures(session: ConversationSession, slot_key: str | None = None) -> None:
    if slot_key is None:
        session.slot_fail_counts = {}
        session.failed_turns_in_state = 0
        session.consecutive_loop_count = 0
        return
    counts = dict(session.slot_fail_counts)
    counts.pop(slot_key, None)
    session.slot_fail_counts = counts


def should_trip_circuit_breaker(session: ConversationSession) -> bool:
    """Never auto-restart. Unexpected answers must re-ask the current field."""
    return False


def reset_session_to_greeting(session: ConversationSession) -> None:
    """Clear enquiry memory and return to STATE 1."""
    session.fields = EnquiryFields()
    session.history = []
    session.guided_step = GuidedStep.AWAIT_HI
    session.previous_guided_step = None
    session.showcase_prompted = False
    session.pending_name = None
    session.name_confirmed = False
    session.pending_date_confirm = None
    session.pending_event_type_switch = None
    session.consecutive_loop_count = 0
    session.last_assistant_question = None
    session.last_asked_slot = None
    session.failed_turns_in_state = 0
    session.slot_fail_counts = {}
    for key, slot in session.slots.items():
        slot.value = None
        slot.confidence = 0.0
        slot.collected = False
    session.completed = False
    session._saved = False
    session.phase = ConversationPhase.ENQUIRY
    session.selected_dishes = []
    session.selected_category_keys = []
    session.current_category_index = 0
    session.customization_dish_index = 0
    session.welcome_media_sent = False
    session.sent_gallery_urls = []
    session.last_user_message = None
    session.pending_ampm_hour = None
    session.pending_callback_phone_confirm = False
    session.pending_alt_callback_phone = False
    session.special_req_done = False
    session.awaiting_special_req_text = False
    session.conversation_state = ConversationState.START
    _stamp_session(session)


def soft_reset_session(session: ConversationSession) -> str:
    """Book-again: keep confirmed name and phone; clear event-specific booking data."""
    preserved = session.fields.model_dump()
    name = preserved.get("customer_name") if session.name_confirmed else None
    phone = preserved.get("phone_number")
    reset_session_to_greeting(session)
    if name:
        session.fields = EnquiryFields(customer_name=name, phone_number=phone)
        session.name_confirmed = True
        name_slot = session.slots["customer_name"]
        name_slot.value = name
        name_slot.confidence = 1.0
        name_slot.collected = True
        session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
        session.conversation_state = ConversationState.MAIN_MENU
        _stamp_session(session)
        return (
            f"Of course, {name}. We can start fresh. 😊\n\n"
            "What type of event are you planning?"
        )
    session.guided_step = GuidedStep.AWAIT_NAME
    session.conversation_state = ConversationState.MAIN_MENU
    _stamp_session(session)
    return (
        "Your previous planning session has been cleared. Let's start fresh. 😊\n\n"
        "May I know your name?"
    )


def cancel_to_main_menu(session: ConversationSession) -> str:
    """Cancel the current booking flow and return to the main menu."""
    name = session.fields.customer_name if session.name_confirmed else None
    reset_session_to_greeting(session)
    if name:
        session.fields = EnquiryFields(customer_name=name)
        session.name_confirmed = True
        name_slot = session.slots["customer_name"]
        name_slot.value = name
        name_slot.confidence = 1.0
        name_slot.collected = True
        session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
        session.conversation_state = ConversationState.MAIN_MENU
        _stamp_session(session)
        return f"No problem, {name}. What celebration would you like to plan?"
    from app.services.human_style import welcome_message

    session.conversation_state = ConversationState.START
    _stamp_session(session)
    return welcome_message()


def greeting_reset_reply(session: ConversationSession) -> str:
    """Full conversation restart (restart / menu)."""
    reset_session_to_greeting(session)
    return (
        "Your previous planning session has been cleared. Let's start fresh. 😊\n\n"
        "May I know your name?"
    )


def _stamp_session(session: ConversationSession) -> None:
    from datetime import datetime, timezone

    session.updated_at = datetime.now(timezone.utc)


def sync_conversation_state(session: ConversationSession) -> None:
    """Derive a stable conversation_state from guided_step + completion flags."""
    if session.completed and session._saved:
        session.conversation_state = ConversationState.COMPLETED
    elif session.guided_step == GuidedStep.AWAIT_BOOKING_CONFIRM:
        session.conversation_state = ConversationState.BOOKING_CONFIRMATION
    elif session.guided_step == GuidedStep.DONE:
        session.conversation_state = ConversationState.BOOKING_CONFIRMATION
    elif session.guided_step == GuidedStep.COLLECT_DETAILS:
        session.conversation_state = ConversationState.EVENT_DETAILS
    elif session.guided_step == GuidedStep.SHOWING_EVENT_INFORMATION:
        session.conversation_state = ConversationState.SHOWING_EVENT_INFORMATION
    elif session.guided_step == GuidedStep.PAST_SETUPS:
        session.conversation_state = ConversationState.PAST_SETUPS
    elif session.guided_step == GuidedStep.AWAIT_POST_SHOWCASE:
        session.conversation_state = ConversationState.NEW_BOOKING
    elif session.guided_step == GuidedStep.AWAIT_HI:
        session.conversation_state = ConversationState.INITIAL_GREETING
    elif session.guided_step in {GuidedStep.AWAIT_NAME, GuidedStep.AWAIT_NAME_CONFIRM}:
        session.conversation_state = ConversationState.WAITING_FOR_NAME
    else:
        session.conversation_state = ConversationState.MAIN_MENU
    _stamp_session(session)


def circuit_breaker_reply() -> str:
    return CIRCUIT_BREAKER_REPLY
