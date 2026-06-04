import asyncio
import json
import logging
import re
import time
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

EXPENSE_PROMPT = """You are reading a catering business EXPENSE bill or receipt (India, INR).
Extract from the document and return ONLY valid JSON (no markdown):
{
  "doc_type": "expense",
  "amount": 4500,
  "description": "Vendor or shop name",
  "expense_date": "2026-05-28",
  "purpose": "vegetables"
}
Rules:
- amount: grand total as number only, no currency symbols
- expense_date: YYYY-MM-DD from the bill date, or null
- description: vendor / bill title
- purpose: category (vegetables, transport, gas, supplies, wages, packaging, etc.)
"""


def _gemini_key_configured() -> bool:
    key = (settings.gemini_api_key or "").strip()
    if len(key) < 10:
        return False
    placeholders = ("paste-your", "your-gemini", "your_gemini", "xxx", "example")
    lower = key.lower()
    return not any(p in lower for p in placeholders)


def _parse_json_block(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


def _extract_pdf_text(file_path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        parts = []
        for page in reader.pages[:5]:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception as exc:
        logger.warning("PDF text extract failed: %s", exc)
        return ""


def _wait_for_uploaded_file(genai, uploaded) -> object:
    name = uploaded.name
    for _ in range(30):
        uploaded = genai.get_file(name)
        state = getattr(uploaded.state, "name", str(uploaded.state))
        if state == "ACTIVE":
            return uploaded
        if state == "FAILED":
            raise RuntimeError("Gemini could not process this PDF")
        time.sleep(1)
    raise RuntimeError("PDF processing timed out — try a photo (JPG/PNG) of the bill")


def _normalize_result(parsed: dict, *, expense_only: bool) -> dict:
    doc_type = "expense" if expense_only else str(parsed.get("doc_type", "expense")).lower()
    if doc_type not in ("expense", "profit"):
        doc_type = "expense"

    amount = parsed.get("amount")
    if amount is not None:
        try:
            amount = float(str(amount).replace(",", "").replace("₹", "").strip())
        except (TypeError, ValueError):
            amount = None

    description = (
        str(parsed.get("description") or parsed.get("vendor") or parsed.get("notes") or "")
        .strip()[:500]
        or None
    )
    purpose = str(parsed.get("purpose") or parsed.get("category") or "").strip()[:500] or None
    expense_date_raw = parsed.get("expense_date") or parsed.get("date") or parsed.get("bill_date")
    expense_date: str | None = None
    if expense_date_raw:
        raw = str(expense_date_raw).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
            try:
                from datetime import datetime

                expense_date = datetime.strptime(raw[:10], fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        if not expense_date and len(raw) >= 8:
            expense_date = raw[:10]

    recognized = amount is not None and bool(description or purpose)
    return {
        "doc_type": doc_type,
        "amount": amount,
        "description": description,
        "expense_date": expense_date,
        "purpose": purpose,
        "notes": description,
        "recognized": recognized,
    }


_MODEL_CACHE: list[str] | None = None


def _resolve_gemini_models(genai) -> list[str]:
    """Pick models that support generateContent for this API key."""
    global _MODEL_CACHE
    if _MODEL_CACHE:
        return _MODEL_CACHE

    preferred = [
        settings.gemini_model.strip(),
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.5-flash-lite",
    ]
    available: list[str] = []
    try:
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", None) or []
            if "generateContent" not in methods:
                continue
            name = (m.name or "").replace("models/", "")
            if name and "gemini" in name.lower():
                available.append(name)
    except Exception as exc:
        logger.warning("Could not list Gemini models: %s", exc)

    ordered: list[str] = []
    for name in preferred + available:
        if not name or name in ordered:
            continue
        if available and name not in available:
            continue
        # Skip TTS / image-only variants for bill reading
        lower = name.lower()
        if any(skip in lower for skip in ("tts", "image", "preview-tts", "nano-banana")):
            continue
        ordered.append(name)

    _MODEL_CACHE = ordered[:6] if ordered else ["gemini-2.5-flash", "gemini-2.0-flash"]
    return _MODEL_CACHE


def _failure(message: str) -> dict:
    return {
        "doc_type": "expense",
        "amount": None,
        "description": None,
        "expense_date": None,
        "purpose": None,
        "notes": message,
        "recognized": False,
    }


def _recognize_sync(file_path: Path, *, expense_only: bool = False) -> dict:
    if not _gemini_key_configured():
        return _failure(
            "Set GEMINI_API_KEY in whatsapp/.env (from https://aistudio.google.com/apikey) and restart the server."
        )

    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key.strip())
    ext = file_path.suffix.lower()
    mime = MIME_BY_EXT.get(ext, "application/octet-stream")
    prompt = EXPENSE_PROMPT if expense_only else EXPENSE_PROMPT

    models_to_try = _resolve_gemini_models(genai)
    last_error = ""
    raw = ""

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            parts: list = []

            if ext == ".pdf":
                pdf_text = _extract_pdf_text(file_path)
                if pdf_text:
                    parts.append(
                        f"Bill text extracted from PDF:\n{pdf_text[:8000]}\n\n{prompt}"
                    )
                else:
                    uploaded = genai.upload_file(str(file_path), mime_type="application/pdf")
                    uploaded = _wait_for_uploaded_file(genai, uploaded)
                    parts = [uploaded, prompt]
            else:
                data = file_path.read_bytes()
                parts = [{"mime_type": mime, "data": data}, prompt]

            response = model.generate_content(parts)
            raw = (response.text or "").strip()
            if not raw:
                last_error = "Empty response from Gemini"
                continue
            parsed = _parse_json_block(raw)
            return _normalize_result(parsed, expense_only=expense_only)
        except json.JSONDecodeError:
            logger.warning("Bill JSON parse failed for %s: %s", model_name, raw[:300] if "raw" in dir() else "")
            last_error = "Could not parse bill — try a clearer photo"
        except Exception as exc:
            logger.exception("Bill recognition failed (%s)", model_name)
            last_error = str(exc)
            if "API_KEY" in last_error.upper() or "401" in last_error or "403" in last_error:
                return _failure(
                    "Invalid GEMINI_API_KEY — create a key at https://aistudio.google.com/apikey "
                    "(starts with AIza…), update whatsapp/.env, restart uvicorn."
                )

    hint = last_error[:200] if last_error else "Recognition failed"
    return _failure(f"Could not read bill: {hint}. Try JPG/PNG or check GEMINI_API_KEY.")


async def recognize_bill(file_path: Path, *, expense_only: bool = False) -> dict:
    return await asyncio.to_thread(_recognize_sync, file_path, expense_only=expense_only)
