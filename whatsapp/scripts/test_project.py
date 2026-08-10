"""Full project smoke tests — run: python scripts/test_project.py"""
from __future__ import annotations

import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import os
os.environ["TESTING"] = "true"

ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT.parent / "website"
sys.path.insert(0, str(ROOT))

from starlette.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.callback_time import parse_callback_time  # noqa: E402

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


def auth_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"username": "Admin", "password": "Admin@123"})
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.text[:200]}")
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_public_routes(client: TestClient) -> None:
    print("\n--- Public routes ---")
    for path, name in (
        ("/", "GET /"),
        ("/api/health", "GET /api/health"),
    ):
        r = client.get(path)
        if r.status_code == 200:
            ok(name)
        else:
            bad(name, str(r.status_code))

    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "x", "hub.challenge": "123"})
    if r.status_code in (200, 403):
        ok("GET /webhook (verify endpoint reachable)")
    else:
        bad("GET /webhook", str(r.status_code))


def test_auth(client: TestClient) -> None:
    print("\n--- Auth ---")
    r = client.get("/api/stats")
    if r.status_code == 401:
        ok("Protected routes require login")
    else:
        bad("Auth gate", f"got {r.status_code}")

    r = client.post("/api/auth/login", json={"username": "wrong", "password": "x"})
    if r.status_code == 401:
        ok("Bad credentials rejected")
    else:
        bad("Bad login", str(r.status_code))

    h = auth_headers(client)
    r = client.get("/api/auth/me", headers=h)
    if r.status_code == 200 and r.json().get("username") == "Admin":
        ok("Login + /api/auth/me")
    else:
        bad("/api/auth/me", r.text[:120])


def test_dashboard_apis(client: TestClient, h: dict[str, str]) -> None:
    print("\n--- Dashboard APIs ---")
    for path in (
        "/api/stats",
        "/api/enquiries",
        "/api/dishes",
        "/api/analytics",
        "/api/workers",
        "/api/vendors",
        "/api/expenses",
        "/api/notifications",
        "/api/whatsapp/status",
    ):
        r = client.get(path, headers=h)
        if r.status_code == 200:
            ok(f"GET {path}")
        else:
            bad(f"GET {path}", str(r.status_code))

    r = client.get("/api/analytics", headers=h)
    if r.status_code == 200:
        data = r.json()
        if "expense_items" in data and "total_expenses" in data:
            ok("Analytics schema")
        else:
            bad("Analytics schema")


def test_enquiry_lifecycle(client: TestClient, h: dict[str, str]) -> None:
    print("\n--- Enquiry lifecycle ---")
    callback_at = datetime.now() + timedelta(days=1)
    callback_at = callback_at.replace(hour=16, minute=0, second=0, microsecond=0)
    r = client.post(
        "/api/enquiries",
        headers=h,
        json={
            "customerName": "Project Test",
            "phoneNumber": f"91{uuid.uuid4().int % 10**10:010d}",
            "eventType": "Wedding",
            "eventDate": (datetime.now() + timedelta(days=30)).isoformat(),
            "eventLocation": "Koramangala",
            "guestCount": 100,
            "preferredCallbackAt": callback_at.isoformat(),
            "notes": "Manual test enquiry",
        },
    )
    if r.status_code != 200:
        bad("POST /api/enquiries", r.text[:200])
        return
    enquiry = r.json()
    ok("POST /api/enquiries (manual create)")

    eid = enquiry["id"]
    r = client.patch(
        f"/api/enquiries/{eid}/status",
        headers=h,
        json={"status": "CONTACTED"},
    )
    if r.status_code == 200 and r.json().get("status") == "CONTACTED":
        ok("PATCH enquiry status -> CONTACTED")
    else:
        bad("PATCH enquiry status", r.text[:120])

    r = client.patch(
        f"/api/enquiries/{eid}/status",
        headers=h,
        json={"status": "CONVERTED"},
    )
    if r.status_code == 200 and r.json().get("status") == "CONVERTED":
        ok("PATCH enquiry status -> CONVERTED (order)")
    else:
        bad("PATCH enquiry status CONVERTED", r.text[:120])
        return

    dishes = client.get("/api/dishes", headers=h).json()
    if not dishes:
        bad("Order dish add", "no dishes in catalog")
        return

    r = client.post(
        f"/api/enquiries/{eid}/dishes",
        headers=h,
        json={"dishId": dishes[0]["id"], "category": "Lunch", "quantity": 50},
    )
    if r.status_code == 200 and r.json().get("dishes"):
        ok("POST order dish on converted enquiry")
    else:
        bad("POST order dish", r.text[:200])


