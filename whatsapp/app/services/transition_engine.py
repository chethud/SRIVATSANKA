"""Deterministic forward-only guided-state transitions."""

from __future__ import annotations

from app.services.session_store import ConversationSession, GuidedStep


STATE_ORDER = {
    GuidedStep.AWAIT_HI: 0,
    GuidedStep.AWAIT_NAME: 1,
    GuidedStep.AWAIT_NAME_CONFIRM: 2,
    GuidedStep.AWAIT_EVENT_TYPE: 3,
    GuidedStep.AWAIT_OTHER_EVENT: 4,
    GuidedStep.AWAIT_POST_SHOWCASE: 5,
    GuidedStep.PAST_SETUPS: 6,
    GuidedStep.SHOWING_EVENT_INFORMATION: 7,
    GuidedStep.COLLECT_DETAILS: 8,
    GuidedStep.AWAIT_BOOKING_CONFIRM: 9,
    GuidedStep.AWAIT_EDIT_FIELD: 9,
    GuidedStep.AWAIT_CANCEL_CONFIRM: 9,
    GuidedStep.DONE: 10,
}


def move_to(session: ConversationSession, next_step: GuidedStep, *, force: bool = False) -> None:
    if not force and STATE_ORDER[next_step] < STATE_ORDER[session.guided_step]:
        return
    if session.guided_step != next_step:
        session.previous_guided_step = session.guided_step
        session.guided_step = next_step
        # New state = fresh failure budget (rules: 3 failed turns *in the same state*)
        session.failed_turns_in_state = 0
        session.consecutive_loop_count = 0
        session.slot_fail_counts = {}
        session.last_asked_slot = None
        session.last_assistant_question = None


def advance_from_slots(session: ConversationSession) -> None:
    """Skip ahead only when required slots for later states are already filled.

    Rules STATE 1.5: event without name must NOT skip past name collection.
    Rules STATE 1.2: never skip past name confirmation until name_confirmed is true.
    """
    fields = session.fields
    # Name confirmation is decided by the name handlers (skip Yes/No when confident).
    if not session.name_confirmed:
        return
    if fields.customer_name and session.guided_step in {
        GuidedStep.AWAIT_HI,
        GuidedStep.AWAIT_NAME,
        GuidedStep.AWAIT_NAME_CONFIRM,
    }:
        move_to(
            session,
            GuidedStep.AWAIT_EVENT_TYPE if not fields.event_type else GuidedStep.AWAIT_POST_SHOWCASE,
        )
    if fields.event_type and session.guided_step == GuidedStep.AWAIT_EVENT_TYPE:
        move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
    if session.guided_step in {
        GuidedStep.PAST_SETUPS,
        GuidedStep.SHOWING_EVENT_INFORMATION,
        GuidedStep.AWAIT_POST_SHOWCASE,
        GuidedStep.AWAIT_OTHER_EVENT,
        GuidedStep.AWAIT_BOOKING_CONFIRM,
        GuidedStep.AWAIT_EDIT_FIELD,
        GuidedStep.AWAIT_CANCEL_CONFIRM,
    }:
        return
