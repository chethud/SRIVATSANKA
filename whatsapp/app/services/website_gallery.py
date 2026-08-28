"""Gallery photos for WhatsApp replies — uploaded event albums first, website gallery fallback."""

import logging

from sqlalchemy import select

from app.data.company_knowledge import GALLERY_ITEMS, match_service_key
from app.schemas import MediaAttachment
from app.services.event_photos import event_photo_public_url, resolve_requested_event
from app.services.session_store import ConversationSession

logger = logging.getLogger(__name__)


def customer_wants_photos(text: str) -> bool:
    from app.services.human_style import normalize_customer_text

    t = normalize_customer_text(text)
    cues = (
        "photo",
        "photos",
        "picture",
        "pictures",
        "pic",
        "pics",
        "gallery",
        "image",
        "images",
        "see your",
        "show me",
        "show your",
        "want photo",
        "want photos",
        "old event",
        "past event",
        "previous event",
        "events you",
        "event you have",
        "work you have",
        "work you done",
        "you have done",
        "portfolio",
        "samples",
        "sample",
        "look like",
        "how it looks",
        "visual",
        "setups",
        "past work",
        "want to see",
        "let me see",
        "nodu",
        "kalisu",
    )
    return any(c in t for c in cues)


def mark_gallery_sent(session: ConversationSession, urls: list[str]) -> None:
    seen = set(session.sent_gallery_urls)
    for url in urls:
        if url not in seen:
            session.sent_gallery_urls.append(url)


def _preferred_categories(user_text: str | None) -> list[str] | None:
    if not user_text:
        return None
    key = match_service_key(user_text)
    if key and key != "all":
        return [key]
    return None


async def _uploaded_photo_items(event_type: str | None) -> list[dict[str, str]]:
    from app.database import SessionLocal
    from app.models import EventPhoto
    from app.services.event_photos import canonical_photo_event

    async with SessionLocal() as db:
        result = await db.execute(select(EventPhoto).order_by(EventPhoto.createdAt.desc()))
        rows = list(result.scalars().all())

    wanted = canonical_photo_event(event_type) if event_type else None
    items: list[dict[str, str]] = []
    for row in rows:
        if wanted and canonical_photo_event(row.eventType) != wanted:
            continue
        caption = row.caption or f"{row.eventType} by Srivatsanka"
        items.append({"url": event_photo_public_url(row.id), "caption": caption})
    return items


def _website_gallery_items(user_text: str | None) -> list[dict[str, str]]:
    preferred = _preferred_categories(user_text)
    ordered = list(GALLERY_ITEMS)
    if preferred:
        preferred_items = [i for i in ordered if i.get("category") in preferred]
        other_items = [i for i in ordered if i.get("category") not in preferred]
        ordered = preferred_items + other_items
    return [{"url": i["url"], "caption": i.get("caption") or "Srivatsanka Events and Services"} for i in ordered]


async def prepare_gallery_photos(
    session: ConversationSession,
    *,
    limit: int = 1,
    user_text: str | None = None,
    event_type: str | None = None,
) -> list[MediaAttachment]:
    """Next photo: uploaded album for that event, else website gallery. No repeating captions."""
    sent = set(session.sent_gallery_urls)
    requested = resolve_requested_event(user_text=user_text, session_event=event_type)

    uploaded = await _uploaded_photo_items(requested)
    if requested and not uploaded:
        uploaded = []
    pool = uploaded if uploaded else _website_gallery_items(user_text or event_type)

    attachments: list[MediaAttachment] = []
    for item in pool:
        url = item["url"]
        if url in sent:
            continue
        attachments.append(MediaAttachment(url=url, caption=None))
        mark_gallery_sent(session, [url])
        if len(attachments) >= max(1, limit):
            break
    return attachments
