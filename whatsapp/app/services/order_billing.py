"""Order billing totals from Excel-style notes JSON (menu columns + extras)."""

from __future__ import annotations

import json
from typing import Any


def _safe_float(value: Any) -> float | None:
    if value is None or value is False:
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if n != n:  # NaN
        return None
    return n


def billing_total_from_notes(notes: str | None) -> float | None:
    """Sum session column amounts + enabled extras from enquiry notes JSON."""
    if not notes or not notes.strip():
        return None
    try:
        data = json.loads(notes)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    total = 0.0
    found = False

    columns = data.get("menuColumns") or []
    if isinstance(columns, list):
        for col in columns:
            if not isinstance(col, dict):
                continue
            amt = _safe_float(col.get("amount"))
            if amt is not None:
                total += amt
                found = True

    extras = data.get("extraItems") or []
    if isinstance(extras, list):
        for row in extras:
            if not isinstance(row, dict):
                continue
            enabled = row.get("enabled")
            if enabled is False:
                continue
            # Treat missing enabled as active if amount/description present (matches UI merge)
            if enabled is not True:
                desc = str(row.get("description") or "").strip()
                qty = str(row.get("quantity") or "").strip()
                amt_probe = _safe_float(row.get("amount"))
                if not desc and not qty and not amt_probe:
                    continue
            amt = _safe_float(row.get("amount"))
            if amt is not None and amt > 0:
                total += amt
                found = True

    return total if found else None
