"""Developer workflow smoke tests — run: python scripts/test_workflows.py"""
from __future__ import annotations

import sys
from pathlib import Path

# whatsapp/ as cwd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from starlette.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

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


def main() -> int:
    print("=== Kannans API workflow tests ===\n")
    with TestClient(app) as c:
        # Public
        r = c.get("/api/health")
        if r.status_code == 200:
            ok("GET /api/health (public)")
        else:
            bad("GET /api/health", str(r.status_code))

        r = c.get("/api/stats")
        if r.status_code == 401:
            ok("GET /api/stats blocked without auth")
        else:
            bad("GET /api/stats without auth", f"got {r.status_code}")

        # Login
        r = c.post("/api/auth/login", json={"username": "wrong", "password": "x"})
        if r.status_code == 401:
            ok("POST /api/auth/login rejects bad credentials")
        else:
            bad("bad login", str(r.status_code))

        r = c.post("/api/auth/login", json={"username": "Admin", "password": "Admin@123"})
        if r.status_code != 200 or "access_token" not in r.json():
            bad("POST /api/auth/login", r.text[:200])
            print("\nAborting — cannot continue without token")
            return 1
        ok("POST /api/auth/login (Admin)")
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        r = c.get("/api/auth/me", headers=h)
        if r.status_code == 200 and r.json().get("username") == "Admin":
            ok("GET /api/auth/me")
        else:
            bad("GET /api/auth/me", r.text)

        # Core dashboard APIs
        for path in (
            "/api/stats",
            "/api/enquiries",
            "/api/dishes",
            "/api/analytics",
            "/api/workers",
            "/api/vendors",
            "/api/notifications",
        ):
            r = c.get(path, headers=h)
            if r.status_code == 200:
                ok(f"GET {path}")
            else:
                bad(f"GET {path}", str(r.status_code))

        # Analytics expense_items shape
        r = c.get("/api/analytics", headers=h)
        if r.status_code == 200:
            data = r.json()
            if "expense_items" in data and "total_expenses" in data:
                ok("Analytics has expense_items + total_expenses")
            else:
                bad("Analytics schema")
        else:
            bad("GET /api/analytics", str(r.status_code))

        # Invoice confirm workflow (pending file)
        import uuid

        from app.routers.orders import UPLOAD_DIR

        pid = uuid.uuid4().hex
        pending = UPLOAD_DIR / "pending"
        pending.mkdir(parents=True, exist_ok=True)
        src = pending / f"{pid}.pdf"
        src.write_bytes(b"%PDF-1.4 test")
        r = c.post(
            "/api/invoices/confirm",
            headers={**h, "Content-Type": "application/json"},
            json={
                "pendingId": pid,
                "description": "Test Gas Bill",
                "expenseDate": "2026-06-02",
                "amount": 1500,
                "purpose": "gas",
            },
        )
        if r.status_code == 200 and r.json().get("amount") == 1500:
            ok("POST /api/invoices/confirm (standalone expense)")
        else:
            bad("POST /api/invoices/confirm", r.text[:300])

        # Dev seed (optional)
        r = c.post("/dev/seed", headers=h)
        if r.status_code == 200 and "enquiries" in r.json():
            ok("POST /dev/seed")
        else:
            bad("POST /dev/seed", str(r.status_code))

        # AI assistant
        r = c.post(
            "/api/ai-assistant",
            headers={**h, "Content-Type": "application/json"},
            json={"query": "How many enquiries?"},
        )
        if r.status_code == 200 and "reply" in r.json():
            ok("POST /api/ai-assistant")
        else:
            bad("POST /api/ai-assistant", str(r.status_code))

    print(f"\n=== Results: {PASS} passed, {FAIL} failed ===")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
