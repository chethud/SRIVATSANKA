"""Validation and loop guard helpers for the guided FSM.

Source of truth: D:\\Kannan.rules.txt — Global FSM recovery + State 5 circuit breaker.
"""

from __future__ import annotations

from app.schemas import EnquiryFields
from app.services.session_store import ConversationSession, GuidedStep

RESET_PHRASES = frozenset(
    {
        "reset",
        "restart",
        "start over",
        "begin again",
        "main menu",
    }
)

CIRCUIT_BREAKER_REPLY = (
    "It looks like we got a little tangled up! Let's start fresh. 🌿\n\n"
    "You can type **RESTART** at any time to kickstart our conversation from the beginning.\n\n"
    "Hello! Welcome to Srivatsanka Events & Catering. ✨ May I have your name, please?"
)


def is_reset_message(text: str) -> bool:
    return text.strip().lower().rstrip("!.") in RESET_PHRASES


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
    """Rules: consecutive_loop_count >= 2 OR 3 failed turns in the same state.

    Streak semantics: first ask sets count=1, second identical-slot ask sets count=2.
    Trip only once we are about to ask a *third* time (count >= 3), or after 3 hard failures.
    Asking twice (greeting + clarify) must not wipe the session before the user can answer.
    """
    return session.consecutive_loop_count >= 3 or session.failed_turns_in_state >= 3


def reset_session_to_greeting(session: ConversationSession) -> None:
    """Clear enquiry memory and return to STATE 1."""
    session.fields = EnquiryFields()
    session.history = []
    session.guided_step = GuidedStep.AWAIT_HI
    session.previous_guided_step = None
    session.showcase_prompted = False
    session.pending_name = None
    session.name_confirmed = False
    session.consecutive_loop_count = 0
    session.last_assistant_question = None
    session.last_asked_slot = None
    session.failed_turns_in_state = 0
    session.slot_fail_counts = {}
    for key, slot in session.slots.items():
        slot.value = None
        slot.confidence = 0.0
        slot.collected = False


def circuit_breaker_reply() -> str:
    return CIRCUIT_BREAKER_REPLY
