"""JSON-first reply pack for the WhatsApp FSM.

The guided flow looks up scripted lines here BEFORE composing any text. Gemini is
only used when a reply_id is missing and the current state has no catch-all.

Source of truth for the copy: D:\\Kannan.rules.txt (mirrored into replies.json).
"""

from __future__ import annotations

import json
import logging
import random
from functools import lru_cache
from pathlib import Path

from app.schemas import MediaAttachment

logger = logging.getLogger(__name__)

_PACK_PATH = Path(__file__).resolve().parent.parent / "data" / "replies.json"


@lru_cache(maxsize=1)
def _load_pack() -> dict:
    try:
        with _PACK_PATH.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        logger.exception("Failed to load replies.json from %s", _PACK_PATH)
        return {"replies": {}, "catchall": {}, "event_profiles": {}, "media_groups": {}}


def reload_pack() -> None:
    """Clear the cached pack (useful for tests / hot reload)."""
    _load_pack.cache_clear()


def has_reply(reply_id: str) -> bool:
    return reply_id in _load_pack().get("replies", {})


def get_entry(reply_id: str) -> dict | None:
    return _load_pack().get("replies", {}).get(reply_id)


def get_catchall(state: str) -> str | None:
    """Return the catch-all reply_id for a state, if one is configured."""
    return _load_pack().get("catchall", {}).get(state)


def next_state_for(reply_id: str) -> str | None:
    entry = get_entry(reply_id)
    return entry.get("next_state") if entry else None


def ask_slot_for(reply_id: str) -> str | None:
    entry = get_entry(reply_id)
    return entry.get("ask_slot") if entry else None


def media_group_name_for(reply_id: str) -> str | None:
    entry = get_entry(reply_id)
    return entry.get("media_group") if entry else None


def get_event_profile(event_type: str | None) -> dict:
    """Per-event validation / showcase / media_group copy (pack first)."""
    pack = _load_pack()
    default = pack.get("default_event_profile", {})
    if not event_type:
        return default
    label = event_type.lower()
    for key, profile in pack.get("event_profiles", {}).items():
        if key in label:
            return profile
    return default


def get_media_group(name: str | None) -> list[MediaAttachment]:
    if not name:
        return []
    items = _load_pack().get("media_groups", {}).get(name, [])
    attachments: list[MediaAttachment] = []
    for item in items[:1]:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        attachments.append(MediaAttachment(url=url, caption=None))
    return attachments


def _fill(text: str, ctx: dict) -> str:
    for token, value in ctx.items():
        placeholder = "{" + token + "}"
        if placeholder in text:
            text = text.replace(placeholder, value)
    return text


def _build_context(
    *,
    name: str | None,
    event_type: str | None,
    special_request: str | None,
    slot: str | None,
) -> dict:
    # Local import avoids a circular import at module load time.
    from app.data.company_knowledge import COMPANY, POPULAR_DISHES
    from app.services.human_style import (
        ask_event_date_only,
        showcase_followup_date_ask,
    )

    who = (name or "").strip() or "there"
    dishes = ", ".join(POPULAR_DISHES[:3])
    occasion = (event_type or "celebration").strip().lower()
    if not occasion or occasion == "general":
        occasion = "celebration"
    event = event_type or "celebration"
    profile = get_event_profile(event_type)

    return {
        "name": who,
        "who": who,
        "event": event,
        "occasion": occasion,
        "special_request": special_request or "your request",
        "slot": slot or "",
        "dishes": dishes,
        "phone": COMPANY.get("phone", ""),
        "email": COMPANY.get("email", ""),
        "hours": COMPANY.get("eat_rep_eat_hours", ""),
        "company": COMPANY.get("legal_name", "Srivatsanka Events and Services"),
        "established": str(COMPANY.get("established", "")),
        "validation": profile.get("validation", ""),
        "showcase": profile.get("showcase", ""),
        "date_ask": showcase_followup_date_ask(event_type=event_type),
        "date_only": ask_event_date_only(event_type=event_type),
    }


def get_reply(
    reply_id: str,
    *,
    name: str | None = None,
    event_type: str | None = None,
    special_request: str | None = None,
    slot: str | None = None,
) -> str | None:
    """Return the rendered reply text for a reply_id, or None if missing.

    Supports single `text` or a `variants` list (random rotation, matching the
    previous python behavior).
    """
    entry = get_entry(reply_id)
    if not entry:
        return None

    if "variants" in entry and entry["variants"]:
        template = random.choice(entry["variants"])
    else:
        template = entry.get("text")
    if not template:
        return None

    ctx = _build_context(
        name=name,
        event_type=event_type,
        special_request=special_request,
        slot=slot,
    )
    return _fill(template, ctx)


if __name__ == "__main__":
    reload_pack()
    pack = _load_pack()
    replies = pack.get("replies") or {}
    assert replies, "replies.json has no replies"
    assert pack.get("_meta", {}).get("redeploy", {}).get("never_delete_live_data") is True
    sample = get_reply("state1.welcome")
    assert sample and "Srivatsanka" in sample
    print(f"ok {len(replies)} replies")
