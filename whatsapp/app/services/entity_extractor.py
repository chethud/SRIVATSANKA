"""Deterministic entity extraction helpers for the guided FSM."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.data.company_knowledge import is_known_event_type, match_event_type
from app.services.callback_time import is_immediate_callback, normalize_callback_label
from app.services.conversation_turns import extract_name
from app.services.event_date import is_urgent_event_date
from app.services.human_style import wants_discuss_on_call
from app.services.location_normalize import extract_location_entity
from app.services.session_store import ConversationSession


RESET_WORDS = {"reset", "restart", "start over", "begin again"}


@dataclass
class ExtractedEntities:
    customer_name: str | None = None
    event_type: str | None = None
    event_date: str | None = None
    guest_count: str | int | None = None
    event_location: str | None = None
    meal_preference: str | None = None
    preferred_callback: str | None = None
    special_requests: str | None = None
    reset_requested: bool = False
    callback_requested: bool = False
    urgent_date: bool = False


def _extract_event(text: str, name: str | None) -> str | None:
    event_type = match_event_type(text)
    if not is_known_event_type(event_type):
        return None
    if name and event_type.lower() == name.lower():
        return None
    return event_type


def _sanitize_name(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = re.split(
        r"\b(planning|looking|need|for|wedding|engagement|reception|birthday|housewarming|upanayanam|seemantham|baby shower)\b",
        name,
        maxsplit=1,
        flags=re.I,
    )[0].strip(" ,.-")
    if not cleaned:
        return None
    reject = {
        "hi",
        "hello",
        "hey",
        "yes",
        "ok",
        "okay",
        "sure",
        "no",
        "skip",
        "none",
        "thanks",
        "thank you",
        "new",
        "reset",
        "restart",
    }
    if cleaned.lower() in reject:
        return None
    return cleaned


def _extract_date_entity(text: str) -> str:
    raw = text.strip().rstrip(".,!?")
    lower = raw.lower()
    # Prefer fuller phrases like "next month 20th" / "20th of next month"
    fuller = (
        r"(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:next\s+month|this\s+month)",
        r"(?:next\s+month|this\s+month)\s+(?:the\s+)?\d{1,2}(?:st|nd|rd|th)?",
        r"(?:the\s+)?\d+(?:st|nd|rd|th)\s+week\s+of\s+next\s+month",
        r"next\s+month(?:\s+(?:the\s+)?\d+(?:st|nd|rd|th)\s+week)?",
        r"(?:the\s+)?\d+(?:st|nd|rd|th)\s+week\s+of\s+(?:this\s+|next\s+)?\w+",
        r"(?:early|mid|late)[\s-]*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?|next\s+month)",
        r"(?:this|next)\s+(?:week|month|weekend|year)",
    )
    for pat in fuller:
        match = re.search(pat, lower, re.I)
        if match:
            return raw[match.start() : match.end()]
    return raw


def _extract_guest_count(text: str) -> str | int:
    raw = text.strip()
    if re.search(r"\b\d{1,2}(?:st|nd|rd|th)\b", raw, re.I) and re.search(r"\b(week|month|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|today|tomorrow)\b", raw, re.I):
        return raw[:60] if raw else 100
    scoped_range = re.search(
        r"(\d+)\s*(?:-|–|—|to|and)\s*(\d+)\s*(?:guests?|people|pax)",
        raw,
        re.I,
    )
    if scoped_range:
        return f"{scoped_range.group(1)} to {scoped_range.group(2)}"
    scoped_single = re.search(r"(\d+)\s*(?:guests?|people|pax)\b", raw, re.I)
    if scoped_single:
        return int(scoped_single.group(1))
    range_match = re.search(
        r"(?:around\s+|about\s+|approx(?:imately)?\s+|roughly\s+)?(\d+)\s*(?:-|–|—|to|and)\s*(\d+)",
        raw,
        re.I,
    )
    if range_match:
        return f"{range_match.group(1)} to {range_match.group(2)}"
    single = re.search(r"(\d+)", raw)
    if single:
        return int(single.group(1))
    return raw[:60] if raw else 100


def _extract_meal_from_text(text: str) -> str | None:
    lower = text.lower()
    selected: list[str] = []
    if "breakfast" in lower:
        selected.append("Breakfast")
    if "lunch" in lower:
        selected.append("Lunch")
    if "dinner" in lower:
        selected.append("Dinner")
    if "snacks" in lower or "high tea" in lower:
        selected.append("Snacks")
    if "tea" in lower or "coffee" in lower:
        if "Snacks" not in selected:
            selected.append("Snacks")
        selected.append("Tea")
    return ", ".join(selected) if selected else None


def extract_entities(text: str, session: ConversationSession) -> ExtractedEntities:
    raw = (text or "").strip()
    lower = raw.lower()
    name = _sanitize_name(extract_name(raw) or None)
    event_type = _extract_event(raw, name)

    entities = ExtractedEntities(
        customer_name=name,
        event_type=event_type,
        reset_requested=lower in RESET_WORDS,
        callback_requested=wants_discuss_on_call(raw),
    )

    # Date words often appear in callback phrases — do not treat those as event_date.
    callbackish = bool(
        wants_discuss_on_call(raw)
        or re.search(r"\b(call|callback|ring me|speak|talk)\b", lower)
    )
    if is_urgent_event_date(raw) and not callbackish:
        entities.event_date = _extract_date_entity(raw)
        entities.urgent_date = True
    elif (not callbackish) and re.search(
        r"\b(today|tomorrow|next|week|month|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2})\b",
        lower,
    ):
        date_entity = _extract_date_entity(raw)
        if date_entity and date_entity != raw[:3]:
            entities.event_date = date_entity

    if re.search(r"\bguests?\b|\bpeople\b|\bpax\b", lower):
        entities.guest_count = _extract_guest_count(raw)

    if re.search(r"\b(venue|location|hall|area|city|locality|mysore|mysuru|bangalore|bengaluru|hunsur|hundur)\b", lower):
        entities.event_location = extract_location_entity(raw)

    meal = _extract_meal_from_text(raw)
    if meal:
        entities.meal_preference = meal
    elif session.history:
        history_text = " ".join(m["content"] for m in session.history if m["role"] == "user").lower()
        if "dinner" in history_text:
            entities.meal_preference = "Dinner, Dessert"
        elif "lunch" in history_text:
            entities.meal_preference = "Lunch"

    if is_immediate_callback(raw) or (
        entities.callback_requested
        and re.search(r"\b(today|tomorrow|weekend|morning|evening|afternoon|night|am|pm)\b", lower)
    ):
        entities.preferred_callback = normalize_callback_label(raw)
    elif re.search(r"\b(today|tomorrow|weekend|morning|evening|afternoon|night)\b", lower) and re.search(
        r"\b(call|callback|ring|speak|talk)\b",
        lower,
    ):
        entities.preferred_callback = normalize_callback_label(raw)

    if re.search(r"\b(fusion|custom|italian|chinese|dessert|live counter|pan asian|mocktail|gelato)\b", lower):
        if not re.search(r"\b(cocktail party|alcohol|alcoholic|conference|exhibition|expo)\b", lower):
            entities.special_requests = raw

    return entities
