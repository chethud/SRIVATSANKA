"""Separate venue_status, home vs hall, and venue name / area."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.company_knowledge import match_event_type
from app.services.location_normalize import AREA_ALIASES, extract_location_entity, normalize_location

_FIXED_CUES = (
    "already fixed",
    "already booked",
    "venue is fixed",
    "venue is booked",
    "hall is booked",
    "place is fixed",
    "it's fixed",
    "its fixed",
    "is fixed",
    "fixed already",
    "we have a venue",
    "venue is ready",
)
_NOT_FIXED_CUES = (
    "not fixed",
    "not yet",
    "no venue",
    "looking for venue",
    "need a venue",
    "help with venue",
    "suggest a venue",
    "haven't decided",
    "havent decided",
    "undecided",
)

_HOME_RE = re.compile(
    r"\b(?:(?:at|in|from)\s+)?(?:our|my|the)?\s*(?:own\s+)?(?:house|home)\b|"
    r"\bhome\s+venue\b|"
    r"\bhouse\s+itself\b",
    re.I,
)

_CALLBACK_OR_FILLER = frozenset(
    {
        "yes",
        "no",
        "ok",
        "okay",
        "sure",
        "tomorrow",
        "today",
        "tonight",
        "morning",
        "afternoon",
        "evening",
        "night",
        "noon",
        "call",
        "callback",
        "now",
        "asap",
        "hi",
        "hai",
        "hello",
        "hey",
        "sir",
        "madam",
    }
)


@dataclass
class VenueParse:
    status: str | None  # fixed | not_fixed | None
    location: str | None
    venue_name: str | None = None
    is_home: bool = False
    confidence: float = 0.0


def _strip_event_words(text: str) -> str:
    cleaned = text
    et = match_event_type(text)
    if et and et != "General":
        cleaned = re.sub(re.escape(et), " ", cleaned, flags=re.I)
        for piece in et.lower().split():
            cleaned = re.sub(rf"\b{re.escape(piece)}\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(
        r"\b(house\s*warming|housewarming|gruhapravesham|grahapravesham|ceremony)\b",
        " ",
        cleaned,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", cleaned).strip(" ,.-")


def looks_like_locality(text: str) -> bool:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw or len(raw) < 3 or len(raw) > 60:
        return False
    lower = raw.lower()
    if lower in _CALLBACK_OR_FILLER:
        return False
    if re.search(r"\d{6,}", raw):
        return False
    if re.search(
        r"\b(call|tomorrow|today|morning|evening|afternoon|am|pm|guests?|people|pax|"
        r"january|february|march|april|june|july|august|september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
        lower,
    ):
        return False
    if re.search(r"\d", raw):
        return False
    if lower in AREA_ALIASES:
        return True
    for alias in AREA_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            return True
    words = [w for w in re.findall(r"[A-Za-z]+", raw)]
    if not words or len(words) > 4:
        return False
    if any(w.lower() in _CALLBACK_OR_FILLER for w in words):
        return False
    if len(words) == 1 and len(words[0]) >= 4:
        return True
    if 2 <= len(words) <= 4 and all(len(w) >= 2 for w in words):
        return True
    return False


def parse_venue_reply(text: str) -> VenueParse:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return VenueParse(status=None, location=None, confidence=0.0)
    lower = raw.lower()

    is_home = bool(_HOME_RE.search(lower)) and not re.search(
        r"\bhouse\s*warming\b|\bhousewarming\b", lower
    )

    status: str | None = None
    if any(c in lower for c in _NOT_FIXED_CUES):
        status = "not_fixed"
    elif is_home or any(c in lower for c in _FIXED_CUES):
        status = "fixed"

    remainder = _strip_event_words(raw)
    remainder = re.sub(
        r"\b(already|fixed|booked|its|it's|it is|the venue|venue is|location is|"
        r"our house|my house|our home|my home|at home|house|home)\b",
        " ",
        remainder,
        flags=re.I,
    )
    remainder = re.sub(r"\s+", " ", remainder).strip(" ,.-")

    location = None
    if remainder and remainder.lower() not in {"a", "the", "our", "my"}:
        loc = extract_location_entity(remainder)
        key = remainder.lower()
        has_place_token = any(alias in key for alias in AREA_ALIASES) or bool(
            re.search(
                r"\b(hall|resort|hotel|layout|nagar|road|apartment|flat|temple|"
                r"bengaluru|bangalore|locality|area)\b",
                key,
            )
        )
        leftover_chatter = bool(
            re.search(r"\b(planning|people|guests|pax|ceremony|already|warming)\b", remainder, re.I)
        )
        if looks_like_locality(remainder) and not leftover_chatter:
            location = loc or normalize_location(remainder)
        elif has_place_token and loc:
            location = loc

    if is_home:
        return VenueParse(
            status="fixed",
            location=location,
            venue_name="customer's house",
            is_home=True,
            confidence=0.95,
        )
    if status == "fixed" and not location:
        return VenueParse(status="fixed", location=None, confidence=0.9)
    if location:
        return VenueParse(status=status or "unknown", location=location, confidence=0.85)
    if status:
        return VenueParse(status=status, location=None, confidence=0.8)
    if looks_like_locality(raw):
        return VenueParse(
            status=None,
            location=normalize_location(raw),
            confidence=0.75,
        )
    return VenueParse(status=None, location=None, confidence=0.0)
