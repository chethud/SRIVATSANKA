"""Normalize Bengaluru area names from WhatsApp replies (typos / casing)."""

from __future__ import annotations

import re

AREA_ALIASES: dict[str, str] = {
    "hsr": "HSR Layout",
    "hsr layout": "HSR Layout",
    "hsr laytout": "HSR Layout",
    "hsr lay out": "HSR Layout",
    "koramangala": "Koramangala",
    "koramangla": "Koramangala",
    "indiranagar": "Indiranagar",
    "indira nagar": "Indiranagar",
    "whitefield": "Whitefield",
    "whitfield": "Whitefield",
    "jayanagar": "Jayanagar",
    "jaya nagar": "Jayanagar",
    "jp nagar": "JP Nagar",
    "jpnagar": "JP Nagar",
    "btm": "BTM Layout",
    "btm layout": "BTM Layout",
    "marathahalli": "Marathahalli",
    "marathalli": "Marathahalli",
    "electronic city": "Electronic City",
    "hebbal": "Hebbal",
    "yelahanka": "Yelahanka",
    "banashankari": "Banashankari",
    "rajajinagar": "Rajajinagar",
    "malleshwaram": "Malleshwaram",
    "malleswaram": "Malleshwaram",
}


def normalize_location(text: str) -> str:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return raw
    key = raw.lower()
    if key in AREA_ALIASES:
        return AREA_ALIASES[key]
    for alias, canonical in AREA_ALIASES.items():
        if alias in key or key in alias:
            return canonical
    return raw.title()
