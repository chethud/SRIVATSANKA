#!/usr/bin/env python3
"""Seed 4 Excel-reference orders on the hosted API (no Supabase login required).

Usage:
  python scripts/seed_excel_reference_orders.py
  python scripts/seed_excel_reference_orders.py --base-url https://srivatsanka.onrender.com
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

DEFAULT_BASE = "https://srivatsanka.onrender.com"


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Excel-reference converted orders via /dev/seed-excel-refs")
    parser.add_argument("--base-url", default=os.environ.get("API_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--dev-token", default=os.environ.get("DEV_SEED_TOKEN", ""))
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    headers: dict[str, str] = {}
    if args.dev_token.strip():
        headers["X-Dev-Seed-Token"] = args.dev_token.strip()

    with httpx.Client(timeout=180.0) as client:
        # Wake cold start
        try:
            client.get(f"{base}/health", timeout=60.0)
        except Exception:
            pass

        res = client.post(f"{base}/dev/seed-excel-refs", headers=headers)
        if res.status_code == 404:
            print(
                "Endpoint not found — deploy latest main to Render, then run again.",
                file=sys.stderr,
            )
            return 1
        if res.status_code != 200:
            print(f"Seed failed ({res.status_code}): {res.text}", file=sys.stderr)
            return 1

        data = res.json()
        print("Excel-reference orders seeded:")
        print(f"  removed: {data.get('removed')}")
        print(f"  created: {data.get('created')}")
        for order in data.get("orders") or []:
            print(f"  - {order.get('customerName')} ({order.get('id')}) ← {order.get('ref')}")
        print("\nOpen Orders on the dashboard → open each “(Excel Ref)” order → Download Excel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
