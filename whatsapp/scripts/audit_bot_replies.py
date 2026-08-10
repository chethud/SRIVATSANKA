"""Audit WhatsApp bot replies against Kannan.rules.txt scenarios.

Run: python scripts/audit_bot_replies.py
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

os.environ["TESTING"] = "true"

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from starlette.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASS = 0
FAIL = 0
ISSUES: list[str] = []


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  OK  {name}")


def bad(name: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    msg = f"  FAIL {name}" + (f" — {detail}" if detail else "")
    print(msg.encode("ascii", "backslashreplace").decode("ascii"))
    ISSUES.append(msg)


def guardrail_check(reply: str, label: str) -> None:
    if "—" in reply or "–" in reply:
        bad(f"{label}: em-dash", repr(reply[:120]))
    else:
        ok(f"{label}: no em-dash")
    if re.search(r"(?m)^\s*\d+\.\s+\w+", reply) or re.search(r"\b1\.\s+\w+.+\b2\.\s+\w+", reply):
        bad(f"{label}: numbered picker", repr(reply[:160]))
    else:
        ok(f"{label}: no numbered picker")
    # Stacked Intent B copy (two planning preambles in one reply)
    planning_hits = len(
        re.findall(
            r"(jump straight into|get right down to planning|help you plan directly)",
            reply,
            flags=re.I,
        )
    )
    if planning_hits > 1:
        bad(f"{label}: duplicate planning preamble", repr(reply[:220]))
    else:
        ok(f"{label}: single planning preamble")


def safe(text: str) -> str:
    return text.encode("ascii", "backslashreplace").decode("ascii")


def run_scenario(client: TestClient, headers: dict[str, str], label: str, steps: list[str]) -> list[dict]:
    print(f"\n=== {label} ===")
    phone = f"91{uuid.uuid4().int % 10**10:010d}"
    turns: list[dict] = []
    for msg in steps:
        r = client.post("/dev/message", headers=headers, json={"from_number": phone, "text": msg})
        if r.status_code != 200:
            bad(f"{label} HTTP for {msg!r}", r.text[:160])
            return turns
        data = r.json()
        reply = data.get("reply") or ""
        fields = data.get("fields") or {}
        print(f"USER: {msg!r}")
        print(f"BOT:  {safe(reply.replace(chr(10), ' | ')[:320])}")
        print(
            "      "
            f"complete={data.get('is_complete')} saved={data.get('enquiry_saved')} "
            f"name={fields.get('customer_name')!r} event={fields.get('event_type')!r} "
            f"date={fields.get('event_date')!r} pax={fields.get('guest_count')!r} "
            f"loc={fields.get('event_location')!r} meal={fields.get('meal_preference')!r} "
            f"cb={fields.get('preferred_callback')!r}"
        )
        print()
        guardrail_check(reply, f"{label}/{msg!r}")
        turns.append(data)
    return turns


def main() -> int:
    print("=== WhatsApp bot reply audit ===\n")
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"username": "Admin", "password": "Admin@123"})
        if login.status_code != 200:
            print("Login failed", login.text[:200])
            return 1
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        happy = run_scenario(
            client,
            headers,
            "HAPPY_PATH",
            [
                "new",
                "Hi",
                "Test User",
                "Wedding",
                "ok",
                "15 June 2026",
                "150 guests",
                "Whitefield",
                "tomorrow 4pm",
            ],
        )
        if happy and happy[-1].get("enquiry_saved"):
            ok("HAPPY_PATH enquiry_saved")
        else:
            bad("HAPPY_PATH enquiry_saved", str((happy[-1] if happy else {}).get("is_complete")))

        multi = run_scenario(
            client,
            headers,
            "MULTI_ENTITY",
            ["new", "Hi I am Tejasvi planning a baby shower"],
        )
        if multi:
            fields = multi[-1].get("fields") or {}
            if fields.get("customer_name") and "Tejasvi" in str(fields.get("customer_name")):
                ok("MULTI_ENTITY captured name")
            else:
                bad("MULTI_ENTITY name", str(fields.get("customer_name")))
            if fields.get("event_type"):
                ok("MULTI_ENTITY captured event")
            else:
                bad("MULTI_ENTITY event", str(fields.get("event_type")))

        run_scenario(client, headers, "EVENT_NO_NAME", ["new", "Looking for wedding catering"])
        run_scenario(client, headers, "PORTFOLIO", ["new", "Hi", "Anita", "What events do you cater to?"])
        run_scenario(
            client,
            headers,
            "URGENT",
            ["new", "Hi", "Ravi", "Wedding", "ok", "Tomorrow"],
        )
        run_scenario(
            client,
            headers,
            "EARLY_PIVOT",
            ["new", "Hi", "Meera", "Wedding", "ok", "let's discuss on call"],
        )
        run_scenario(client, headers, "UNSUPPORTED", ["new", "Hi", "Kiran", "Cocktails party"])
        run_scenario(client, headers, "RESET", ["new", "Hi", "RESET"])

        # Correct step order including guest count (rules State 4)
        legacy = run_scenario(
            client,
            headers,
            "FULL_CALLBACK_STEPS",
            [
                "new",
                "Hi",
                "Test User",
                "Wedding",
                "ok",
                "15 June 2026",
                "150 guests",
                "Whitefield",
                "tomorrow 4pm",
            ],
        )
        if legacy and legacy[-1].get("enquiry_saved"):
            ok("FULL_CALLBACK_STEPS enquiry_saved")
        else:
            bad("FULL_CALLBACK_STEPS enquiry_saved", "flow did not complete")
        if legacy:
            replies = " || ".join((t.get("reply") or "") for t in legacy)
            if "—" not in replies and "–" not in replies:
                ok("FULL_CALLBACK_STEPS no em-dash across turns")
            else:
                bad("FULL_CALLBACK_STEPS em-dash found")
            fields = legacy[-1].get("fields") or {}
            if fields.get("customer_name") == "Test User" and fields.get("guest_count") == 150:
                ok("FULL_CALLBACK_STEPS slots retained")
            else:
                bad("FULL_CALLBACK_STEPS slots", str(fields))

    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    if ISSUES:
        print("\nIssues:")
        for issue in ISSUES:
            print(issue)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
