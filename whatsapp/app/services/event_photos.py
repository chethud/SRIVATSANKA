"""Owner-uploaded event photos for the dashboard and WhatsApp."""

from __future__ import annotations

from app.config import settings
from app.data.company_knowledge import is_known_event_type, match_event_type

PHOTO_EVENT_TYPES = [
    "Wedding",
    "Birthday",
    "Corporate events",
]

MAX_PHOTOS_PER_EVENT = 5

_TRADITIONAL_KEYS = {
    "traditional",
    "tradition",
    "wedding",
    "engagement",
    "reception",
    "baby shower",
    "baby shower (seemantham)",
    "seemantham",
    "upanayanam",
    "house warming",
    "housewarming",
    "gruhapravesham",
    "grahapravesham",
    "naming ceremony",
    "family gathering",
    "family function",
    "family event",
    "family",
}

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTO_BYTES = 10 * 1024 * 1024

_EVENT_ALIASES = {
    "housewarming": "house warming",
    "house warming": "house warming",
    "gruhapravesham": "house warming",
    "grahapravesham": "house warming",
    "baby shower (seemantham)": "baby shower",
    "seemantham": "baby shower",
    "corporate": "corporate events",
    "corporate event": "corporate events",
    "corporate events": "corporate events",
    "family": "family gathering",
    "family gathering": "family gathering",
    "family function": "family gathering",
    "tradition": "traditional",
    "traditional": "traditional",
}


def public_api_base() -> str:
    raw = (settings.public_api_url or "").strip().rstrip("/")
    if raw:
        return raw
    if settings.is_production:
        return "http://13.232.230.198"
    return f"http://127.0.0.1:{settings.port}"


def event_photo_public_url(photo_id: str) -> str:
    return f"{public_api_base()}/api/public/event-photos/{photo_id}"


def event_photo_dashboard_url(photo_id: str) -> str:
    return f"/api/public/event-photos/{photo_id}"


def normalize_event_label(label: str | None) -> str:
    t = " ".join((label or "").lower().replace("_", " ").replace("-", " ").split())
    return _EVENT_ALIASES.get(t, t)


def canonical_photo_event(label: str | None) -> str | None:
    if not label:
        return None
    wanted = normalize_event_label(label)
    if wanted in {"birthday"}:
        return "Birthday"
    if wanted in {"corporate events", "corporate", "corporate event"}:
        return "Corporate events"
    if wanted in {"wedding"} or wanted in _TRADITIONAL_KEYS or wanted == "traditional":
        return "Wedding"
    for event in PHOTO_EVENT_TYPES:
        if normalize_event_label(event) == wanted:
            return event
    mapped = match_event_type(label)
    if mapped == "Birthday":
        return "Birthday"
    if mapped == "Corporate events":
        return "Corporate events"
    if mapped != "General" and is_known_event_type(mapped):
        return "Wedding"
    cleaned = " ".join((label or "").split()).strip()
    if len(cleaned) >= 2:
        return cleaned
    return None


def resolve_requested_event(*, user_text: str | None, session_event: str | None) -> str | None:
    """Prefer the event named in the customer's message, else the stored session event."""
    asked = canonical_photo_event(user_text)
    if asked:
        return asked
    mapped = match_event_type(user_text or "")
    if mapped == "Birthday":
        return "Birthday"
    if mapped == "Corporate events":
        return "Corporate events"
    if is_known_event_type(mapped):
        return "Wedding"
    return canonical_photo_event(session_event)


def sniff_image_type(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def guess_image_type(file_name: str) -> str:
    lower = (file_name or "").lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"
