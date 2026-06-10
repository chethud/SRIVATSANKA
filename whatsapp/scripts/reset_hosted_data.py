#!/usr/bin/env python3
"""Log in and wipe all data on the hosted API (Render)."""

import argparse
import os
import sys

import httpx

DEFAULT_BASE = "https://srivatsanka.onrender.com"


def main() -> int:
    parser = argparse.ArgumentParser(description="Clear all dashboard data on hosted SRIVATSANKA API")
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--username", default=os.environ.get("DASHBOARD_USERNAME", "Admin"))
    parser.add_argument("--password", default=os.environ.get("DASHBOARD_PASSWORD", "Admin@123"))
    parser.add_argument("--dev-token", default=os.environ.get("DEV_SEED_TOKEN", ""))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    headers: dict[str, str] = {}
    if args.dev_token.strip():
        headers["X-Dev-Seed-Token"] = args.dev_token.strip()

    with httpx.Client(timeout=120.0) as client:
        login = client.post(
            f"{base}/api/auth/login",
            json={"username": args.username, "password": args.password},
        )
        if login.status_code != 200:
            print(f"Login failed ({login.status_code}): {login.text}", file=sys.stderr)
            return 1
        token = login.json().get("access_token")
        if not token:
            print("Login response missing access_token", file=sys.stderr)
            return 1

        auth = {**headers, "Authorization": f"Bearer {token}"}
        reset = client.post(
            f"{base}/dev/reset",
            headers=auth,
            json={"confirm": "DELETE_ALL"},
        )
        if reset.status_code == 404:
            print(
                "Reset endpoint not found — deploy latest main to Render first, then run this script again.",
                file=sys.stderr,
            )
            return 1
        if reset.status_code != 200:
            print(f"Reset failed ({reset.status_code}): {reset.text}", file=sys.stderr)
            return 1

        print("Hosted data cleared:", reset.json())

        stats = client.get(f"{base}/api/stats", headers=auth)
        if stats.status_code == 200:
            print("Stats after reset:", stats.json())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