def test_bot_flows(client: TestClient, h: dict[str, str]) -> None:
    print("\n--- WhatsApp bot flows ---")

    def run_flow(phone: str, steps: list[str]) -> dict | None:
        last = None
        for msg in steps:
            r = client.post("/dev/message", headers=h, json={"from_number": phone, "text": msg})
            if r.status_code != 200:
                bad(f"bot message {msg!r}", r.text[:160])
                return None
            last = r.json()
        return last

    phone1 = f"91{uuid.uuid4().int % 10**10:010d}"
    callback = "tomorrow 4pm"
    expected = parse_callback_time(callback)
    last = run_flow(
        phone1,
        ["new", "Hi", "Bot Test A", "yes", "Wedding", "ok", "15 June 2026", "150 guests", "Whitefield", callback],
    )
    if not last:
        return
    if last.get("enquiry_saved"):
        ok("Bot flow completes wedding with callback")
    else:
        bad("Bot flow enquiry_saved (wedding)", str(last.get("is_complete")))

    enqs = client.get("/api/enquiries", headers=h).json()
    match = next((e for e in enqs if e.get("phoneNumber") == phone1), None)
    if not match:
        bad("Bot enquiry in list", phone1)
        return

    saved = datetime.fromisoformat(match["preferredCallbackAt"].replace("Z", "+00:00")).replace(tzinfo=None)
    if abs((saved - expected).total_seconds()) < 2:
        ok(f"Callback parsed: {saved.strftime('%d %b %I:%M %p')}")
    else:
        bad("Callback time", f"saved {saved}, expected {expected}")

    phone2 = f"91{uuid.uuid4().int % 10**10:010d}"
    last2 = run_flow(
        phone2,
        [
            "new",
            "Hi",
            "Bot Test B",
            "yes",
            "House Warming",
            "ok",
            "20 July 2026",
            "50 pax",
            "Jayanagar",
            "today evening",
        ],
    )
    if last2 and last2.get("enquiry_saved"):
        ok("Bot flow completes housewarming")
    elif last2:
        bad("Bot flow housewarming", f"enquiry_saved={last2.get('enquiry_saved')}")
    else:
        bad("Bot flow housewarming", "flow failed")


def test_resources_crud(client: TestClient, h: dict[str, str]) -> None:
    print("\n--- Resources CRUD ---")
    r = client.post(
        "/api/vendors",
        headers=h,
        json={"name": "Test Vendor", "category": "Vegetables", "phoneNumber": "9999999999"},
    )
    if r.status_code == 200:
        vid = r.json()["id"]
        ok("POST /api/vendors")
        dr = client.delete(f"/api/vendors/{vid}", headers=h)
        if dr.status_code == 200:
            ok("DELETE /api/vendors/{id}")
        else:
            bad("DELETE vendor", str(dr.status_code))
    else:
        bad("POST /api/vendors", r.text[:120])

    r = client.post(
        "/api/workers",
        headers=h,
        json={"name": "Test Worker", "role": "Helper", "phoneNumber": "8888888888", "dailyWage": 500},
    )
    if r.status_code == 200:
        wid = r.json()["id"]
        ok("POST /api/workers")
        dr = client.delete(f"/api/workers/{wid}", headers=h)
        if dr.status_code == 200:
            ok("DELETE /api/workers/{id}")
        else:
            bad("DELETE worker", str(dr.status_code))
    else:
        bad("POST /api/workers", r.text[:120])

    r = client.post(
        "/api/expenses",
        headers=h,
        json={
            "description": "Test expense",
            "amount": 250,
            "expenseDate": datetime.now().isoformat(),
            "category": "misc",
        },
    )
    if r.status_code == 200:
        eid = r.json()["id"]
        ok("POST /api/expenses")
        dr = client.delete(f"/api/expenses/{eid}", headers=h)
        if dr.status_code == 200:
            ok("DELETE /api/expenses/{id}")
        else:
            bad("DELETE expense", str(dr.status_code))
    else:
        bad("POST /api/expenses", r.text[:120])


def test_ai_assistant(client: TestClient, h: dict[str, str]) -> None:
    print("\n--- AI assistant ---")
    r = client.post(
        "/api/ai-assistant",
        headers=h,
        json={"query": "How many enquiries do we have?"},
    )
    if r.status_code == 200 and "reply" in r.json():
        ok("POST /api/ai-assistant")
    else:
        bad("POST /api/ai-assistant", str(r.status_code))


def test_frontend_build() -> None:
    print("\n--- Frontend build (website/) ---")
    if not WEBSITE.exists():
        bad("website folder", "not found")
        return
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    try:
        result = subprocess.run(
            [npm, "run", "build"],
            cwd=WEBSITE,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except FileNotFoundError:
        bad("npm run build", "npm not found")
        return
    except subprocess.TimeoutExpired:
        bad("npm run build", "timed out after 180s")
        return

    if result.returncode == 0:
        ok("npm run build (TypeScript + Vite)")
    else:
        bad("npm run build", (result.stderr or result.stdout)[-400:])


def main() -> int:
    print("=== Kannans full project tests ===")
    with TestClient(app) as client:
        test_public_routes(client)
        test_auth(client)
        try:
            h = auth_headers(client)
        except RuntimeError as exc:
            print(f"\nAborting — {exc}")
            return 1
        test_dashboard_apis(client, h)
        test_enquiry_lifecycle(client, h)
        test_bot_flows(client, h)
        test_resources_crud(client, h)
        test_ai_assistant(client, h)

    test_frontend_build()

    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
