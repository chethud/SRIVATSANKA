from __future__ import annotations

import re
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import uuid4

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.seed_excel_reference_orders import excel_reference_order_defs
from app.models import Enquiry, EnquiryDish, EnquiryStatus
from app.schemas import OrderExcelImportIn


DEFAULT_PHONE = "910000000000"
DEFAULT_EVENT_TYPE = "Imported Event"
DEFAULT_LOCATION = "Location to be updated"
DEFAULT_NAME = "Imported Excel Order"
DEFAULT_SESSION_TIMES: dict[str, tuple[str | None, str | None]] = {
    "Breakfast": ("08:00", "11:00"),
    "Lunch": ("12:30", "15:00"),
    "Snacks": ("16:00", "18:00"),
    "Dinner": ("19:00", "21:30"),
    "Coffee": ("06:00", "07:00"),
    "Tea": ("10:00", "18:00"),
    "Juice": ("10:30", "11:30"),
    "Dessert": (None, None),
}
def _clean(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", text)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "item"


def _parse_date_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    text = _clean(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            continue
    return None


def _parse_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean(value).replace(",", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _looks_like_amount(value: str) -> bool:
    if not value:
        return False
    if re.fullmatch(r"[\d,]+(?:\.\d+)?", value):
        return True
    return False


def _looks_like_session_detail(value: str) -> bool:
    lowered = value.lower()
    if "pax" in lowered:
        return True
    if re.search(r"\d+\s*[-:]\s*\d+", lowered):
        return True
    if re.search(r"\d\s*am\b", lowered) or re.search(r"\d\s*pm\b", lowered):
        return True
    return False


def _looks_like_session_label(value: str) -> bool:
    lowered = value.lower()
    if any(hint in lowered for hint in (
        "breakfast", "lunch", "dinner", "snacks", "buffet", "packed",
        "plantain", "main course", "chaats", "dose counter", "cut fruits",
        "ice cream",
    )):
        return True
    if lowered in {"coffee", "tea", "juice", "dessert"}:
        return True
    if "counter" in lowered:
        return True
    if lowered.startswith(("coffee ", "tea ", "juice ")):
        return True
    return False


def _extract_pax_and_times(value: str, base_session: str) -> tuple[int | None, str | None, str | None]:
    text = _clean(value)
    pax = None
    time_from = None
    time_to = None
    pax_match = re.search(r"(\d+)\s*pax", text, re.I)
    if pax_match:
        pax = int(pax_match.group(1))
    else:
        number_only = re.fullmatch(r"(\d+)", text)
        if number_only:
            pax = int(number_only.group(1))

    def to_24h(hour: int, minute: int, suffix: str | None) -> str:
        if suffix:
            suffix = suffix.lower()
            if suffix == "pm" and hour != 12:
                hour += 12
            if suffix == "am" and hour == 12:
                hour = 0
        return f"{hour:02d}:{minute:02d}"

    range_match = re.search(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        text,
        re.I,
    )
    if range_match:
        h1 = int(range_match.group(1))
        m1 = int(range_match.group(2) or 0)
        s1 = range_match.group(3)
        h2 = int(range_match.group(4))
        m2 = int(range_match.group(5) or 0)
        s2 = range_match.group(6) or s1
        time_from = to_24h(h1, m1, s1)
        time_to = to_24h(h2, m2, s2)
    elif pax is not None:
        default_times = DEFAULT_SESSION_TIMES.get(base_session)
        if default_times:
            time_from, time_to = default_times

    return pax, time_from, time_to


def _classify_base_session(label: str) -> str:
    lowered = label.lower()
    mapping = [
        ("coffee", "Coffee"),
        ("tea", "Tea"),
        ("juice", "Juice"),
        ("breakfast", "Breakfast"),
        ("lunch", "Lunch"),
        ("snacks", "Snacks"),
        ("roll", "Snacks"),
        ("dinner", "Dinner"),
        ("dessert", "Dessert"),
    ]
    for needle, session in mapping:
        if needle in lowered:
            return session
    return "Lunch"


def _guess_event_type(title: str, location: str) -> str:
    text = f"{title} {location}".lower()
    if "wedding" in text:
        return "Wedding"
    if "corporate" in text or "private limited" in text:
        return "Corporate Event"
    if "reception" in text:
        return "Reception"
    return DEFAULT_EVENT_TYPE


def _guess_phone() -> str:
    return DEFAULT_PHONE


def _guess_callback(event_date: datetime) -> datetime:
    return event_date.replace(hour=10, minute=0, second=0, microsecond=0) - timedelta(days=1)


def _detect_layout(workbook) -> str:
    for ws in workbook.worksheets:
        for row in ws.iter_rows(min_row=1, max_row=20, values_only=True):
            values = [_clean(v) for v in row]
            lowered = [v.lower() for v in values if v]
            if any(v == "s. no." for v in lowered) and any("part description" in v for v in lowered):
                return "sales_invoice"
    return "menu_grid"


def _normalized_reference_order(match: dict[str, Any], filename: str) -> dict[str, Any]:
    dishes = [
        {
            "tempId": f"dish_{index+1}",
            "dishName": name,
            "category": category,
            "sessionColumnId": column_id,
            "notes": None,
        }
        for index, (name, category, column_id) in enumerate(match["dishes"])
    ]
    return {
        "layout": "reference_match",
        "warnings": ["Matched a known Kannan reference workbook and used the full structured order mapping."],
        "order": {
            "customerName": match["customerName"],
            "phoneNumber": match["phoneNumber"],
            "eventType": match["eventType"],
            "eventDate": match["eventDate"],
            "eventLocation": match["eventLocation"],
            "guestCount": match["guestCount"],
            "preferredCallbackAt": match["preferredCallbackAt"],
            "dietary": match.get("dietary") or [],
            "scheduleDateFrom": match["scheduleDateFrom"],
            "scheduleDateTo": match["scheduleDateTo"],
            "menuColumns": match["menuColumns"],
            "dishes": dishes,
            "extraItems": match.get("extras") or [],
            "venueMapLink": match.get("venueMapLink"),
            "regionalStylesByDate": match.get("regionalStylesByDate") or {},
            "customSessions": [],
            "sourceFileName": filename,
            "sourceLayout": "reference_match",
        },
    }


def _match_reference_workbook(workbook, filename: str) -> dict[str, Any] | None:
    text_parts = [filename.lower()]
    for ws in workbook.worksheets[:2]:
        for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
            for value in row[:4]:
                cleaned = _clean(value)
                if cleaned:
                    text_parts.append(cleaned.lower())
    haystack = " ".join(text_parts)
    for order in excel_reference_order_defs():
        tokens = [
            order["customerName"].lower(),
            order["ref"].lower(),
            order["eventLocation"].lower(),
        ]
        if any(token and token in haystack for token in tokens):
            return order
    filename_lower = filename.lower()
    alias_map = {
        "nithin": "Nithin Wedding PG Menu",
        "muralidharan": "Muralidharan Daughter Wedding Menu",
        "casagrand": "Casagrand Vivacity Sales Invoice",
        "vivacity": "Casagrand Vivacity Sales Invoice",
        "ra hospital": "RA Hospitalities Sales Invoice",
        "ra hospitalies": "RA Hospitalities Sales Invoice",
    }
    matched_ref = next((ref for key, ref in alias_map.items() if key in filename_lower), None)
    if matched_ref:
        for order in excel_reference_order_defs():
            if order["ref"] == matched_ref:
                return order
    return None


def _find_date_row(ws) -> tuple[int, list[tuple[int, datetime]]]:
    best_row = 1
    best_dates: list[tuple[int, datetime]] = []
    for row_idx in range(1, min(ws.max_row, 12) + 1):
        row_dates: list[tuple[int, datetime]] = []
        for col_idx in range(1, ws.max_column + 1):
            parsed = _parse_date_value(ws.cell(row_idx, col_idx).value)
            if parsed:
                row_dates.append((col_idx, parsed))
        if len(row_dates) > len(best_dates):
            best_row = row_idx
            best_dates = row_dates
    return best_row, best_dates


def _is_probable_block_start(current: str, next_values: list[str]) -> bool:
    if not current or _looks_like_amount(current):
        return False
    lowered = current.lower()
    if lowered.startswith("client :") or lowered.startswith("billing address"):
        return False
    if "allergy" in lowered:
        return False
    if not _looks_like_session_label(current):
        return False
    following = [v for v in next_values if v]
    if not following:
        return False
    first_following = following[0]
    if not (_looks_like_session_detail(first_following) or _looks_like_amount(first_following)):
        return False
    has_detail = any(_looks_like_session_detail(v) for v in following)
    has_amount = any(_looks_like_amount(v) for v in following)
    return has_detail or has_amount


def _is_skip_row(value: str) -> bool:
    """Rows that are neither session headers nor dishes — metadata we consume inline."""
    if not value:
        return True
    lowered = value.lower()
    if lowered.startswith(("sub total", "grand total", "payment", "advance", "account")):
        return True
    return False


def _is_extras_stop_label(value: str) -> bool:
    lowered = value.lower().strip()
    return (
        lowered in {"total", "grand total"}
        or lowered.startswith("grand total")
        or lowered.startswith("payment")
        or lowered.startswith("account detail")
    )


def _looks_like_extra_amount(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean(value)
    if not text:
        return None
    if text.upper() in {"NIL", "N/A", "NA", "COMPLIMENTORY", "COMPLIMENTARY"}:
        return None
    if not _looks_like_amount(text):
        return None
    return _parse_number(text)


def _parse_extras_section(ws) -> list[dict[str, Any]]:
    """Read Sweet Box / Thambula / Garlands / Logistics rows after Sub Total."""
    start_row = None
    for row_idx in range(1, ws.max_row + 1):
        label = _clean(ws.cell(row_idx, 1).value).lower()
        if label.startswith("sub total"):
            start_row = row_idx + 1
            break
    if start_row is None:
        return []

    extras: list[dict[str, Any]] = []
    amount_col = min(ws.max_column, 8)
    for row_idx in range(start_row, ws.max_row + 1):
        title = _clean(ws.cell(row_idx, 1).value)
        if not title:
            continue
        if _is_extras_stop_label(title):
            break

        description = _clean(ws.cell(row_idx, 2).value)
        quantity_raw = _clean(ws.cell(row_idx, 3).value)
        quantity = ""
        amount = None
        for col_idx in range(amount_col, 1, -1):
            parsed_amount = _looks_like_extra_amount(ws.cell(row_idx, col_idx).value)
            if parsed_amount is not None:
                amount = parsed_amount
                break

        # Prefer short C3 values as quantity; long notes go into description.
        if quantity_raw:
            if len(quantity_raw) <= 40 or any(
                token in quantity_raw.lower() for token in ("box", "set", "pkt", "pax", "pc", "kg", "nil")
            ):
                quantity = quantity_raw
            else:
                description = f"{description}\n{quantity_raw}".strip() if description else quantity_raw

        if not quantity:
            for col_idx in range(3, amount_col + 1):
                candidate = _clean(ws.cell(row_idx, col_idx).value)
                if not candidate or _looks_like_amount(candidate):
                    continue
                if candidate.upper() in {"NIL", "N/A", "COMPLIMENTORY", "COMPLIMENTARY"}:
                    quantity = candidate
                    break
                if len(candidate) <= 40:
                    quantity = candidate
                    break

        # Skip payment/account rows that may appear without clean stop markers.
        lowered = title.lower()
        if lowered.startswith(("advance", "payment", "account")):
            continue

        extras.append(
            {
                "id": f"extra_{_slug(title)}_{len(extras)+1}",
                "title": title.replace("\n", " ").strip(),
                "description": description,
                "quantity": quantity,
                "amount": amount,
                "enabled": True,
                "isCustom": True,
            }
        )
    return extras


def _parse_column_cells(ws, col_idx: int, col_date: datetime, start_row: int, end_row: int) -> dict[str, Any]:
    """Walk one column top-to-bottom, collecting sessions and dishes."""
    menu_columns: list[dict[str, Any]] = []
    dishes: list[dict[str, Any]] = []
    dietary: list[str] = []

    current_column: dict[str, Any] | None = None

    def _start_session(label: str, row_idx: int) -> None:
        nonlocal current_column
        base_session = _classify_base_session(label)
        pax = None
        time_from = None
        time_to = None
        amount = None

        # Consume up to 3 following metadata rows (pax/time detail, amount)
        consumed = 0
        for offset in range(1, 4):
            if row_idx + offset > end_row:
                break
            candidate = _clean(ws.cell(row_idx + offset, col_idx).value)
            if not candidate:
                continue
            if _looks_like_session_detail(candidate) and pax is None and time_from is None:
                pax, time_from, time_to = _extract_pax_and_times(candidate, base_session)
                consumed = offset
                continue
            if _looks_like_amount(candidate) and amount is None:
                amount = _parse_number(candidate)
                consumed = offset
                continue
            break  # stop at first cell that is neither detail nor amount

        # Also check if pax/time is embedded in the label itself (e.g. "Coffee @ 6.30am Sugarless 100 Pax")
        if pax is None and time_from is None and _looks_like_session_detail(label):
            pax, time_from, time_to = _extract_pax_and_times(label, base_session)

        if time_from is None and time_to is None:
            _, time_from, time_to = _extract_pax_and_times("", base_session)

        col_id = f"{col_date.strftime('%Y%m%d')}_{_slug(label)}_{len(menu_columns)+1}"
        current_column = {
            "id": col_id,
            "date": col_date.strftime("%Y-%m-%d"),
            "sessionLabel": label,
            "baseSession": base_session,
            "pax": pax,
            "timeFrom": time_from,
            "timeTo": time_to,
            "amount": amount,
            "_consumed_until": row_idx + consumed,
        }
        menu_columns.append(current_column)

    row = start_row
    while row <= end_row:
        value = _clean(ws.cell(row, col_idx).value)
        if not value:
            row += 1
            continue

        lowered = value.lower()

        # Stop markers
        if lowered.startswith(("sub total", "grand total")):
            break

        # Skip non-food metadata
        if _is_skip_row(value):
            row += 1
            continue

        # Dietary / allergy notes
        if "allergy" in lowered or lowered.startswith("note:"):
            dietary.append(value)
            row += 1
            continue

        # Check if this is a session header
        next_vals = [_clean(ws.cell(row + off, col_idx).value) for off in range(1, 4) if row + off <= end_row]
        if _is_probable_block_start(value, next_vals):
            _start_session(value, row)
            row = current_column["_consumed_until"] + 1  # type: ignore[index]
            continue

        # It's a dish row (or an amount/detail that slipped through)
        if _looks_like_amount(value) or _looks_like_session_detail(value):
            row += 1
            continue

        # It's a dish — attach to current session column
        if current_column is not None:
            dishes.append({
                "tempId": f"dish_{len(dishes)+1}",
                "dishName": value,
                "category": current_column["baseSession"],
                "sessionColumnId": current_column["id"],
                "notes": None,
            })
        row += 1

    # Clean internal tracking keys
    for col in menu_columns:
        col.pop("_consumed_until", None)

    return {"menuColumns": menu_columns, "dishes": dishes, "dietary": dietary}


def _parse_menu_sheet(ws) -> dict[str, Any]:
    title = _clean(ws.cell(1, 1).value or ws.cell(1, 2).value)
    if title.lower().startswith("client :"):
        title = title.split(":", 1)[1].strip()
    location = _clean(ws.cell(2, 1).value or ws.cell(2, 2).value) or DEFAULT_LOCATION
    date_row_idx, date_cells = _find_date_row(ws)
    if not date_cells:
        return {
            "title": title,
            "location": location,
            "menuColumns": [],
            "dishes": [],
            "dietary": [],
            "extraItems": [],
        }

    # Find the end row (Sub Total or max_row)
    end_row = ws.max_row
    for r in range(date_row_idx + 1, ws.max_row + 1):
        v = _clean(ws.cell(r, 1).value).lower()
        if v.startswith("sub total") or v.startswith("grand total"):
            end_row = r - 1
            break

    all_columns: list[dict[str, Any]] = []
    all_dishes: list[dict[str, Any]] = []
    all_dietary: list[str] = []

    for col_idx, col_date in date_cells:
        parsed = _parse_column_cells(ws, col_idx, col_date, date_row_idx + 1, end_row)
        all_columns.extend(parsed["menuColumns"])
        all_dishes.extend(parsed["dishes"])
        all_dietary.extend(parsed["dietary"])

    return {
        "title": title,
        "location": location,
        "menuColumns": all_columns,
        "dishes": all_dishes,
        "dietary": list(dict.fromkeys(all_dietary)),
        "extraItems": _parse_extras_section(ws),
    }


def _parse_menu_grid(workbook, filename: str) -> dict[str, Any]:
    warnings: list[str] = []
    preferred_ws = workbook["Menu"] if "Menu" in workbook.sheetnames else workbook.worksheets[0]
    primary = _parse_menu_sheet(preferred_ws)
    if not primary["menuColumns"]:
        fallback = max((_parse_menu_sheet(ws) for ws in workbook.worksheets), key=lambda item: len(item["menuColumns"]))
        primary = fallback

    menu_columns = primary["menuColumns"]
    dishes = primary["dishes"]
    dietary = primary["dietary"]
    extra_items = primary.get("extraItems") or []
    title = primary["title"] or DEFAULT_NAME
    location = primary["location"] or DEFAULT_LOCATION

    if not menu_columns:
        raise ValueError("Could not detect order dates or session blocks from this Excel layout")

    if not menu_columns:
        raise ValueError("Could not detect menu/session blocks from this Excel layout")

    dates = sorted({c["date"] for c in menu_columns})
    event_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    guest_count = max((c.get("pax") or 0) for c in menu_columns)
    custom_sessions = sorted({c["baseSession"] for c in menu_columns if c["baseSession"] not in DEFAULT_SESSION_TIMES})

    return {
        "layout": "menu_grid",
        "warnings": warnings,
        "order": {
            "customerName": title or DEFAULT_NAME,
            "phoneNumber": _guess_phone(),
            "eventType": _guess_event_type(title, location),
            "eventDate": event_date,
            "eventLocation": location,
            "guestCount": guest_count,
            "preferredCallbackAt": _guess_callback(event_date),
            "dietary": list(dict.fromkeys([note for note in dietary if note])),
            "scheduleDateFrom": dates[0],
            "scheduleDateTo": dates[-1],
            "menuColumns": menu_columns,
            "dishes": dishes,
            "extraItems": extra_items,
            "venueMapLink": None,
            "regionalStylesByDate": {},
            "customSessions": custom_sessions,
            "sourceFileName": filename,
            "sourceLayout": "menu_grid",
        },
    }


def _find_invoice_table_start(ws) -> int | None:
    for row_idx in range(1, min(ws.max_row, 25) + 1):
        row = [_clean(ws.cell(row_idx, col_idx).value).lower() for col_idx in range(1, min(ws.max_column, 12) + 1)]
        if "s. no." in row and any("part description" in cell for cell in row):
            return row_idx
    return None


def _parse_sales_invoice(workbook, filename: str) -> dict[str, Any]:
    ws = workbook[workbook.sheetnames[0]]
    table_row = _find_invoice_table_start(ws)
    if table_row is None:
        raise ValueError("Could not detect the invoice item table in this Excel layout")

    title = DEFAULT_NAME
    for row_idx in range(1, min(ws.max_row, 12) + 1):
        row_values = [_clean(ws.cell(row_idx, col_idx).value) for col_idx in range(1, min(ws.max_column, 4) + 1)]
        if any(v.lower().startswith("billing address") for v in row_values):
            next_value = _clean(ws.cell(row_idx + 1, 1).value)
            if next_value:
                title = next_value
                break
    customer_name = title.split("\n")[0].strip() or DEFAULT_NAME
    location = customer_name
    invoice_date = None
    for row_idx in range(1, min(ws.max_row, 15) + 1):
        for col_idx in range(1, min(ws.max_column, 8) + 1):
            cell = _clean(ws.cell(row_idx, col_idx).value)
            if cell.lower().startswith("date"):
                tail = cell.split(":", 1)[-1].strip()
                invoice_date = _parse_date_value(tail)
                break
        if invoice_date:
            break
    if not invoice_date:
        invoice_date = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

    menu_columns: list[dict[str, Any]] = []
    dishes: list[dict[str, Any]] = []
    extra_items: list[dict[str, Any]] = []
    warnings: list[str] = []

    def _is_invoice_extra(desc: str) -> bool:
        lowered = desc.lower()
        return any(
            key in lowered
            for key in (
                "transport",
                "sweet box",
                "kanti",
                "logistics",
                "cleaning",
            )
        )

    row_idx = table_row + 1
    while row_idx <= ws.max_row:
        number_cell = _clean(ws.cell(row_idx, 1).value)
        desc = _clean(ws.cell(row_idx, 2).value)
        amount = _parse_number(ws.cell(row_idx, 8).value)
        qty = _parse_number(ws.cell(row_idx, 5).value)
        qty_text = _clean(ws.cell(row_idx, 5).value)
        if desc.lower().startswith("sub total") or desc.lower().startswith("cgst") or desc.lower().startswith("sgst"):
            break
        if not desc:
            row_idx += 1
            continue
        if number_cell and not number_cell.isdigit():
            row_idx += 1
            continue

        if _is_invoice_extra(desc):
            extra_items.append(
                {
                    "id": f"extra_{_slug(desc)}_{len(extra_items)+1}",
                    "title": desc,
                    "description": "",
                    "quantity": qty_text if qty_text else (str(int(qty)) if qty is not None else ""),
                    "amount": amount,
                    "enabled": True,
                    "isCustom": True,
                }
            )
            row_idx += 1
            continue

        base_session = _classify_base_session(desc)
        col_id = f"{invoice_date.strftime('%Y%m%d')}_{_slug(desc)}_{len(menu_columns)+1}"
        time_from, time_to = DEFAULT_SESSION_TIMES.get(base_session, (None, None))
        menu_columns.append(
            {
                "id": col_id,
                "date": invoice_date.strftime("%Y-%m-%d"),
                "sessionLabel": desc,
                "baseSession": base_session,
                "pax": int(qty) if qty is not None else None,
                "timeFrom": time_from,
                "timeTo": time_to,
                "amount": amount,
            }
        )
        dishes.append(
            {
                "tempId": f"dish_{len(dishes)+1}",
                "dishName": desc,
                "category": base_session,
                "sessionColumnId": col_id,
                "notes": "Imported from sales invoice line item",
            }
        )
        row_idx += 1

    if not menu_columns and not extra_items:
        raise ValueError("No invoice line items found to build the order")

    guest_count = max((c.get("pax") or 0) for c in menu_columns) if menu_columns else 0
    return {
        "layout": "sales_invoice",
        "warnings": warnings + ["Imported from sales-invoice format. Review customer, venue, and menu details after creation."],
        "order": {
            "customerName": customer_name,
            "phoneNumber": _guess_phone(),
            "eventType": _guess_event_type(customer_name, location),
            "eventDate": invoice_date,
            "eventLocation": location or DEFAULT_LOCATION,
            "guestCount": guest_count,
            "preferredCallbackAt": _guess_callback(invoice_date),
            "dietary": [],
            "scheduleDateFrom": invoice_date.strftime("%Y-%m-%d"),
            "scheduleDateTo": invoice_date.strftime("%Y-%m-%d"),
            "menuColumns": menu_columns,
            "dishes": dishes,
            "extraItems": extra_items,
            "venueMapLink": None,
            "regionalStylesByDate": {},
            "customSessions": [],
            "sourceFileName": filename,
            "sourceLayout": "sales_invoice",
        },
    }


def parse_order_excel_bytes(contents: bytes, filename: str) -> dict[str, Any]:
    workbook = load_workbook(BytesIO(contents), data_only=True)
    layout = _detect_layout(workbook)
    if layout == "sales_invoice":
        return _parse_sales_invoice(workbook, filename)
    return _parse_menu_grid(workbook, filename)


def _serialize_notes(order: dict[str, Any], dish_columns: dict[str, str]) -> str:
    schedules: dict[str, dict[str, str | None]] = {}
    for col in order["menuColumns"]:
        base = col["baseSession"]
        if base not in schedules and (col.get("timeFrom") or col.get("timeTo")):
            schedules[base] = {"timeFrom": col.get("timeFrom"), "timeTo": col.get("timeTo")}
    regional_styles_by_date = order.get("regionalStylesByDate") or {}
    extras = order.get("extraItems") or []
    return __import__("json").dumps(
        {
            "dietary": order.get("dietary") or [],
            "liveCounters": [],
            "addOns": [],
            "scheduleDateFrom": order.get("scheduleDateFrom"),
            "scheduleDateTo": order.get("scheduleDateTo"),
            "mealSchedules": schedules,
            "menuColumns": order["menuColumns"],
            "dishColumns": dish_columns,
            "extrasEnabled": bool(extras),
            "extraItems": extras,
            "regionalStylesByDate": regional_styles_by_date,
            "regionalStyles": list(dict.fromkeys(regional_styles_by_date.values())),
            "regionalStyle": next(iter(regional_styles_by_date.values()), None),
            "venueMapLink": order.get("venueMapLink"),
            "customSessions": order.get("customSessions") or [],
            "assignedWorkerIds": [],
            "dispatchPhase": "planned",
            "itemDispatch": {},
            "_importSource": order.get("sourceLayout"),
            "_importFileName": order.get("sourceFileName"),
        }
    )


async def import_normalized_order(session: AsyncSession, payload: OrderExcelImportIn) -> tuple[Enquiry, list[str]]:
    data = payload.order.model_dump(mode="json")
    warnings = [*[]]

    if payload.mode == "existing":
        result = await session.execute(
            select(Enquiry)
            .options(selectinload(Enquiry.dish_items), selectinload(Enquiry.payments))
            .where(Enquiry.id == payload.existingEnquiryId)
        )
        enquiry = result.scalar_one_or_none()
        if not enquiry:
            raise ValueError("Order not found for replacement")
    else:
        enquiry = Enquiry(
            customerName=DEFAULT_NAME,
            phoneNumber=DEFAULT_PHONE,
            eventType=DEFAULT_EVENT_TYPE,
            eventDate=datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0),
            eventLocation=DEFAULT_LOCATION,
            guestCount=0,
            preferredCallbackAt=datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0),
            status=EnquiryStatus.CONVERTED,
            ownerViewedAt=datetime.utcnow(),
            notes="{}",
        )
        session.add(enquiry)
        await session.flush()

    customer_name = _clean(data.get("customerName")) or DEFAULT_NAME
    phone = _clean(data.get("phoneNumber")) or DEFAULT_PHONE
    event_type = _clean(data.get("eventType")) or DEFAULT_EVENT_TYPE
    location = _clean(data.get("eventLocation")) or DEFAULT_LOCATION
    guest_count = max(0, int(data.get("guestCount") or 0))
    event_date = payload.order.eventDate
    callback_at = payload.order.preferredCallbackAt

    if customer_name == DEFAULT_NAME:
        warnings.append("Customer name was missing in the Excel and has been filled with a placeholder.")
    if phone == DEFAULT_PHONE:
        warnings.append("Phone number was missing in the Excel and has been filled with a placeholder.")
    if location == DEFAULT_LOCATION:
        warnings.append("Event location was missing in the Excel and has been filled with a placeholder.")

    enquiry.customerName = customer_name
    enquiry.phoneNumber = phone
    enquiry.eventType = event_type
    enquiry.eventDate = event_date.replace(tzinfo=None)
    enquiry.eventLocation = location
    enquiry.guestCount = guest_count
    enquiry.preferredCallbackAt = callback_at.replace(tzinfo=None)
    enquiry.status = EnquiryStatus.CONVERTED
    if enquiry.ownerViewedAt is None:
        enquiry.ownerViewedAt = datetime.utcnow()

    for existing_item in list(getattr(enquiry, "dish_items", []) or []):
        await session.delete(existing_item)
    await session.flush()

    enquiry.notes = _serialize_notes(data, {})
    await session.flush()

    dish_columns: dict[str, str] = {}
    for row in payload.order.dishes:
        item = EnquiryDish(
            enquiryId=enquiry.id,
            dishId=None,
            dishName=row.dishName.strip(),
            category=row.category.strip() or _classify_base_session(row.dishName),
            notes=(row.notes or "").strip() or None,
            quantity=1.0,
            quantityUnit="pcs",
            unitPrice=None,
            served=False,
        )
        session.add(item)
        await session.flush()
        dish_columns[item.id] = row.sessionColumnId

    enquiry.notes = _serialize_notes(data, dish_columns)
    await session.commit()
    await session.refresh(enquiry)
    return enquiry, warnings
