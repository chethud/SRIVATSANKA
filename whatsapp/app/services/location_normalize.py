"""Normalize Bengaluru area names from WhatsApp replies (typos / casing)."""

from __future__ import annotations

import re

AREA_ALIASES: dict[str, str] = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "banglore": "Bengaluru",
    "benglore": "Bengaluru",
    "bengalore": "Bengaluru",
    "mysuru": "Mysuru",
    "mysore": "Mysuru",
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
    for alias, canonical in sorted(AREA_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", key):
            return canonical
    return raw.title()


def extract_location_entity(text: str) -> str:
    """Pull a clean venue/area name out of conversational replies like 'Yes Hundur'."""
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return raw
    lower = raw.lower()
    if "help" in lower and "venue" in lower:
        city_match = re.search(r"\b(?:in|at|around|near)\s+([A-Za-z][A-Za-z\s.-]{1,40})", raw, re.I)
        if city_match:
            return f"{normalize_location(city_match.group(1).strip())} (Venue Selection Needed)"
        return "Venue Selection Needed"
    if lower in {"no help me", "help me", "need help"}:
        return "Venue Selection Needed"

    cleaned = re.sub(
        r"^(?:yes|yeah|yep|yup|ok|okay|sure|got it|alright|all right|"
        r"venue is|location is|hall is|place is|it'?s|its|"
        r"at|in|near|around)\s*[,.:;\-!]?\s*",
        "",
        raw,
        flags=re.I,
    )
    cleaned = re.sub(
        r"\b(?:yes|yeah|yep|yup|ok|okay|sure)\b[,.:;\-!]?\s*",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = cleaned.strip(" ,.-!")
    return normalize_location(cleaned or raw)
