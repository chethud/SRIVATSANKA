"""Regression: book again keeps the name and does not send completed-booking copy.

Run: python scripts/test_book_again_loop.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["TESTING"] = "true"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COMPLETION_MARKERS = (
    "we've noted your additional details",
    "we’ve noted your additional details",
    "noted your additional details",
)


async def run() -> int:
    from app.schemas import EnquiryFields
    from app.services.conversation_handler import handle_conversation
    from app.services.session_store import ConversationState, GuidedStep, session_store
    from app.services.validation_layer import soft_reset_session

    phone = "919900011122"
    session_store.reset(phone)
    session = session_store.get(phone)
    session.completed = True
    session._saved = True
    session.name_confirmed = True
    session.guided_step = GuidedStep.DONE
    session.conversation_state = ConversationState.COMPLETED
    session.fields = EnquiryFields(
        customer_name="Tejasvi",
        event_type="Wedding",
        event_date="27 Nov 2026",
        event_location="Bengaluru",
        guest_count=200,
        preferred_callback="Evening",
        meal_preference="To be discussed on call",
    )
    session.slots["customer_name"].collected = True
    session.slots["customer_name"].value = "Tejasvi"
    session.slots["event_type"].collected = True
    session.slots["event_type"].value = "Wedding"

    db = AsyncMock()
    failures: list[str] = []

    def check(label: str, reply: str, *, must_not: tuple[str, ...] = COMPLETION_MARKERS) -> None:
        low = (reply or "").lower()
        print(f"\n--- {label} ---")
        print((reply or "")[:500].replace("\n", " | ").encode("ascii", "replace").decode("ascii"))
        for marker in must_not:
            if marker in low:
                failures.append(f"{label}: still sent completed-booking copy ({marker!r})")

    with (
        patch("app.services.conversation_handler.resume_bot_for_phone", new_callable=AsyncMock),
        patch("app.services.guided_flow.prepare_gallery_photos", new_callable=AsyncMock, return_value=[]),
    ):
        result, _ = await handle_conversation(phone, "book again", db)
        check("book again", result.reply, must_not=COMPLETION_MARKERS)
        if session.completed or session._saved:
            failures.append("book again: completed/_saved flags were not cleared")
        if session.guided_step != GuidedStep.AWAIT_EVENT_TYPE:
            failures.append(f"book again: expected AWAIT_EVENT_TYPE, got {session.guided_step}")
        if session.fields.event_date:
            failures.append("book again: booking form data was not cleared")
        if (session.fields.customer_name or "").lower() != "tejasvi":
            failures.append("book again: customer name was not preserved")
        if "type *done*" in (result.reply or "").lower():
            failures.append("book again: still asked to type DONE")

        result, _ = await handle_conversation(phone, "Wedding", db)
        check("select wedding", result.reply)
        if session.guided_step != GuidedStep.AWAIT_POST_SHOWCASE:
            failures.append(f"wedding: expected AWAIT_POST_SHOWCASE, got {session.guided_step}")

        result, _ = await handle_conversation(phone, "past setups", db)
        check("past setups", result.reply)
        if session.completed:
            failures.append("past setups: session marked completed again")
        if "type *done*" in (result.reply or "").lower() or "type done" in (result.reply or "").lower():
            failures.append("past setups: asked to type DONE")
        if "type *event*" in (result.reply or "").lower():
            failures.append("past setups: still asked to type event")

        result, _ = await handle_conversation(phone, "", db, button_id="plan_event")
        check("plan event", result.reply)
        if session.completed:
            failures.append("plan event: session marked completed")
        if session.guided_step != GuidedStep.COLLECT_DETAILS:
            failures.append(f"plan event: expected COLLECT_DETAILS, got {session.guided_step}")
        if "tentative date" not in (result.reply or "").lower() and "date or month" not in (result.reply or "").lower():
            failures.append("plan event: did not ask the first event-detail date question")

        session.completed = True
        session._saved = True
        session.guided_step = GuidedStep.DONE
        session.fields = EnquiryFields(
            customer_name="Tejasvi",
            event_type="Wedding",
            event_date="27 Nov 2026",
            event_location="Bengaluru",
            guest_count=200,
            preferred_callback="Evening",
        )
        session.name_confirmed = True
        result, _ = await handle_conversation(phone, "book again", db)
        check("book again 2", result.reply)
        result, _ = await handle_conversation(phone, "", db, button_id="info_no")
        check("info_no after book again", result.reply)

        session.completed = True
        session._saved = True
        soft_reset_session(session)
        if session.completed or session._saved:
            failures.append("soft_reset_session: did not clear completed/_saved")

    if failures:
        print("\nFAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nAll book-again loop checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
