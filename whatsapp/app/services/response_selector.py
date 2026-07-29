"""Response selection helpers that preserve existing copy."""

from __future__ import annotations

from app.services.human_style import (
    callback_pivot_prompt,
    planning_date_prompt,
    urgent_timeline_reply,
    warm_enquiry_signoff,
)


def callback_response(name: str | None) -> str:
    return callback_pivot_prompt(name=name)


def planning_response() -> str:
    return planning_date_prompt()


def urgent_response() -> str:
    return urgent_timeline_reply()


def signoff_response(name: str | None, event_type: str | None) -> str:
    return warm_enquiry_signoff(name=name, event_type=event_type)
