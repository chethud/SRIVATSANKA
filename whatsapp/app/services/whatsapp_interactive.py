"""WhatsApp Cloud API interactive replies (buttons + lists) with stable IDs."""

from __future__ import annotations

from dataclasses import dataclass, field

# Reply button titles must be <= 20 chars; list row titles <= 24.

EVENT_ROWS = (
    ("event_wedding", "Wedding", "Ceremony, reception & coordination"),
    ("event_baby_shower", "Baby Shower", "Seemantham / Valaikappu"),
    ("event_housewarming", "Housewarming", "Griha Pravesham celebrations"),
    ("event_upanayanam", "Upanayanam", "Traditional ceremony planning"),
    ("event_birthday", "Birthday", "Family celebrations"),
    ("event_corporate", "Corporate Event", "Office & formal gatherings"),
    ("event_other", "Other", "Tell us the event name"),
)

EVENT_ID_TO_TYPE = {
    "event_wedding": "Wedding",
    "event_baby_shower": "Baby Shower",
    "event_housewarming": "House Warming",
    "event_upanayanam": "Upanayanam",
    "event_birthday": "Birthday",
    "event_corporate": "Corporate events",
}

EVENT_DISPLAY_LABEL = {
    "Wedding": "Wedding",
    "Baby Shower": "Baby Shower / Seemantham",
    "House Warming": "Housewarming",
    "Upanayanam": "Upanayanam",
    "Birthday": "Birthday",
    "Corporate events": "Corporate Event",
}

CUISINE_ROWS = (
    ("cuisine_traditional", "Traditional Vegetarian", ""),
    ("cuisine_south", "South Indian", ""),
    ("cuisine_north", "North Indian", ""),
    ("cuisine_custom", "Custom Menu", ""),
    ("cuisine_unsure", "Not Sure", ""),
)

CUISINE_ID_TO_VALUE = {
    "cuisine_traditional": "Traditional Vegetarian",
    "cuisine_south": "South Indian",
    "cuisine_north": "North Indian",
    "cuisine_custom": "Custom Menu",
    "cuisine_unsure": "To be discussed on call",
}

CALLBACK_ROWS = (
    ("callback_morning", "Morning", "Around 10 AM – 12 PM"),
    ("callback_afternoon", "Afternoon", "Around 2 PM – 5 PM"),
    ("callback_evening", "Evening", "Around 6 PM – 8 PM"),
    ("callback_other", "Choose Another Time", "Type a day and time"),
)

CALLBACK_ID_TO_LABEL = {
    "callback_morning": "morning",
    "callback_afternoon": "afternoon",
    "callback_evening": "evening",
}

CALLBACK_SLOT_IDS = {
    "callback_slot_8_10": "8 AM – 10 AM",
    "callback_slot_10_12": "10 AM – 12 PM",
    "callback_slot_12_2": "12 PM – 2 PM",
    "callback_slot_2_4": "2 PM – 4 PM",
    "callback_slot_4_6": "4 PM – 6 PM",
    "callback_slot_6_8": "6 PM – 8 PM",
}

EDIT_ROWS = (
    ("edit_event", "Event", "Change the occasion"),
    ("edit_date", "Date", "Change the date or month"),
    ("edit_guests", "Guests", "Change guest count"),
    ("edit_venue", "Venue", "Change venue or area"),
    ("edit_catering", "Catering", "Change cuisine"),
    ("edit_requirements", "Requirements", "Change special notes"),
    ("edit_callback", "Callback", "Change callback time"),
)

EDIT_ID_TO_SLOT = {
    "edit_event": "event_type",
    "edit_date": "event_date",
    "edit_guests": "guest_count",
    "edit_venue": "event_location",
    "edit_catering": "meal_preference",
    "edit_requirements": "special_requirements",
    "edit_callback": "preferred_callback",
}


@dataclass
class InteractiveSpec:
    kind: str  # button | list
    body: str
    footer: str | None = None
    list_button: str = "Select"
    buttons: list[tuple[str, str]] = field(default_factory=list)  # (id, title)
    rows: list[tuple[str, str, str]] = field(default_factory=list)  # (id, title, desc)
    section_title: str = "Options"

    def to_payload(self) -> dict:
        if self.kind == "list":
            action = {
                "button": self.list_button[:20],
                "sections": [
                    {
                        "title": self.section_title[:24],
                        "rows": [
                            {
                                "id": row_id,
                                "title": title[:24],
                                **({"description": desc[:72]} if desc else {}),
                            }
                            for row_id, title, desc in self.rows
                        ],
                    }
                ],
            }
            payload = {
                "type": "list",
                "body": {"text": self.body[:1024]},
                "action": action,
            }
        else:
            payload = {
                "type": "button",
                "body": {"text": self.body[:1024]},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": bid, "title": title[:20]}}
                        for bid, title in self.buttons[:3]
                    ]
                },
            }
        if self.footer:
            payload["footer"] = {"text": self.footer[:60]}
        return payload


