"""Gallery photos from https://kannansharangapani.com/ for WhatsApp replies."""

import logging

from app.data.company_knowledge import GALLERY_ITEMS
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


def prepare_gallery_photos(
    session: ConversationSession,
    *,
    limit: int = 4,
) -> list[MediaAttachment]:
    """Return the next batch of unsent website gallery photos for WhatsApp delivery."""
    sent = set(session.sent_gallery_urls)
    attachments: list[MediaAttachment] = []
    for item in GALLERY_ITEMS:
        url = item["url"]
        if url in sent:
            continue
        caption = item.get("caption") or "SRIVATSANKA event catering"
        attachments.append(MediaAttachment(url=url, caption=caption))
        mark_gallery_sent(session, [url])
        if len(attachments) >= limit:
            break
    return attachments
