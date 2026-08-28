"""Classify each WhatsApp turn by meaning, not by the last question asked."""

from __future__ import annotations

import re
from enum import Enum

from app.data.company_knowledge import is_known_event_type, match_event_type
from app.services.callback_time import (
    _mentions_today,
    _mentions_tomorrow,
    _mentions_day_after_tomorrow,
)
from app.services.conversation_turns import extract_name, is_greeting_only
from app.services.event_date import is_impossible_calendar_date, looks_like_event_date
from app.services.human_style import (
    has_callback_intent,
    is_name_confirm_no,
    is_name_confirm_yes,
    normalize_customer_text,
)
from app.services.session_store import ConversationSession, GuidedStep
from app.services.validation_layer import is_cancel_message, is_reset_message
from app.services.venue_parser import looks_like_locality, parse_venue_reply

PHONE_RE = re.compile(
    r"(?:\+?91[\s-]*)?([6-9]\d{9})\b"
)
THIS_NUMBER_RE = re.compile(
    r"\b(?:this\s+(?:number|no|num)|same\s+number|my\s+(?:whatsapp\s+)?number|"
    r"on\s+this\s+(?:number|no)|call\s+(?:me\s+)?(?:on\s+)?this)\b",
    re.I,
)
CALLBACK_DAY_RE = re.compile(
    r"\b(today|tomorrow|tommorow|tommarow|tmrw|tmr|tonight)\b",
    re.I,
)


class MessageKind(str, Enum):
    GREETING = "GREETING"
    CUSTOMER_NAME = "CUSTOMER_NAME"
    EVENT_TYPE = "EVENT_TYPE"
    GUEST_COUNT = "GUEST_COUNT"
    EVENT_DATE = "EVENT_DATE"
    VENUE_HOME = "VENUE_HOME"
    VENUE_AREA = "VENUE_AREA"
    VENUE_STATUS = "VENUE_STATUS"
    CALLBACK_DATE = "CALLBACK_DATE"
    CALLBACK_TIME = "CALLBACK_TIME"
    CALLBACK_COMBO = "CALLBACK_COMBO"
    PHONE_NUMBER = "PHONE_NUMBER"
    CONFIRMATION = "CONFIRMATION"
    RESTART = "RESTART"
    CANCEL = "CANCEL"
    GENERAL_QUESTION = "GENERAL_QUESTION"
    UNKNOWN = "UNKNOWN"


def extract_phone_number(text: str) -> str | None:
    raw = text or ""
    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) == 12 and digits_only.startswith("91"):
        digits_only = digits_only[2:]
    if len(digits_only) == 10 and digits_only[0] in "6789":
        return digits_only
    match = PHONE_RE.search(raw)
    if match:
        return match.group(1)
    return None


def uses_this_whatsapp_number(text: str) -> bool:
    return bool(THIS_NUMBER_RE.search(text or ""))


def venue_area_missing(session: ConversationSession) -> bool:
    fields = session.fields
    if fields.venue_area:
        return False
    loc = (fields.event_location or "").strip()
    if loc and loc.lower() not in {"our house", "my house", "home", "at home", "customer's house"}:
        if fields.venue_name and "house" in fields.venue_name.lower() and not fields.venue_area:
            return True
        return False
    if fields.venue_status == "fixed" and (fields.venue_name or "house" in loc.lower() or not loc):
        return True
    return not loc


