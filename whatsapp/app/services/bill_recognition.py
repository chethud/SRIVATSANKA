import asyncio
import json
import logging
import re
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

MIME_BY_EXT = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".pdf": "application/pdf",
}


def _parse_json_block(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def _recognize_sync(file_path: Path, *, expense_only: bool = False) -> dict:
    if not settings.gemini_api_key or settings.gemini_api_key.startswith("paste-your"):
        return {
            "doc_type": "expense",
            "amount": None,
            "notes": "Add GEMINI_API_KEY in whatsapp/.env for automatic bill reading",
            "recognized": False,
        }

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    ext = file_path.suffix.lower()
    mime = MIME_BY_EXT.get(ext, "application/octet-stream")

    if expense_only:
        prompt = """You are reading a catering business EXPENSE bill or receipt (India, INR).
Return ONLY valid JSON:
- doc_type: always "expense"
- amount: total as a number (no ₹ symbol), or null if unclear
- notes: one short line — WHAT is this expense? (e.g. vegetables, transport, gas, supplies, wages)

Example: {"doc_type": "expense", "amount": 4500, "notes": "Weekly vegetable purchase"}"""
    else:
        prompt = """You are reading a catering business bill (India, INR).
Return ONLY valid JSON:
- doc_type: "expense" if money spent, "profit" if money received
- amount: total as a number, or null if unclear
- notes: short description of what the bill is for

Example: {"doc_type": "expense", "amount": 4500, "notes": "Vegetable supplier"}"""

    model = genai.GenerativeModel(settings.gemini_model)

    if ext == ".pdf":
        uploaded = genai.upload_file(str(file_path))
        response = model.generate_content([uploaded, prompt])
    else:
        data = file_path.read_bytes()
        response = model.generate_content([{"mime_type": mime, "data": data}, prompt])

    raw = (response.text or "").strip()
    try:
        parsed = _parse_json_block(raw)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Bill recognition parse failed: %s", raw[:200])
        return {
            "doc_type": "expense",
            "amount": None,
            "notes": "Could not read bill — check image quality",
            "recognized": False,
        }

    doc_type = "expense" if expense_only else str(parsed.get("doc_type", "expense")).lower()
    if doc_type not in ("expense", "profit"):
        doc_type = "expense"

    amount = parsed.get("amount")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None

    return {
        "doc_type": doc_type,
        "amount": amount,
        "notes": str(parsed.get("notes", ""))[:500] or None,
        "recognized": amount is not None,
    }


async def recognize_bill(file_path: Path, *, expense_only: bool = False) -> dict:
    return await asyncio.to_thread(_recognize_sync, file_path, expense_only=expense_only)