def buttons(body: str, pairs: list[tuple[str, str]], *, footer: str | None = None) -> InteractiveSpec:
    return InteractiveSpec(kind="button", body=body, footer=footer, buttons=pairs)


def option_list(
    body: str,
    rows: tuple[tuple[str, str, str], ...] | list[tuple[str, str, str]],
    *,
    list_button: str,
    section_title: str,
    footer: str | None = None,
) -> InteractiveSpec:
    return InteractiveSpec(
        kind="list",
        body=body,
        footer=footer,
        list_button=list_button,
        rows=list(rows),
        section_title=section_title,
    )


def event_type_list(*, name: str | None, body: str | None = None) -> InteractiveSpec:
    who = (name or "").strip()
    text = body or (
        f"Lovely to connect with you, {who}! 😊\n\nWhat are you planning?\n\nPlease select an event below:"
        if who
        else "What are you planning?\n\nPlease select an event below:"
    )
    return option_list(text, EVENT_ROWS, list_button="Select event", section_title="EVENT TYPES")


def info_yes_no(*, event_label: str) -> InteractiveSpec:
    return buttons(
        f"Would you like to know more about our {event_label} event services and options?",
        [("info_yes", "Yes"), ("info_no", "No")],
    )


def plan_or_back(*, extra: str | None = None) -> InteractiveSpec:
    body = extra or "What would you like to do next?"
    return buttons(body, [("plan_event", "Plan My Event"), ("back_to_events", "Back to Events")])


def venue_status_buttons() -> InteractiveSpec:
    return buttons(
        "Is your venue already fixed?",
        [("venue_fixed", "Yes, Venue Fixed"), ("venue_help", "No, Need Help")],
    )


def cuisine_list() -> InteractiveSpec:
    return option_list(
        "What kind of catering would you prefer?",
        CUISINE_ROWS,
        list_button="Select cuisine",
        section_title="CATERING",
    )


def date_status_buttons() -> InteractiveSpec:
    return buttons(
        "Is your event date confirmed, or is it still tentative?",
        [("date_confirmed", "Date Confirmed"), ("date_tentative", "Tentative Date")],
    )


def event_month_list(*, tentative: bool) -> InteractiveSpec:
    from calendar import month_name
    from datetime import datetime
    from zoneinfo import ZoneInfo

    start = datetime.now(ZoneInfo("Asia/Kolkata")).date().replace(day=1)
    rows = []
    year, month = start.year, start.month
    for _ in range(5):
        label = f"{month_name[month]} {year}"
        rows.append((f"month_{year}_{month:02d}", label[:24], ""))
        month += 1
        if month > 12:
            month = 1
            year += 1
    rows.append(("month_other", "Other Month", ""))
    body = (
        "What month are you considering for the event?"
        if tentative
        else "Please select the month of your event."
    )
    return option_list(body, rows, list_button="Select month", section_title="MONTH")


def callback_day_buttons() -> InteractiveSpec:
    return buttons(
        "When would you like our senior planner to call you?",
        [
            ("callback_today", "Today"),
            ("callback_tomorrow", "Tomorrow"),
            ("callback_choose_date", "Choose Date"),
        ],
    )


def callback_period_buttons() -> InteractiveSpec:
    return buttons(
        "What time of day works best?",
        [
            ("callback_morning", "Morning"),
            ("callback_afternoon", "Afternoon"),
            ("callback_evening", "Evening"),
        ],
    )


def callback_slot_buttons(period: str) -> InteractiveSpec:
    period = (period or "").lower()
    if period == "afternoon":
        pairs = [
            ("callback_slot_12_2", "12 PM – 2 PM"),
            ("callback_slot_2_4", "2 PM – 4 PM"),
            ("callback_exact", "Choose Exact Time"),
        ]
    elif period == "evening":
        pairs = [
            ("callback_slot_4_6", "4 PM – 6 PM"),
            ("callback_slot_6_8", "6 PM – 8 PM"),
            ("callback_exact", "Choose Exact Time"),
        ]
    else:
        pairs = [
            ("callback_slot_8_10", "8 AM – 10 AM"),
            ("callback_slot_10_12", "10 AM – 12 PM"),
            ("callback_exact", "Choose Exact Time"),
        ]
    return buttons("What time would you prefer?", pairs)


def special_req_buttons() -> InteractiveSpec:
    return buttons(
        "Do you have any special requirements or preferences for the event?",
        [("req_yes", "Yes"), ("req_no", "No")],
    )


