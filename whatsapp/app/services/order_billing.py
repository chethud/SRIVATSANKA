"""Order billing totals from Excel-style notes JSON (menu columns + extras)."""

from __future__ import annotations

import json
import re
from typing import Any

from app.data.meal_sessions import PREFERENCE_SESSION_LABELS

PREFERENCE_CATEGORIES = PREFERENCE_SESSION_LABELS

_AUTHORITATIVE_TOTAL_EXTRA = re.compile(
    r"\b(grand\s*total|overall\s*total|total\s*amount|total\s*bill|contract\s*total|final\s*total|package\s*total)\b",
    re.IGNORECASE,
)


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


def _menu_items_only(dish_items: list[Any]) -> list[Any]:
    return [
        d
        for d in dish_items
        if str(getattr(d, "category", "") or "") not in PREFERENCE_CATEGORIES
    ]


def _is_authoritative_total_extra(row: dict[str, Any]) -> bool:
    title = str(row.get("title") or "").strip()
    if not title:
        return False
    if _AUTHORITATIVE_TOTAL_EXTRA.search(title):
        return True
    if title.lower() == "total":
        return True
    desc = str(row.get("description") or "").strip()
    return bool(desc and _AUTHORITATIVE_TOTAL_EXTRA.search(desc))


def _is_overall_total_extra(row: dict[str, Any]) -> bool:
    if row.get("overallTotal") is True:
        return True
    if _is_authoritative_total_extra(row):
        return True
    title = str(row.get("title") or "").strip()
    return bool(re.search(r"\bgrand\s*total\b", title, re.IGNORECASE))


def _overall_total_from_extras(data: dict[str, Any]) -> float | None:
    if not data.get("extrasEnabled"):
        return None
    extras = data.get("extraItems") or []
    if not isinstance(extras, list):
        return None
    amounts: list[float] = []
    for row in extras:
        if not isinstance(row, dict) or row.get("enabled") is not True:
            continue
        if not _is_overall_total_extra(row):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        amt = _safe_float(row.get("amount"))
        if amt is not None and amt > 0:
            amounts.append(amt)
    if not amounts:
        return None
    return amounts[-1]


def _effective_dish_column_map(
    columns: list[dict[str, Any]],
    items: list[Any],
    dish_columns_saved: dict[str, str],
) -> dict[str, str]:
    out = dict(dish_columns_saved)
    sorted_cols = sorted(
        columns,
        key=lambda c: (
            str(c.get("date") or ""),
            str(c.get("timeFrom") or ""),
            str(c.get("baseSession") or ""),
            str(c.get("sessionLabel") or ""),
        ),
    )
    for dish in items:
        did = str(getattr(dish, "id", ""))
        if not did or did in out:
            continue
        cat = str(getattr(dish, "category", "") or "")
        name = str(getattr(dish, "dishName", "") or "")
        for col in sorted_cols:
            base = str(col.get("baseSession") or "")
            label = str(col.get("sessionLabel") or "")
            if cat in (base, label) or name == label:
                out[did] = str(col.get("id") or "")
                break
    return out


def _dishes_for_column(
    column: dict[str, Any],
    items: list[Any],
    dish_columns: dict[str, str],
    all_columns: list[dict[str, Any]],
) -> list[Any]:
    col_id = str(column.get("id") or "")
    if all_columns:
        effective = _effective_dish_column_map(all_columns, items, dish_columns)
        if effective:
            return [d for d in items if effective.get(str(getattr(d, "id", ""))) == col_id]

    base = str(column.get("baseSession") or "")
    label = str(column.get("sessionLabel") or "")
    return [
        d
        for d in items
        if str(getattr(d, "category", "") or "") in (base, label)
    ]


def _sum_billable_extra_amounts(data: dict[str, Any]) -> float:
    if not data.get("extrasEnabled"):
        return 0.0
    total = 0.0
    extras = data.get("extraItems") or []
    if not isinstance(extras, list):
        return 0.0
    for row in extras:
        if not isinstance(row, dict):
            continue
        if row.get("enabled") is not True:
            continue
        if _is_overall_total_extra(row):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        amt = _safe_float(row.get("amount"))
        if amt is not None and amt > 0:
            total += amt
    return total


def billing_total_from_notes(notes: str | None, dish_items: list[Any] | None = None) -> float | None:
    """Sum billable session column amounts + enabled extras from enquiry notes JSON."""
    if not notes or not notes.strip():
        return None
    try:
        data = json.loads(notes)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    overall = _overall_total_from_extras(data)
    if overall is not None:
        return overall

    override = _safe_float(data.get("bookedTotalOverride"))
    if override is not None and override > 0:
        return override

    items = _menu_items_only(list(dish_items or []))
    dish_columns_raw = data.get("dishColumns") or {}
    dish_columns = (
        {str(k): str(v) for k, v in dish_columns_raw.items()}
        if isinstance(dish_columns_raw, dict)
        else {}
    )

    columns_raw = data.get("menuColumns") or []
    columns = [c for c in columns_raw if isinstance(c, dict)] if isinstance(columns_raw, list) else []

    seen: set[str] = set()
    total = 0.0
    found = False

    for col in columns:
        amt = _safe_float(col.get("amount"))
        if amt is None:
            continue
        col_dishes = _dishes_for_column(col, items, dish_columns, columns)
        if col_dishes:
            dish_ids = sorted(str(getattr(d, "id", "")) for d in col_dishes)
            signature = f"{','.join(dish_ids)}|{int(round(amt))}"
        else:
            col_id = str(col.get("id") or "")
            if not col_id:
                continue
            signature = f"col:{col_id}|{int(round(amt))}"
        if signature in seen:
            continue
        seen.add(signature)
        total += amt
        found = True

    extras_sum = _sum_billable_extra_amounts(data)
    if extras_sum > 0:
        total += extras_sum
        found = True

    return total if found else None
