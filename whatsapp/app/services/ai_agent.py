import asyncio
import json
from datetime import datetime, timedelta

import google.generativeai as genai

from app.config import settings
from app.schemas import AgentTurnResult, EnquiryFields
from app.services.session_store import ConversationSession

SYSTEM_PROMPT = """You are the WhatsApp AI assistant for Kannans Catering, a professional catering service in India.

Your job is to warmly greet customers and collect an event enquiry through natural conversation.

You MUST collect ALL of these fields before marking complete:
1. customer_name – customer's full name
2. phone_number – contact number (include country code if given)
3. event_type – e.g. Wedding, Birthday, Corporate, Reception
4. event_date – date of the event (accept natural language like "15 June 2026")
5. event_location – venue or city
6. guest_count – approximate number of guests (integer)
7. preferred_callback – when the owner should call back (e.g. "today 4 PM", "tomorrow 10 AM")

Rules:
- Ask ONE or TWO related questions at a time; do not overwhelm the customer.
- If the customer gives multiple details in one message, acknowledge all of them.
- Keep replies concise and friendly (2–4 short sentences max).
- Use simple English; customers may mix Tamil/Hindi – understand intent.
- If a field is already collected, do not ask again unless unclear.
- When ALL 7 fields are collected, confirm the summary and set is_complete to true.
- If customer says "new" or wants to start over, treat all fields as empty.

Respond ONLY with valid JSON in this exact shape:
{
  "reply": "your message to the customer",
  "fields": {
    "customer_name": null or string,
    "phone_number": null or string,
    "event_type": null or string,
    "event_date": null or string,
    "event_location": null or string,
    "guest_count": null or integer,
    "preferred_callback": null or string
  },
  "is_complete": false or true
}
"""


def _merge_fields(existing: EnquiryFields, incoming: EnquiryFields) -> EnquiryFields:
    data = existing.model_dump()
    for key, value in incoming.model_dump().items():
        if value is not None:
            data[key] = value
    return EnquiryFields(**data)


def _all_fields_filled(fields: EnquiryFields) -> bool:
    return all(
        [
            fields.customer_name,
            fields.phone_number,
            fields.event_type,
            fields.event_date,
            fields.event_location,
            fields.guest_count is not None,
            fields.preferred_callback,
        ]
    )


def parse_event_date(text: str) -> datetime:
    for fmt in ("%d %B %Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%B %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return datetime.now() + timedelta(days=7)


def parse_callback_time(text: str) -> datetime:
    lower = text.lower()
    now = datetime.now()

    import re

    in_minutes = re.search(r"in\s+(\d+)\s*min", lower)
    if in_minutes:
        return now + timedelta(minutes=int(in_minutes.group(1)))

    if "tomorrow" in lower:
        base = now + timedelta(days=1)
    elif "today" in lower:
        base = now
    else:
        try:
            return parse_event_date(text)
        except Exception:
            return now + timedelta(hours=2)

    match = re.search(r"(\d{1,2})\s*(am|pm)", lower)
    if match:
        hour = int(match.group(1))
        if match.group(2) == "pm" and hour < 12:
            hour += 12
        if match.group(2) == "am" and hour == 12:
            hour = 0
        return base.replace(hour=hour, minute=0, second=0, microsecond=0)

    return base + timedelta(hours=2)


def _build_gemini_history(session: ConversationSession) -> list[dict]:
    history = []
    for msg in session.history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    return history


def _call_gemini(session: ConversationSession, user_text: str) -> str:
    genai.configure(api_key=settings.gemini_api_key)

    collected = session.fields.model_dump()
    context = f"Already collected fields (keep unless customer corrects): {json.dumps(collected)}"

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )

    history = _build_gemini_history(session)
    chat = model.start_chat(history=history)

    prompt = user_text if not collected else f"{context}\n\nCustomer message: {user_text}"
    response = chat.send_message(prompt)
    return response.text or "{}"


class AIAgent:
    async def process_message(self, session: ConversationSession, user_text: str) -> AgentTurnResult:
        if user_text.strip().lower() in {"new", "start over", "restart"}:
            session.fields = EnquiryFields()
            session.completed = False
            session.history = []
            user_text = "I'd like to submit a new enquiry"

        if session.completed:
            return AgentTurnResult(
                reply=(
                    "Your enquiry is already submitted ✅ Our team will contact you at your "
                    "preferred time. Send *new* to start another enquiry."
                ),
                fields=session.fields,
                is_complete=True,
            )

        session.history.append({"role": "user", "content": user_text})

        if not settings.gemini_api_key or settings.gemini_api_key.startswith("paste-your"):
            return self._fallback_reply(session, user_text)

        try:
            raw = await asyncio.to_thread(_call_gemini, session, user_text)
            payload = json.loads(raw)
            result = AgentTurnResult(
                reply=payload.get("reply", "Thank you! Could you tell me more about your event?"),
                fields=EnquiryFields(**payload.get("fields", {})),
                is_complete=bool(payload.get("is_complete", False)),
            )
        except Exception:
            return self._fallback_reply(session, user_text)

        session.fields = _merge_fields(session.fields, result.fields)

        if _all_fields_filled(session.fields):
            result.enquiry_fields_complete = True
            result.is_complete = False

        session.history.append({"role": "assistant", "content": result.reply})
        result.fields = session.fields
        return result

    def _fallback_reply(self, session: ConversationSession, user_text: str) -> AgentTurnResult:
        """Rule-based fallback when Gemini key is missing."""
        steps = [
            ("customer_name", "Welcome to Kannans Catering! 🍽️ May I know your name?"),
            ("phone_number", "Thank you! What is your phone number?"),
            ("event_type", "What type of event is this? (Wedding, Birthday, Corporate, etc.)"),
            ("event_date", "When is the event?"),
            ("event_location", "Where is the event location?"),
            ("guest_count", "Approximately how many guests?"),
            ("preferred_callback", "What time should we call you back? (e.g. today 4 PM)"),
        ]

        has_assistant_reply = any(m["role"] == "assistant" for m in session.history)

        if has_assistant_reply:
            for key, _ in steps:
                if getattr(session.fields, key) is None:
                    value: str | int | None = user_text.strip()
                    if key == "guest_count":
                        digits = "".join(c for c in user_text if c.isdigit())
                        value = int(digits) if digits else None
                    if value:
                        session.fields = EnquiryFields(
                            **{**session.fields.model_dump(), key: value}
                        )
                    break

        for key, prompt in steps:
            if getattr(session.fields, key) is None:
                session.history.append({"role": "assistant", "content": prompt})
                return AgentTurnResult(reply=prompt, fields=session.fields)

        return AgentTurnResult(
            reply="Perfect! Let's select your menu next.",
            fields=session.fields,
            enquiry_fields_complete=True,
        )


ai_agent = AIAgent()