def callback_period_list() -> InteractiveSpec:
    return option_list(
        "When would be a convenient time for our senior event planner to call you?",
        CALLBACK_ROWS,
        list_button="Select time",
        section_title="CALLBACK",
    )


def booking_confirm_buttons(summary: str) -> InteractiveSpec:
    return buttons(
        summary,
        [
            ("booking_confirm", "Confirm"),
            ("booking_edit", "Edit Details"),
            ("booking_cancel", "Cancel"),
        ],
    )


def edit_field_list() -> InteractiveSpec:
    return option_list(
        "What would you like to change?",
        EDIT_ROWS,
        list_button="Select field",
        section_title="EDIT DETAILS",
    )


def cancel_confirm_buttons() -> InteractiveSpec:
    return buttons(
        "Would you like to cancel this planning session?",
        [("cancel_yes", "Yes, Cancel"), ("cancel_no", "No, Continue")],
    )


def book_again_buttons(*, name: str | None = None) -> InteractiveSpec:
    who = (name or "").strip() or "there"
    return buttons(
        f"Thank you, {who}! If you'd like to plan another celebration, tap below.",
        [("book_again", "Book Another Event")],
    )


def display_event_label(event_type: str | None) -> str:
    if not event_type or event_type == "General":
        return "event"
    return EVENT_DISPLAY_LABEL.get(event_type, event_type)


def attach_session_ui(session, result):
    """Attach WhatsApp interactive payload from the current conversation step."""
    if result is None:
        return None
    if getattr(result, "interactive", None):
        return result
    from app.services.session_store import GuidedStep

    step = session.guided_step
    asked = session.last_asked_slot
    spec = None
    if step == GuidedStep.AWAIT_NAME_CONFIRM:
        spec = buttons(
            result.reply,
            [("name_yes", "Yes"), ("name_no", "No")],
        )
    elif step == GuidedStep.AWAIT_EVENT_TYPE:
        spec = event_type_list(name=session.fields.customer_name, body=result.reply)
    elif step == GuidedStep.AWAIT_POST_SHOWCASE:
        spec = info_yes_no(event_label=display_event_label(session.fields.event_type))
    elif step in {GuidedStep.SHOWING_EVENT_INFORMATION, GuidedStep.PAST_SETUPS}:
        spec = plan_or_back(extra=result.reply)
    elif step == GuidedStep.AWAIT_BOOKING_CONFIRM:
        spec = booking_confirm_buttons(result.reply)
    elif step == GuidedStep.AWAIT_EDIT_FIELD:
        spec = edit_field_list()
    elif step == GuidedStep.AWAIT_CANCEL_CONFIRM:
        spec = cancel_confirm_buttons()
    elif step == GuidedStep.DONE or (session.completed and session._saved):
        spec = book_again_buttons(name=session.fields.customer_name)
    elif step == GuidedStep.COLLECT_DETAILS:
        if asked == "date_status":
            spec = date_status_buttons()
        elif asked == "event_date" and not session.pending_event_month:
            spec = event_month_list(tentative=session.fields.date_status != "confirmed")
        elif asked == "event_location" and not session.fields.venue_status:
            spec = venue_status_buttons()
        elif asked == "meal_preference":
            spec = cuisine_list()
        elif asked == "special_requirements" and not session.awaiting_special_req_text:
            spec = special_req_buttons()
        elif asked in {"callback_date", "preferred_callback"} and not session.fields.callback_date and not session.callback_period:
            spec = callback_day_buttons()
        elif asked in {"callback_period", "preferred_callback"} and session.fields.callback_date and not session.callback_period:
            spec = callback_period_buttons()
        elif asked == "callback_slot" or (
            asked in {"preferred_callback", "callback_time"}
            and session.callback_period
            and not session.fields.callback_time
        ):
            spec = callback_slot_buttons(session.callback_period or "")
    if spec:
        payload = spec.to_payload()
        payload["body"] = {"text": (result.reply or spec.body)[:1024]}
        result.interactive = payload
    return result


def parse_inbound_message(message: dict) -> tuple[str, str | None]:
    """Return (display_text, button_id)."""
    mtype = (message or {}).get("type")
    if mtype == "text":
        return ((message.get("text") or {}).get("body") or "").strip(), None
    if mtype == "interactive":
        inter = message.get("interactive") or {}
        itype = inter.get("type")
        if itype == "button_reply":
            row = inter.get("button_reply") or {}
            return (row.get("title") or "").strip(), (row.get("id") or "").strip() or None
        if itype == "list_reply":
            row = inter.get("list_reply") or {}
            return (row.get("title") or "").strip(), (row.get("id") or "").strip() or None
    if mtype == "button":
        row = message.get("button") or {}
        return (row.get("text") or "").strip(), (row.get("payload") or "").strip() or None
    return "", None
