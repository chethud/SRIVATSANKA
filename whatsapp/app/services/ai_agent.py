import asyncio
import json
from datetime import datetime, timedelta

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import COMPANY, WEBSITE_URL, build_agent_context
from app.schemas import AgentTurnResult, EnquiryFields
from app.services.gemini_conversation import is_gemini_configured
from app.services.session_store import ConversationSession

AGENT_SYSTEM_PROMPT = f"""You are a warm, professional *human catering consultant* for SRIVATSANKA on WhatsApp — NOT a rigid bot.

You represent {COMPANY['legal_name']} ({COMPANY['brand_name']}), Bengaluru pure-veg catering since {COMPANY['established']}.
Official site: {WEBSITE_URL}

{build_agent_context()}

YOUR PERSONALITY
- Sound like Kannan's team: confident, caring, experienced — never robotic or form-like.
- Build a real conversation: acknowledge feelings, celebrate their occasion, then gently gather details.
- Early in the chat, naturally mention what we do well (weddings, multi-cuisine veg menus, hygiene, personal touch by Mr. Kannan Sharangapani).
- Ask what they are looking for: event type, scale, cuisine style, dates — listen first, then guide.
- Use short WhatsApp-friendly paragraphs (2–4 sentences). Light emoji only where natural.
- Never say "I am a bot" or "automated system". Say "our team" / "we at SRIVATSANKA".
- Tamil/Hindi mixed English is fine — understand intent warmly.

INFORMATION TO COLLECT (all required before is_complete=true)
1. customer_name
2. phone_number (use WhatsApp number if customer confirms)
3. event_type
4. event_date
5. event_location
6. preferred_callback — when Mr. Kannan's team should call

Do NOT ask for guest count — pax varies per meal session and is set when planning the menu.

CONVERSATION RULES
- Do NOT ask for all fields in one message. Chat naturally; one or two questions at a time.
- If they share multiple details, thank them and confirm what you understood.
- Reference our experience when relevant (e.g. "We've catered many weddings in Bengaluru with South Indian & North Indian spreads").
- If they ask price/menu: say our team customises every menu and will discuss on callback; offer to note their preferences.
- When all 6 fields are clear, give a warm summary and set is_complete=true.
- If they say "new" / start over, reset mentally and greet fresh.

After is_complete=true the system will ask cuisine *types* only (multi cuisine, South Indian, etc.) — you do not need to list individual dishes.

Respond ONLY with valid JSON:
{{
  "reply": "your WhatsApp message",
  "fields": {{
    "customer_name": null or string,
    "phone_number": null or string,
    "event_type": null or string,
    "event_date": null or string,
    "event_location": null or string,
    "preferred_callback": null or string
  }},
  "is_complete": false or true
}}
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
    context = f"Already collected (keep unless customer corrects): {json.dumps(collected)}"

    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=AGENT_SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.72,
        ),
    )

    history = _build_gemini_history(session)
    chat = model.start_chat(history=history)

    prompt = user_text if not any(v for v in collected.values() if v is not None) else (
        f"{context}\n\nCustomer message: {user_text}"
    )
    response = chat.send_message(prompt)
    return response.text or "{}"


class AIAgent:
    async def process_message(self, session: ConversationSession, user_text: str) -> AgentTurnResult:
        if user_text.strip().lower() in {"new", "start over", "restart"}:
            session.fields = EnquiryFields()
            session.completed = False
            session.history = []
            session.welcome_media_sent = False
            from app.services.session_store import GuidedStep

            session.guided_step = GuidedStep.AWAIT_HI
            user_text = "Hi"

        if session.completed:
            return AgentTurnResult(
                reply=(
                    "Your enquiry is with our team ✅ We'll call you at the time you chose. "
                    "Send *new* anytime to plan another celebration."
                ),
                fields=session.fields,
                is_complete=True,
            )

        session.history.append({"role": "user", "content": user_text})

        agent_input = user_text
        if session.welcome_media_sent and sum(1 for m in session.history if m["role"] == "user") == 1:
            agent_input = (
                "[System: You already greeted the customer and sent sample photos from our website. "
                "Do not repeat a long introduction — continue naturally.]\n\n"
                f"Customer: {user_text}"
            )

        if not settings.gemini_api_key or not is_gemini_configured():
            return self._fallback_reply(session, agent_input)

        try:
            raw = await asyncio.to_thread(_call_gemini, session, agent_input)
            payload = json.loads(raw)
            result = AgentTurnResult(
                reply=payload.get("reply", "Thank you for reaching SRIVATSANKA! What celebration are you planning?"),
                fields=EnquiryFields(**payload.get("fields", {})),
                is_complete=bool(payload.get("is_complete", False)),
            )
        except Exception:
            return self._fallback_reply(session, agent_input)

        session.fields = _merge_fields(session.fields, result.fields)

        if _all_fields_filled(session.fields):
            result.enquiry_fields_complete = True
            result.is_complete = False

        session.history.append({"role": "assistant", "content": result.reply})
        result.fields = session.fields
        return result

    def _fallback_reply(self, session: ConversationSession, user_text: str) -> AgentTurnResult:
        """Conversational fallback when Gemini is unavailable."""
        if not session.history or len(session.history) <= 1:
            reply = (
                f"Vanakkam! Welcome to *{COMPANY['brand_name']}* 🌿\n\n"
                "We're Srivatsanka Events — pure veg catering in Bengaluru since 2017. "
                "Weddings, house warmings, naming ceremonies & more, with menus guests still talk about.\n\n"
                f"See our work: {WEBSITE_URL}\n\n"
                "What kind of celebration are you planning?"
            )
            session.history.append({"role": "assistant", "content": reply})
            return AgentTurnResult(reply=reply, fields=session.fields)

        steps = [
            ("customer_name", "Lovely! May I have your name?"),
            ("phone_number", "Thank you — and the best number to reach you?"),
            ("event_type", "What celebration is it? (Wedding, house warming, baby shower, etc.)"),
            ("event_date", "When is the event?"),
            ("event_location", "Which area or venue in Bengaluru?"),
            ("preferred_callback", "When should Mr. Kannan's team call you? (e.g. today 4 PM)"),
        ]

        has_assistant = any(m["role"] == "assistant" for m in session.history)
        if has_assistant:
            for key, _ in steps:
                if getattr(session.fields, key) is None:
                    value: str | int | None = user_text.strip()
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
            reply=(
                "Perfect — I have your event details. "
                "Last step: which cuisine styles interest you? (e.g. Multi Cuisine, South Indian)"
            ),
            fields=session.fields,
            enquiry_fields_complete=True,
        )


ai_agent = AIAgent()
