"""Replay Tejasvi WhatsApp transcript and flag known failure patterns.

Run: python scripts/test_tejasvi_flow.py
Optional: python scripts/test_tejasvi_flow.py --base http://13.232.230.198
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from pathlib import Path

os.environ["TESTING"] = "true"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"  FAIL {msg}")


def ok(msg: str) -> None:
    print(f"  OK   {msg}")


def check_reply(label: str, user: str, reply: str, fields: dict, *, media_count: int = 0) -> None:
    low = reply.lower()
    print(f"\n--- {label} ---")
    print(f"USER: {user}")
    print(f"BOT:  {reply[:400].replace(chr(10), ' | ')}")
    print(
        f"      fields: name={fields.get('customer_name')!r} event={fields.get('event_type')!r} "
        f"date={fields.get('event_date')!r} pax={fields.get('guest_count')!r} "
        f"loc={fields.get('event_location')!r} media={media_count}"
    )

    if "tangled up" in low or "start fresh" in low and user.lower().strip() in {"okay", "ok"}:
        fail(f"{label}: circuit breaker triggered on short ack")
    if "my name is" in (fields.get("customer_name") or "").lower():
        fail(f"{label}: name still contains intro phrase")
    if re.search(r"tentative date|date or month", low) and fields.get("event_date"):
        fail(f"{label}: re-asked date although event_date is set ({fields.get('event_date')})")
    if "benglore" in low:
        fail(f"{label}: echoed misspelled Bengaluru as Benglore")
    if user.lower().startswith("i already told") and "sorry" not in low and "noted" not in low:
        fail(f"{label}: did not acknowledge customer already provided info")
    if "callback is set for evening" in low or "callback is set for dinner" in low or "callback is set for lunch" in low:
        fail(f"{label}: confused meal type with callback time")
    if "unforgettable" in low:
        fail(f"{label}: overly promotional sign-off wording")
    if "could you share that again" in low and fields.get("event_location"):
        fail(f"{label}: re-asked location although event_location is set ({fields.get('event_location')})")


def run_local() -> None:
    from starlette.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"username": "Admin", "password": "Admin@123"})
        if login.status_code != 200:
            fail(f"login failed: {login.text[:120]}")
            return
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        phone = f"91{uuid.uuid4().int % 10**10:010d}"
        steps = [
            ("greeting+details", "Hi i am Tejasvi i am looking for a wedding catering pure veg the event is next nov 27th 2026"),
            ("confirm name", "Yes"),
            ("ask showcase", "What kind of weddings have you done please show"),
            ("already told date", "I already told the date show me pictures"),
            ("okay continue", "Okay"),
            ("restart", "Restart"),
            ("name only", "Tejasvi"),
            ("confirm name 2", "Yes"),
            ("upanayanam", "I want catering for my upanayanam"),
            ("skip showcase", "No"),
            ("ambiguous date", "Next month 2"),
            ("confirm date", "Yes"),
            ("pax", "33"),
            ("city typo", "Benglore"),
            ("callback", "Today evening"),
        ]
        for label, msg in steps:
            r = client.post("/dev/message", headers=headers, json={"from_number": phone, "text": msg})
            if r.status_code != 200:
                fail(f"{label}: HTTP {r.status_code} {r.text[:120]}")
                continue
            data = r.json()
            check_reply(label, msg, data.get("reply") or "", data.get("fields") or {}, media_count=len(data.get("media") or []))

        run_birthday_flow(client, headers)


def run_birthday_flow(client, headers) -> None:
    """Replay the Tejasvi birthday transcript that confused meal vs callback."""
    phone = f"91{uuid.uuid4().int % 10**10:010d}"
    steps = [
        ("hey", "Hey"),
        ("name", "Tejasvi jois"),
        ("confirm name", "Yes"),
        ("event", "Birthday"),
        ("skip showcase", "No"),
        ("date", "Dec 21"),
        ("pax", "30"),
        ("city", "Mysuru"),
        ("meal", "Evening dinner"),
        ("when call", "When will they call me"),
    ]
    last_fields: dict = {}
    for label, msg in steps:
        r = client.post("/dev/message", headers=headers, json={"from_number": phone, "text": msg})
        if r.status_code != 200:
            fail(f"birthday/{label}: HTTP {r.status_code} {r.text[:120]}")
            continue
        data = r.json()
        fields = data.get("fields") or {}
        last_fields = fields
        check_reply(f"birthday/{label}", msg, data.get("reply") or "", fields)
    if last_fields.get("meal_preference") and "dinner" not in str(last_fields.get("meal_preference")).lower():
        fail("birthday: meal_preference not stored for evening dinner")
    if last_fields.get("preferred_callback") and "dinner" in str(last_fields.get("preferred_callback")).lower():
        fail("birthday: preferred_callback incorrectly set to meal type")
    else:
        ok("birthday: meal and callback fields kept separate")


def run_remote(base: str) -> None:
    import httpx

    base = base.rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as client:
        login = client.post("/api/auth/login", json={"username": "Admin", "password": "Admin@123"})
        if login.status_code != 200:
            fail(f"remote login failed: {login.status_code}")
            return
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        phone = f"91{uuid.uuid4().int % 10**10:010d}"
        steps = [
            ("greeting+details", "Hi i am Tejasvi i am looking for a wedding catering pure veg the event is next nov 27th 2026"),
            ("confirm name", "Yes"),
            ("ask showcase", "What kind of weddings have you done please show"),
            ("already told date", "I already told the date show me pictures"),
            ("okay continue", "Okay"),
        ]
        for label, msg in steps:
            r = client.post("/dev/message", headers=headers, json={"from_number": phone, "text": msg})
            if r.status_code != 200:
                fail(f"{label}: HTTP {r.status_code} {r.text[:120]}")
                continue
            data = r.json()
            check_reply(label, msg, data.get("reply") or "", data.get("fields") or {}, media_count=len(data.get("media") or []))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Test against remote API (e.g. http://13.232.230.198)")
    args = parser.parse_args()

    print("=== Tejasvi WhatsApp flow test ===")
    if args.base:
        print(f"Target: {args.base}")
        run_remote(args.base)
    else:
        print("Target: local TestClient")
        run_local()

    print(f"\n=== Summary: {len(FAILURES)} failure(s) ===")
    for f in FAILURES:
        print(f"  - {f}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
