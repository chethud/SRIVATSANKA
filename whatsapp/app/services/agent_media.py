"""Welcome media and first-contact experience for WhatsApp agent."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    GALLERY_IMAGE_URLS,
    WEBSITE_URL,
    WELCOME_IMAGE_CAPTIONS,
)
from app.services.session_store import ConversationSession
from app.services.whatsapp_client import send_whatsapp_image, send_whatsapp_message

logger = logging.getLogger(__name__)

WELCOME_TRIGGERS = {
    "hi", "hello", "hey", "hii", "hola", "namaste", "vanakkam",
    "start", "menu", "help", "enquire", "enquiry", "quote",
}


def is_conversation_start(session: ConversationSession, user_text: str) -> bool:
    if session.history:
        return False
    t = user_text.strip().lower()
    return len(t) < 80 and (any(t.startswith(w) for w in WELCOME_TRIGGERS) or len(t.split()) <= 3)


async def send_welcome_media(to: str, session: ConversationSession) -> None:
    """Send gallery samples from the company website (first message only)."""
    if session.welcome_media_sent:
        return

    intro = (
        f"Hello! I'm here from *{COMPANY['brand_name']}* — {COMPANY['legal_name']}.\n\n"
        f"We've been creating memorable pure-veg celebrations in Bengaluru since "
        f"{COMPANY['established']} — weddings, house warmings, naming ceremonies, and more.\n\n"
        f"Browse our work: {WEBSITE_URL}"
    )
    await send_whatsapp_message(to, intro)

    for i, url in enumerate(GALLERY_IMAGE_URLS[:3]):
        cap = WELCOME_IMAGE_CAPTIONS[i] if i < len(WELCOME_IMAGE_CAPTIONS) else "Our events"
        ok = await send_whatsapp_image(to, url, caption=cap)
        if not ok:
            logger.warning("Welcome image %s failed for %s", url, to)

    session.welcome_media_sent = True
