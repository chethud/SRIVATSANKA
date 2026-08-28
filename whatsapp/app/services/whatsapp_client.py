from dataclasses import dataclass
import hashlib
import hmac
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API = "https://graph.facebook.com/v21.0"
_http_client: httpx.AsyncClient | None = None


@dataclass
class WhatsAppSendResult:
    ok: bool
    error: str | None = None
    message_id: str | None = None


def _client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=30)
    return _http_client


def normalize_phone(phone: str) -> str:
    """Strip to digits — normalize common India formats (e.g. 078… → 9178…)."""
    digits = re.sub(r"\D", "", phone or "")
    if not digits:
        return ""
    if digits.startswith("0") and len(digits) >= 11:
        digits = "91" + digits.lstrip("0")
    elif len(digits) == 10 and digits[0] in "6789":
        digits = "91" + digits
    return digits


def is_whatsapp_configured() -> bool:
    token = settings.whatsapp_token.strip()
    phone_id = settings.whatsapp_phone_number_id.strip()
    placeholders = {"", "your-whatsapp-cloud-api-token", "your-phone-number-id"}
    return token not in placeholders and phone_id not in placeholders


def verify_webhook_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verify X-Hub-Signature-256 from Meta."""
    secret = settings.meta_app_secret.strip()
    if not secret:
        if settings.is_production:
            logger.warning("META_APP_SECRET unset in production — rejecting unsigned webhook")
            return False
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header.removeprefix("sha256="), expected)


async def send_whatsapp_message_detailed(to: str, text: str) -> WhatsAppSendResult:
    """Send text. Returns ok / error / provider message id."""
    to = normalize_phone(to)
    if not to:
        logger.error("Invalid recipient phone number")
        return WhatsAppSendResult(False, "Invalid phone number")

    if not is_whatsapp_configured():
        if settings.is_production:
            logger.error("WhatsApp not configured — cannot send message in production")
            return WhatsAppSendResult(False, "WhatsApp API not configured")
        logger.info("[WhatsApp Mock] To: %s | %s", to, text[:120])
        return WhatsAppSendResult(True, None, "mock-wamid")

    client = _client()
    try:
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
        )
    except Exception as exc:
        logger.exception("WhatsApp send network error to %s", to)
        return WhatsAppSendResult(False, f"Network error: {exc}")

    if response.status_code >= 400:
        logger.error("WhatsApp send failed (%s): %s", response.status_code, response.text)
        detail = response.text[:240] if response.text else f"HTTP {response.status_code}"
        phone_id = settings.whatsapp_phone_number_id.strip()
        hint = (
            " Check WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_TOKEN in Meta → WhatsApp → API Setup "
            f"(current Phone number ID ends …{phone_id[-6:] if len(phone_id) >= 6 else phone_id})."
        )
        return WhatsAppSendResult(False, f"WhatsApp API error: {detail}.{hint}")
    message_id = None
    try:
        payload = response.json()
        message_id = ((payload.get("messages") or [{}])[0] or {}).get("id")
    except Exception:
        message_id = None
    logger.info("WhatsApp message sent to %s id=%s", to, message_id)
    return WhatsAppSendResult(True, None, message_id)


async def send_whatsapp_message(to: str, text: str) -> tuple[bool, str | None]:
    """Send text. Returns (success, error_message)."""
    result = await send_whatsapp_message_detailed(to, text)
    return result.ok, result.error


async def send_whatsapp_interactive(to: str, interactive: dict) -> tuple[bool, str | None]:
    """Send a Cloud API interactive message (reply buttons or list)."""
    to = normalize_phone(to)
    if not to:
        return False, "Invalid phone number"
    if not interactive:
        return False, "Missing interactive payload"

    if not is_whatsapp_configured():
        if settings.is_production:
            return False, "WhatsApp API not configured"
        logger.info("[WhatsApp Mock Interactive] To: %s | %s", to, interactive.get("type"))
        return True, None

    client = _client()
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
            "type": "interactive",
            "interactive": interactive,
        },
    )
    if response.status_code >= 400:
        logger.error("WhatsApp interactive send failed (%s): %s", response.status_code, response.text)
        detail = response.text[:240] if response.text else f"HTTP {response.status_code}"
        return False, f"WhatsApp API error: {detail}"
    logger.info("WhatsApp interactive message sent to %s", to)
    return True, None


async def send_whatsapp_image(to: str, image_url: str, caption: str | None = None) -> bool:
    """Send image by public URL (Meta WhatsApp Cloud API)."""
    to = normalize_phone(to)
    if not to or not image_url:
        return False

    if not is_whatsapp_configured():
        logger.info("[WhatsApp Mock Image] To: %s | %s | %s", to, image_url[:80], caption)
        return True

    payload: dict = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": {"link": image_url},
    }
    if caption:
        payload["image"]["caption"] = caption[:1024]

    client = _client()
    response = await client.post(
        f"{WHATSAPP_API}/{settings.whatsapp_phone_number_id}/messages",
        headers={
            "Authorization": f"Bearer {settings.whatsapp_token}",
            "Content-Type": "application/json",
        },
        json=payload,
    )
    if response.status_code >= 400:
        logger.error("WhatsApp image failed (%s): %s", response.status_code, response.text)
        return False
    logger.info("WhatsApp image sent to %s", to)
    return True
