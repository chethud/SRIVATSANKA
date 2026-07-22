"""Gallery photos from https://srivatsanka.com/ for WhatsApp replies."""

import logging

from app.data.company_knowledge import GALLERY_ITEMS, match_service_key
from app.schemas import MediaAttachment
from app.services.session_store import ConversationSession

logger = logging.getLogger(__name__)


def customer_wants_photos(text: str) -> bool:
    t = text.lower().strip()
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


def prepare_gallery_photos(
    session: ConversationSession,
    *,
    limit: int = 4,
    user_text: str | None = None,
) -> list[MediaAttachment]:
    """Return the next batch of unsent website gallery photos for WhatsApp delivery."""
    sent = set(session.sent_gallery_urls)
    preferred = _preferred_categories(user_text)

    ordered = list(GALLERY_ITEMS)
    if preferred:
        preferred_items = [i for i in ordered if i.get("category") in preferred]
        other_items = [i for i in ordered if i.get("category") not in preferred]
        ordered = preferred_items + other_items

    attachments: list[MediaAttachment] = []
    for item in ordered:
        url = item["url"]
        if url in sent:
            continue
        caption = item.get("caption") or "SRIVATSANKA"
        attachments.append(MediaAttachment(url=url, caption=caption))
        mark_gallery_sent(session, [url])
        if len(attachments) >= limit:
            break
    return attachments