def classify_message(text: str, session: ConversationSession) -> MessageKind:
    raw = (text or "").strip()
    if not raw:
        return MessageKind.UNKNOWN
    if is_reset_message(raw):
        return MessageKind.RESTART
    if is_cancel_message(raw):
        return MessageKind.CANCEL
    if is_greeting_only(raw) and not extract_name(raw):
        return MessageKind.GREETING

    phone = extract_phone_number(raw)
    words = raw.split()
    # A 10-digit number (optionally with call-this-number wording) is a phone, never a name.
    if phone and (len(words) <= 8 or uses_this_whatsapp_number(raw)):
        return MessageKind.PHONE_NUMBER

    event_type = match_event_type(raw)
    if is_known_event_type(event_type) and (
        session.guided_step in {
            GuidedStep.AWAIT_HI,
            GuidedStep.AWAIT_NAME,
            GuidedStep.AWAIT_NAME_CONFIRM,
            GuidedStep.AWAIT_EVENT_TYPE,
            GuidedStep.AWAIT_POST_SHOWCASE,
        }
        or not session.fields.event_type
    ):
        # Avoid treating long planning sentences as only an event type when other slots are open.
        if len(words) <= 6 or not session.fields.event_type:
            return MessageKind.EVENT_TYPE

    asked = session.last_asked_slot
    venue_slots = {"event_location", "venue_name", "venue_area"}
    collecting_venue = asked in venue_slots
    if session.guided_step == GuidedStep.COLLECT_DETAILS and not collecting_venue:
        venue = None
    else:
        venue = parse_venue_reply(raw)
        if collecting_venue and venue.is_home:
            return MessageKind.VENUE_HOME
        if collecting_venue and venue.status and not venue.location and not venue.is_home:
            return MessageKind.VENUE_STATUS
        if collecting_venue and (venue.location or looks_like_locality(raw)):
            return MessageKind.VENUE_AREA

    lower = normalize_customer_text(raw)
    has_clock = bool(
        re.search(r"\b([01]?\d|2[0-3])\s*(?::|\.)\s*[0-5]\d\b", lower)
        or re.search(r"\b([1-9]|1[0-2])\s*(am|pm|a\.m|p\.m)\b", lower)
        or re.search(r"\bat\s+([1-9]|1[0-2]|12)\b", lower)
        or re.search(r"\b(morning|afternoon|evening|night|noon|midnight)\b", lower)
    )
    has_day = bool(
        CALLBACK_DAY_RE.search(lower)
        or _mentions_today(lower)
        or _mentions_tomorrow(lower)
        or _mentions_day_after_tomorrow(lower)
    )
    callbackish = has_callback_intent(raw) or uses_this_whatsapp_number(raw) or asked == "preferred_callback"

    if (has_day or has_clock or uses_this_whatsapp_number(raw)) and (
        callbackish or asked == "preferred_callback"
    ):
        if has_day and has_clock:
            return MessageKind.CALLBACK_COMBO
        if has_clock or uses_this_whatsapp_number(raw) and asked == "preferred_callback":
            return MessageKind.CALLBACK_TIME if has_clock else MessageKind.CALLBACK_COMBO
        if has_day:
            return MessageKind.CALLBACK_DATE

    if looks_like_locality(raw) and collecting_venue:
        return MessageKind.VENUE_AREA

    if is_name_confirm_yes(raw) or is_name_confirm_no(raw):
        return MessageKind.CONFIRMATION

    if re.search(r"^\s*\d{1,5}(?:\s*(?:-|to|–|—)\s*\d{1,5})?\s*$", raw) or re.search(
        r"\b\d+\s*(?:guests?|people|pax)\b", raw, re.I
    ):
        if asked == "guest_count" or (asked != "preferred_callback" and not has_clock):
            return MessageKind.GUEST_COUNT

    if looks_like_event_date(raw) and asked != "preferred_callback" and not callbackish:
        if is_impossible_calendar_date(raw):
            return MessageKind.EVENT_DATE
        return MessageKind.EVENT_DATE

    if extract_name(raw) and session.guided_step in {
        GuidedStep.AWAIT_HI,
        GuidedStep.AWAIT_NAME,
        GuidedStep.AWAIT_NAME_CONFIRM,
    }:
        return MessageKind.CUSTOMER_NAME

    if "?" in raw or looks_like_info_request(raw):
        return MessageKind.GENERAL_QUESTION

    return MessageKind.UNKNOWN


def looks_like_info_request(text: str) -> bool:
    t = normalize_customer_text(text)
    cues = (
        "what",
        "how much",
        "price",
        "menu",
        "cuisine",
        "photo",
        "do you",
        "can you",
        "tell me",
    )
    return any(c in t for c in cues)
