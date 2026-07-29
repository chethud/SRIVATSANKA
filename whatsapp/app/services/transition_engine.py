"""Deterministic forward-only guided-state transitions."""

from __future__ import annotations

from app.services.session_store import ConversationSession, GuidedStep


STATE_ORDER = {
    GuidedStep.AWAIT_HI: 0,
    GuidedStep.AWAIT_NAME: 1,
    GuidedStep.AWAIT_EVENT_TYPE: 2,
    GuidedStep.AWAIT_POST_SHOWCASE: 3,
    GuidedStep.COLLECT_DETAILS: 4,
    GuidedStep.DONE: 5,
}


def move_to(session: ConversationSession, next_step: GuidedStep) -> None:
    if STATE_ORDER[next_step] < STATE_ORDER[session.guided_step]:
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
    fields = session.fields
    if fields.customer_name and session.guided_step == GuidedStep.AWAIT_HI:
        move_to(session, GuidedStep.AWAIT_EVENT_TYPE if not fields.event_type else GuidedStep.AWAIT_POST_SHOWCASE)
    if fields.event_type and session.guided_step in {GuidedStep.AWAIT_NAME, GuidedStep.AWAIT_EVENT_TYPE}:
        move_to(session, GuidedStep.AWAIT_POST_SHOWCASE)
    if fields.event_date and session.guided_step == GuidedStep.AWAIT_POST_SHOWCASE:
        move_to(session, GuidedStep.COLLECT_DETAILS)
