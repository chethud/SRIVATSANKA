"""Conversation engine regressions: Kariya-style bugs + book-again + idempotency.

Run: python scripts/test_conversation_engine.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["TESTING"] = "true"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COMPLETION_MARKERS = (
    "we've noted your additional details",
    "noted your additional details",
    "traditional catering",
)


def _low(text: str) -> str:
    return (text or "").lower()


async def _turn(phone: str, text: str, db):
    from app.services.conversation_handler import handle_conversation

    result, saved = await handle_conversation(phone, text, db)
    return result, saved


async def run() -> int:
    from app.schemas import EnquiryFields
    from app.services.callback_time import normalize_callback_label
    from app.services.session_store import GuidedStep, session_store
    from app.services.conversation_turns import extract_name, is_greeting_only
    from app.services.venue_parser import parse_venue_reply

    failures: list[str] = []
    db = AsyncMock()
    phone = "919911122233"

    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"  FAIL {msg}")

    def ok(msg: str) -> None:
        print(f"  OK   {msg}")

    for greet in (
        "hlo kannan",
        "hi kannan",
        "hello Kannan sir",
        "hi bro kannan",
        "namaste kannan",
        "good morning kannan",
        "Kannan",
        "Hai sir",
        "hai sir",
        "hello madam",
        "hlo sir",
        "hi madam",
    ):
        if extract_name(greet):
            fail(f"greeting {greet!r} extracted name {extract_name(greet)!r}")
        elif greet.lower() != "kannan" and not is_greeting_only(greet):
            fail(f"{greet!r} not classified as greeting")
        else:
            ok(f"{greet!r} is greeting, not customer name")

    for intro in ("my name is Kannan", "I am Kannan", "this is Kannan", "Kannan here"):
        got = extract_name(intro)
        if got.lower() != "kannan":
            fail(f"{intro!r} expected Kannan, got {got!r}")
        else:
            ok(f"{intro!r} → Kannan")

    venue = parse_venue_reply("its a house warming its already fixed")
    if venue.status != "fixed" or venue.location:
        fail(f"venue parse expected fixed/empty, got {venue}")
    else:
        ok("venue already-fixed does not invent a location")

    label = normalize_callback_label("today evening would be great")
    if label != "this evening":
        fail(f"callback label expected 'this evening', got {label!r}")
    else:
        ok("callback preference normalized")

    with (
        patch("app.services.conversation_handler.resume_bot_for_phone", new_callable=AsyncMock),
        patch("app.services.conversation_handler.save_enquiry", new_callable=AsyncMock),
        patch("app.services.guided_flow.prepare_gallery_photos", new_callable=AsyncMock, return_value=[]),
    ):
        session_store.reset(phone)
        r, _ = await _turn(phone, "hlo kannan", db)
        first = session_store.get(phone)
        if first.fields.customer_name or first.pending_name:
            fail("hlo kannan saved a customer name from the first message")
        if "kannan" in _low(r.reply) and ("confirm" in _low(r.reply) or "is it" in _low(r.reply) or "your name is" in _low(r.reply)):
            fail("hlo kannan asked to confirm Kannan as customer")
        elif "namaskara" not in _low(r.reply) or "name" not in _low(r.reply):
            fail("hlo kannan did not send the fixed greeting")
        else:
            ok("hlo kannan → welcome, ask customer name")
        session_store.reset(phone)
        r, _ = await _turn(phone, "I am Chetan", db)
        chetan = session_store.get(phone)
        if chetan.fields.customer_name or (chetan.pending_name or "").lower() == "chetan":
            fail("first message 'I am Chetan' saved the name")
        if "is it chetan" in _low(r.reply):
            fail("first message asked to confirm Chetan")
        if "namaskara" not in _low(r.reply):
            fail("first message I am Chetan did not send fixed greeting")
        else:
            ok("first message I am Chetan ignored for name")
        session_store.reset(phone)

        r, _ = await _turn(phone, "Hi", db)
        if "namaskara" not in _low(r.reply) or "name" not in _low(r.reply):
            fail("hi: missing welcome/name ask")
        elif session_store.get(phone).fields.customer_name:
            fail("hi saved a customer name")
        else:
            ok("hi → welcome")

        r, _ = await _turn(phone, "i am kariya", db)
        after_name = session_store.get(phone)
        if after_name.fields.customer_name:
            fail("name saved before Yes confirmation")
        if after_name.name_confirmed:
            fail("name_confirmed before Yes")
        if "kariya" not in _low(r.reply):
            fail("name welcome missing Kariya")
        elif "is it kariya" not in _low(r.reply):
            fail("did not ask to confirm Kariya")
        else:
            ok("name captured → Yes/No confirm")

        r, _ = await _turn(phone, "Yes", db)
        if not session_store.get(phone).name_confirmed:
            fail("Yes did not confirm the name")
        elif "lovely to connect" not in _low(r.reply) and "what are you planning" not in _low(r.reply) and "select" not in _low(r.reply):
            fail(f"after name Yes, expected event-type list, got {r.reply!r}")
        else:
            ok("name confirmed → event types")

        r, _ = await _turn(phone, "housewarming ceremony i am planning for around 30 people", db)
        if "know more" not in _low(r.reply) and "services and options" not in _low(r.reply) and "would you like" not in _low(r.reply):
            fail(f"event intro missing info Yes/No, got {r.reply!r}")
        else:
            ok("event + guests captured, info Yes/No shown")

        session = session_store.get(phone)
        r, _ = await _turn(phone, "yes", db)
        if "traditional catering" in _low(r.reply) and "plan my event" not in _low(r.reply) and "srivatsanka" not in _low(r.reply):
            fail("yes after event did not show event information")
        if session_store.get(phone).guided_step not in {
            GuidedStep.SHOWING_EVENT_INFORMATION,
            GuidedStep.PAST_SETUPS,
            GuidedStep.AWAIT_POST_SHOWCASE,
        }:
            fail(f"info yes advanced unexpectedly to {session_store.get(phone).guided_step}")
        else:
            ok("Yes → event information")

        r, _ = await _turn(phone, "what kind of cuisines you guys have as an option", db)
        if "south indian" not in _low(r.reply) and "cuisine" not in _low(r.reply):
            fail("cuisine question not answered")
        if "coming back" not in _low(r.reply) and "plan" not in _low(r.reply) and "know more" not in _low(r.reply):
            fail("cuisine answer did not restore booking prompt")
        if session_store.get(phone).guided_step not in {
            GuidedStep.AWAIT_POST_SHOWCASE,
            GuidedStep.PAST_SETUPS,
            GuidedStep.SHOWING_EVENT_INFORMATION,
        }:
            fail(f"cuisine question changed state to {session_store.get(phone).guided_step}")
        else:
            ok("cuisine question answered without leaving intro")

        r, _ = await _turn(phone, "event", db)
        if "date" not in _low(r.reply) and "month" not in _low(r.reply):
            fail("event did not start date collection")
        else:
            ok("event → date collection")

        session = session_store.get(phone)
        r, _ = await _turn(phone, "33 november 2026 is the tentative date", db)
        if "valid date" not in _low(r.reply):
            fail("invalid date did not ask for clarification")
        if "start fresh" in _low(r.reply) or "tangled" in _low(r.reply):
            fail("invalid date restarted the conversation")
        if session_store.get(phone).guided_step != GuidedStep.COLLECT_DETAILS:
            fail(f"invalid date left COLLECT_DETAILS, now {session_store.get(phone).guided_step}")
        if (session_store.get(phone).fields.customer_name or "").lower() != "kariya":
            fail("invalid date cleared the customer name")
        else:
            ok("invalid date stays in event details")

        r, _ = await _turn(phone, "21 November 2026", db)
        if "venue" not in _low(r.reply) and "locality" not in _low(r.reply):
            fail("after date, expected venue question")
        else:
            ok("date stored, venue asked")

        r, _ = await _turn(phone, "its a house warming its already fixed", db)
        loc = session_store.get(phone).fields.event_location
        if loc:
            fail(f"stored fake location {loc!r}")
        if "venue name" not in _low(r.reply) and "name and area" not in _low(r.reply):
            fail("did not ask for venue name after fixed-without-name")
        if "noted down the location" in _low(r.reply):
            fail("echoed unusable venue text as confirmed")
        else:
            ok("venue_status=fixed, still asking for name/area")

        r, _ = await _turn(phone, "ABC Gardens", db)
        r, _ = await _turn(phone, "HSR Layout, Bengaluru", db)
        if session_store.get(phone).fields.event_location is None:
            fail("real venue was not stored")
        else:
            ok("real venue stored")

        r, _ = await _turn(phone, "Traditional Vegetarian", db)
        if "traditional" not in str(session_store.get(phone).fields.meal_preference or "").lower():
            fail("cuisine was not stored")
        else:
            ok("cuisine stored")

        r, _ = await _turn(phone, "No", db)
        if session_store.get(phone).last_asked_slot != "callback_date":
            fail(f"No on special req did not move to callback_date, asked={session_store.get(phone).last_asked_slot}")
        if "do you have any special requirements" in _low(r.reply):
            fail("No on special req looped the same question")
        r, _ = await _turn(phone, "today evening would be great", db)
        if session_store.get(phone).fields.callback_date is None:
            fail("today was not stored as callback date")
        if "morning" not in _low(r.reply) and "time of day" not in _low(r.reply) and "afternoon" not in _low(r.reply):
            fail("after callback date, expected time-of-day question")
        else:
            ok("callback date stored, asked time of day")

        # book again loop
        session = session_store.get(phone)
        session.completed = True
        session._saved = True
        session.guided_step = GuidedStep.DONE
        r, _ = await _turn(phone, "book again", db)
        if any(m in _low(r.reply) for m in COMPLETION_MARKERS):
            fail("book again sent completion copy")
        r, _ = await _turn(phone, "past setups", db)
        if "additional details" in _low(r.reply):
            fail("past setups after book again sent completion")
        else:
            ok("book again / past setups not completion")
        r, _ = await _turn(phone, "done", db)
        if "additional details" in _low(r.reply):
            fail("done after book again sent completion")
        else:
            ok("book again / DONE starts details")

        session_store.reset(phone)
        r, _ = await _turn(phone, "Hai sir", db)
        if session_store.get(phone).fields.customer_name or session_store.get(phone).pending_name:
            fail("Hai sir saved a customer name from the first message")
        if "hai sir" in _low(r.reply) or "is it hai" in _low(r.reply):
            fail("Hai sir treated as a customer name")
        elif "namaskara" not in _low(r.reply) or "name" not in _low(r.reply):
            fail("Hai sir did not ask for the customer name")
        else:
            ok("Hai sir → greeting, ask name")

        r, _ = await _turn(phone, "I am Sowmya", db)
        if session_store.get(phone).fields.customer_name:
            fail("Sowmya saved before Yes")
        if "sowmya" not in _low(r.reply):
            fail("Sowmya welcome missing")
        elif "is it sowmya" not in _low(r.reply):
            fail("Sowmya did not ask Yes/No")
        else:
            ok("I am Sowmya → name confirm")
        r, _ = await _turn(phone, "Yes", db)
        if "lovely to connect" not in _low(r.reply) and "what are you planning" not in _low(r.reply):
            fail("Yes after Sowmya did not open event selection")
        else:
            ok("Sowmya confirmed → events")

        r, _ = await _turn(phone, "Srimantha", db)
        if "celebration is this for" in _low(r.reply) and "seemantham" not in _low(r.reply) and "baby shower" not in _low(r.reply):
            fail("Srimantha was not recognized as a baby shower")
        else:
            ok("Srimantha → baby shower / Seemantham")

        sess = session_store.get(phone)
        if sess.guided_step == GuidedStep.AWAIT_EVENT_TYPE:
            r, _ = await _turn(phone, "Baby shower", db)
        r, _ = await _turn(phone, "No", db)
        r, _ = await _turn(phone, "November", db)
        r, _ = await _turn(phone, "200", db)
        r, _ = await _turn(phone, "Location is our house", db)
        if "noted down the location" in _low(r.reply) and "area" not in _low(r.reply) and "locality" not in _low(r.reply):
            fail("home venue skipped the area question")
        if "call" in _low(r.reply) and "area" not in _low(r.reply) and "locality" not in _low(r.reply):
            fail("home venue jumped to callback before area")
        else:
            ok("our house → ask locality")

        r, _ = await _turn(phone, "Sunkadakatte", db)
        if "share that again" in _low(r.reply):
            fail("Sunkadakatte was rejected as location")
        loc = session_store.get(phone).fields.event_location or ""
        area = session_store.get(phone).fields.venue_area or ""
        if "sunkadakatte" not in loc.lower() and "sunkadakatte" not in area.lower():
            fail(f"Sunkadakatte not stored, loc={loc!r} area={area!r}")
        else:
            ok("Sunkadakatte stored as venue area")

        r, _ = await _turn(phone, "South Indian", db)
        r, _ = await _turn(phone, "No", db)
        r, _ = await _turn(phone, "Tomorrow", db)
        if "tangled" in _low(r.reply) or "start fresh" in _low(r.reply):
            fail("Tomorrow restarted the chat")
        if "time" not in _low(r.reply):
            fail("Tomorrow did not ask for callback time")
        else:
            ok("Tomorrow → ask callback time")

        r, _ = await _turn(phone, "Please call to this number at 12", db)
        if "tangled" in _low(r.reply) or "start fresh" in _low(r.reply) or "may i know your name" in _low(r.reply):
            fail("callback instruction restarted the conversation")
        if session_store.get(phone).guided_step == GuidedStep.AWAIT_HI:
            fail("state was lost after callback instruction")
        if "alternative" not in _low(r.reply) and "this whatsapp" not in _low(r.reply) and "this number" not in _low(r.reply):
            fail("did not confirm WhatsApp number vs alternative")
        if "12" not in r.reply and "time" not in _low(r.reply) and "noted" not in _low(r.reply):
            fail("callback at 12 was not understood")
        else:
            ok("please call this number at 12 kept state")

        if session_store.get(phone).pending_ampm_hour == 12 or "12 pm" in _low(r.reply) or "12 p.m" in _low(r.reply):
            r, _ = await _turn(phone, "Yes", db)
        if "tangled" in _low(r.reply) or "start fresh" in _low(r.reply):
            fail("12 PM confirm restarted")
        else:
            ok("callback preference noted without restart")

        step_before = session_store.get(phone).guided_step
        name_before = session_store.get(phone).fields.customer_name
        r, _ = await _turn(phone, "8861829091", db)
        if "may i know your name" in _low(r.reply) or "who do we have" in _low(r.reply):
            fail("phone number reset to START")
        if (session_store.get(phone).fields.customer_name or "").lower() != (name_before or "").lower() and name_before:
            fail("phone number cleared customer name")
        if "tangled" in _low(r.reply):
            fail("phone number tripped restart")
        else:
            ok("phone number kept conversation state")

        # Isolated: special requirements must never write venue_area.
        session_store.reset("919900011122")
        spec_phone = "919900011122"
        sess = session_store.get(spec_phone)
        sess.guided_step = GuidedStep.COLLECT_DETAILS
        sess.name_confirmed = True
        sess.fields = EnquiryFields(
            customer_name="Test",
            event_type="Wedding",
            event_date="26 September 2026",
            date_status="confirmed",
            guest_count=500,
            event_location="BTM Layout",
            venue_area="BTM Layout",
            venue_status="fixed",
            meal_preference="To be discussed",
        )
        sess.last_asked_slot = "special_requirements_details"
        sess.awaiting_special_req_text = True
        r, _ = await _turn(spec_phone, "notjing", db)
        spec_sess = session_store.get(spec_phone)
        if (spec_sess.fields.venue_area or "").lower() == "notjing":
            fail("notjing was saved as venue_area")
        if spec_sess.fields.special_requirements is None:
            fail("notjing was not saved as special requirements")
        if spec_sess.last_asked_slot != "callback_date":
            fail(f"notjing did not advance to callback_date, asked={spec_sess.last_asked_slot}")
        if "special requirements" in _low(r.reply) and "don't have" not in _low(r.reply) and "do not have" not in _low(r.reply):
            fail("notjing re-asked special requirements")
        else:
            ok("notjing in SPECIAL_REQUIREMENTS → none, not venue")

        r, _ = await _turn(spec_phone, "No", db)
        if session_store.get(spec_phone).last_asked_slot == "special_requirements":
            fail("second No returned to SPECIAL_REQUIREMENTS")
        else:
            ok("No after requirements stays on callback")

    # Idempotency unit test with sqlite-like IntegrityError simulation
    from app.services.message_idempotency import claim_inbound_message

    class FakeDB:
        def __init__(self):
            self.ids = set()
            self._pending = None

        def add(self, row):
            self._pending = row

        async def commit(self):
            from sqlalchemy.exc import IntegrityError

            mid = self._pending.messageId
            if mid in self.ids:
                raise IntegrityError("dup", None, None)
            self.ids.add(mid)

        async def rollback(self):
            return None

        async def get(self, model, mid):
            obj = MagicMock()
            obj.status = "sent" if mid in self.ids else "claimed"
            return obj

    fake = FakeDB()
    first = await claim_inbound_message(fake, "wamid.AAA", "9199")
    second = await claim_inbound_message(fake, "wamid.AAA", "9199")
    if not first or second:
        fail("duplicate wamid was not ignored")
    else:
        ok("duplicate webhook message id ignored")

    if failures:
        print("\nFAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nAll conversation engine checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
