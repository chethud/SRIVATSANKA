"""Callback time parser + enquiry integration tests — run: python scripts/test_callback_time.py"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import os
os.environ["TESTING"] = "true"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from starlette.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.callback_time import (  # noqa: E402
    format_callback_display,
    normalize_callback_label,
    parse_callback_time,
)
from app.services.enquiry_service import _callback_text_from_notes  # noqa: E402

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  OK  {name}")


def bad(name: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL {name}" + (f" — {detail}" if detail else ""))


def test_parser_cases() -> None:
    print("--- Parser unit tests ---")
    ref = datetime(2026, 6, 3, 10, 0, 0)

    cases: list[tuple[str, datetime]] = [
        ("tomorrow 4pm", datetime(2026, 6, 4, 16, 0)),
        ("today 4pm", datetime(2026, 6, 3, 16, 0)),
        ("tomorrow afternoon", datetime(2026, 6, 4, 14, 0)),
        # Exactly at morning slot → roll forward (already "past")
        ("today morning", datetime(2026, 6, 4, 10, 0)),
        ("in 2 hours", datetime(2026, 6, 3, 12, 0)),
        ("Imideatly", datetime(2026, 6, 3, 10, 10)),
        ("asap", datetime(2026, 6, 3, 10, 10)),
        ("right now", datetime(2026, 6, 3, 10, 10)),
        ("4:30 PM", datetime(2026, 6, 3, 16, 30)),
        ("4pm", datetime(2026, 6, 3, 16, 0)),
        ("tomorrow 4:30 pm", datetime(2026, 6, 4, 16, 30)),
        ("day after tomorrow evening", datetime(2026, 6, 5, 18, 0)),
        ("in 30 min", datetime(2026, 6, 3, 10, 30)),
        ("today evening", datetime(2026, 6, 3, 18, 0)),
        ("call me tomorrow morning", datetime(2026, 6, 4, 10, 0)),
        ("tommarow @6pm", datetime(2026, 6, 4, 18, 0)),
        ("tomorow 6pm", datetime(2026, 6, 4, 18, 0)),
        ("today @6pm", datetime(2026, 6, 3, 18, 0)),
        ("Call me today evening after 7", datetime(2026, 6, 3, 19, 0)),
        ("Tomorrow morning around 11", datetime(2026, 6, 4, 11, 0)),
        ("Maybe day after around tea time", datetime(2026, 6, 5, 16, 0)),
    ]

    for text, expected in cases:
        got = parse_callback_time(text, ref)
        if got == expected:
            ok(f"parse {text!r} -> {got.strftime('%d %b %H:%M')}")
        else:
            bad(f"parse {text!r}", f"got {got}, expected {expected}")

    ref_evening = datetime(2026, 6, 3, 17, 0, 0)
    got = parse_callback_time("today 4pm", ref_evening)
    expected = datetime(2026, 6, 4, 16, 0)
    if got == expected:
        ok("today 4pm rolls to tomorrow when already past")
    else:
        bad("today 4pm past-time rollover", f"got {got}, expected {expected}")

    display = format_callback_display(datetime(2026, 6, 4, 16, 0), "tomorrow 4pm")
    if "04 Jun 2026" in display and "tomorrow 4pm" in display:
        ok("format_callback_display includes original text")
    else:
        bad("format_callback_display", display)

    if normalize_callback_label("Imideatly") == "Immediately":
        ok("normalize_callback_label fixes Imideatly")
    else:
        bad("normalize_callback_label", normalize_callback_label("Imideatly"))

    asap_display = format_callback_display(datetime(2026, 7, 23, 1, 19), "Imideatly")
    if "23 Jul 2026" in asap_display and "Immediately" in asap_display and "Imideatly" not in asap_display:
        ok("ASAP display uses IST date + Immediately label")
    else:
        bad("ASAP display", asap_display)

    # Server UTC evening must still schedule in IST calendar when now is aware UTC
    from datetime import timezone

    utc_evening = datetime(2026, 7, 22, 19, 39, tzinfo=timezone.utc)  # 01:09 IST Jul 23
    got_ist = parse_callback_time("Imideatly", utc_evening)
    if got_ist.date() == datetime(2026, 7, 23).date() and got_ist.hour == 1:
        ok("UTC server clock maps Immediate to IST Jul 23")
    else:
        bad("UTC→IST immediate", str(got_ist))

    notes = "Callback requested: tomorrow 4pm\nCallback scheduled: 04 Jun 2026, 04:00 PM"
    extracted = _callback_text_from_notes(notes)
    if extracted == "tomorrow 4pm":
        ok("_callback_text_from_notes extracts original")
    else:
        bad("_callback_text_from_notes", str(extracted))


def test_bot_flows() -> None:
    print("\n--- Bot flow integration ---")
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"username": "Admin", "password": "Admin@123"})
        if login.status_code != 200:
            bad("login for bot test", login.text[:120])
            return
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Test standard flow with "tomorrow 4pm"
        phone = f"91{uuid.uuid4().int % 10**10:010d}"
        callback_text = "tomorrow 4pm"
        expected_callback = parse_callback_time(callback_text)

        steps = [
            "new",
            "Hi",
            "Test User",
            "Wedding",
            "ok",
            "15 June 2026",
            "Whitefield",
            callback_text,
            "skip",
        ]

        last = None
        for msg in steps:
            r = client.post("/dev/message", headers=headers, json={"from_number": phone, "text": msg})
            if r.status_code != 200:
                bad(f"POST /dev/message ({msg!r})", r.text[:200])
                return
            last = r.json()

        if not last:
            bad("bot flow", "no responses")
            return

        if not last.get("enquiry_saved"):
            bad("enquiry_saved flag", str(last))
            return
        ok("bot flow saves enquiry after meal step")

        fields = last.get("fields") or {}
        if fields.get("preferred_callback") == callback_text:
            ok("session fields retain preferred_callback text")
        else:
            bad("preferred_callback in fields", str(fields.get("preferred_callback")))

        r = client.get("/api/enquiries", headers=headers)
        if r.status_code != 200:
            bad("GET /api/enquiries", str(r.status_code))
            return

        match = next((e for e in r.json() if e.get("phoneNumber") == phone), None)
        if not match:
            bad("enquiry in API list", f"phone {phone} not found")
            return
        ok("enquiry appears in /api/enquiries")

        saved_at = datetime.fromisoformat(match["preferredCallbackAt"].replace("Z", "+00:00"))
        if saved_at.tzinfo:
            saved_at = saved_at.replace(tzinfo=None)

        delta = abs((saved_at - expected_callback).total_seconds())
        if delta < 2:
            ok(f"preferredCallbackAt parsed correctly ({saved_at.strftime('%d %b %Y %I:%M %p')})")
        else:
            bad(
                "preferredCallbackAt mismatch",
                f"saved {saved_at}, expected {expected_callback}, delta {delta}s",
            )

        notes = match.get("notes") or ""
        if "Callback requested: tomorrow 4pm" in notes:
            ok("notes contain original callback text")
        else:
            bad("notes missing callback text", notes[:200])

        if "Callback scheduled:" in notes:
            ok("notes contain parsed callback display")
        else:
            bad("notes missing scheduled callback", notes[:200])

        # 2. Test Custom timing inputs and sign-off integration
        # Case 1: Call me today evening after 7
        phone1 = f"91{uuid.uuid4().int % 10**10:010d}"
        steps1 = ["new", "Hi", "Alice", "Wedding", "ok", "15 June 2026", "Whitefield", "Call me today evening after 7"]
        last_response = None
        for msg in steps1:
            r = client.post("/dev/message", headers=headers, json={"from_number": phone1, "text": msg})
            assert r.status_code == 200
            last_response = r.json()
        
        reply1 = last_response.get("reply") or ""
        expected_reply1 = "Perfect! We have scheduled a callback for today after 7:00 PM. Our team will reach out to you on this number. 📞"
        if expected_reply1 in reply1:
            ok("Alice gets custom response for 'today evening after 7'")
        else:
            bad("Alice response mismatch", f"got {reply1!r}")

        r = client.post("/dev/message", headers=headers, json={"from_number": phone1, "text": "skip"})
        assert r.status_code == 200
        final_reply1 = r.json().get("reply") or ""
        
        v_a = "Thank you so much, Alice! It was a absolute pleasure chatting with you. We’re thrilled at the opportunity to make your wedding truly unforgettable. ✨\n\nHave a wonderful rest of your day, and talk to you soon!"
        v_b = "Thank you, Alice! We’re honored to be considered for your big day. Our team will connect with you at the scheduled time. 🙏\n\nWishing you a lovely day ahead!"
        if final_reply1 in (v_a, v_b):
            ok("Alice gets valid Phase 7 emotional sign-off")
        else:
            bad("Alice sign-off mismatch", f"got {final_reply1!r}")

        # Case 2: Tomorrow morning around 11
        phone2 = f"91{uuid.uuid4().int % 10**10:010d}"
        steps2 = ["new", "Hi", "Bob", "Birthday", "ok", "15 June 2026", "Whitefield", "Tomorrow morning around 11"]
        for msg in steps2:
            r = client.post("/dev/message", headers=headers, json={"from_number": phone2, "text": msg})
            assert r.status_code == 200
            last_response = r.json()
        reply2 = last_response.get("reply") or ""
        expected_reply2 = "Noted, Bob! We’ll give you a call tomorrow around 11:00 AM. 🗓️"
        if expected_reply2 in reply2:
            ok("Bob gets custom response for 'tomorrow morning around 11'")
        else:
            bad("Bob response mismatch", f"got {reply2!r}")

        # Case 3: Maybe day after around tea time
        phone3 = f"91{uuid.uuid4().int % 10**10:010d}"
        steps3 = ["new", "Hi", "Charlie", "Birthday", "ok", "15 June 2026", "Whitefield", "Maybe day after around tea time"]
        for msg in steps3:
            r = client.post("/dev/message", headers=headers, json={"from_number": phone3, "text": msg})
            assert r.status_code == 200
            last_response = r.json()
        reply3 = last_response.get("reply") or ""
        expected_reply3 = "Sounds great! We’ll give you a call day after tomorrow between 4:00 PM and 5:00 PM. ☕"
        if expected_reply3 in reply3:
            ok("Charlie gets custom response for 'maybe day after around tea time'")
        else:
            bad("Charlie response mismatch", f"got {reply3!r}")

        r = client.post("/dev/message", headers=headers, json={"from_number": phone3, "text": "skip"})
        assert r.status_code == 200
        final_reply3 = r.json().get("reply") or ""
        v_a_charlie = "Thank you so much, Charlie! It was a absolute pleasure chatting with you. We’re thrilled at the opportunity to make your birthday truly unforgettable. ✨\n\nHave a wonderful rest of your day, and talk to you soon!"
        v_b_charlie = "Thank you, Charlie! We’re honored to be considered for your big day. Our team will connect with you at the scheduled time. 🙏\n\nWishing you a lovely day ahead!"
        if final_reply3 in (v_a_charlie, v_b_charlie):
            ok("Charlie gets valid Phase 7 emotional sign-off (birthday event)")
        else:
            bad("Charlie sign-off mismatch", f"got {final_reply3!r}")

        # Case 4: Test General / Fallback to celebration for event type
        from app.services.session_store import ConversationSession, EnquiryFields
        mock_sess = ConversationSession(whatsapp_id="123")
        mock_sess.fields = EnquiryFields(customer_name="Testy", event_type="General", preferred_callback="in 2 hours")
        from app.services.dish_flow import _format_confirmation
        conf_res = _format_confirmation(mock_sess)
        v_a_fallback = "Thank you so much, Testy! It was a absolute pleasure chatting with you. We’re thrilled at the opportunity to make your celebration truly unforgettable. ✨\n\nHave a wonderful rest of your day, and talk to you soon!"
        v_b_fallback = "Thank you, Testy! We’re honored to be considered for your big day. Our team will connect with you at the scheduled time. 🙏\n\nWishing you a lovely day ahead!"
        if conf_res in (v_a_fallback, v_b_fallback):
            ok("Direct _format_confirmation resolves 'General' to 'celebration' and returns correct sign-off")
        else:
            bad("Direct _format_confirmation general fallback mismatch", conf_res)


def main() -> int:
    print("=== Callback time tests ===\n")
    test_parser_cases()
    test_bot_flows()
    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
