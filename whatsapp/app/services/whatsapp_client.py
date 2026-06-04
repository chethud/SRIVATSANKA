import hashlib
import hmac
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API = "https://graph.facebook.com/v21.0"


def normalize_phone(phone: str) -> str:
    """Strip to digits only – Meta WhatsApp API format (e.g. 917899102165)."""
    return re.sub(r"\D", "", phone or "")


def is_whatsapp_configured() -> bool:
    token = settings.whatsapp_token.strip()
    phone_id = settings.whatsapp_phone_number_id.strip()
    placeholders = {"", "your-whatsapp-cloud-api-token", "your-phone-number-id"}
    return token not in placeholders and phone_id not in placeholders


def verify_webhook_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verify X-Hub-Signature-256 from Meta. Skipped if META_APP_SECRET is not set."""
    secret = settings.meta_app_secret.strip()
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header.removeprefix("sha256="), expected)


async def send_whatsapp_message(to: str, text: str) -> bool:
    to = normalize_phone(to)
    if not to:
        logger.error("Invalid recipient phone number")
        return False

    if not is_whatsapp_configured():
        logger.info("[WhatsApp Mock] To: %s | %s", to, text[:120])
        return True

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{WHATSAPP_API}/{settings.whatsapp_phone_number_id}/messages",
            headers={
                "Authorization": f"Bearer {settings.whatsapp_token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"preview_url": False, "body": text},
            },
            timeout=30,
        )
        if response.status_code >= 400:
            logger.error("WhatsApp send failed (%s): %s", response.status_code, response.text)
            return False
        logger.info("WhatsApp message sent to %s", to)
        return True
