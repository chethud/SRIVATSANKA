import asyncio
import json

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import COMPANY, WEBSITE_URL, build_agent_context, build_short_company_context
from app.schemas import AgentTurnResult, EnquiryFields
from app.services.gemini_conversation import is_gemini_configured, trim_whatsapp_reply
from app.services.session_store import ConversationSession

AGENT_SYSTEM_PROMPT = f"""You are a warm, professional human events consultant for SRIVATSANKA EVENTS on WhatsApp.

You represent {COMPANY['legal_name']} ({COMPANY['brand_name']}), Bengaluru celebration services since {COMPANY['established']}.
Official site: {WEBSITE_URL}

{build_agent_context()}

{build_short_company_context()}

HOW YOU THINK AND REPLY
1. Read the customer's message fully — understand intent, tone, and what they actually need.
2. Respond to that first, naturally, like a real person texting on WhatsApp — not a form or script.
3. Keep replies concise: 1–3 short sentences, under 320 characters in "reply".
4. One question at a time. No bullet lists or brochure language unless they ask.
5. Never say you are a bot or AI. Match their tone — casual or formal.
6. Light emoji at most once, only if it fits.
7. Answer company / service questions using the website knowledge above. If unsure, share {WEBSITE_URL}.
8. Avoid stiff phrases ("Kindly", "Please provide", "I didn't catch that"). Vary acknowledgements.

INFORMATION TO COLLECT (all required before is_complete=true)
1. customer_name
2. phone_number (use WhatsApp number if customer confirms)
3. event_type (occasion)
4. event_date (occasion date)
5. event_location
6. preferred_callback — when our team should call

Do NOT ask for guest count — pax is set when planning the menu.

CONVERSATION RULES
- Chat naturally; don't rush all fields at once.
- Say "occasion" not "event" when asking customers.
- Accept casual spelling (e.g. weding, hsr laytout, 24th of this month).
- If they ask price/menu: customised per event — discuss on callback.
- When all 6 fields are clear, warm summary and is_complete=true.
- If they say "new" / start over, greet fresh.

Do NOT send or mention event photos unless the customer explicitly asks for photos.

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
            temperature=0.85,
            max_output_tokens=220,
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
                    "All good — your enquiry is with our team ✅ "
                    "We’ll call at the time you chose. Send *new* anytime for another celebration."
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
                reply=trim_whatsapp_reply(payload.get("reply", "Hi! What occasion are you looking for?")),
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
                f"Hi! Welcome to *{COMPANY['brand_name']}* 🌿 What occasion are you looking for?"
            )
            session.history.append({"role": "assistant", "content": reply})
            return AgentTurnResult(reply=reply, fields=session.fields)

        steps = [
            ("customer_name", "Lovely! Your name?"),
            ("phone_number", "Best number to reach you?"),
            ("event_type", "What occasion are you looking for?"),
            ("event_date", "What date is your occasion?"),
            ("event_location", "Which area in Bengaluru?"),
            ("preferred_callback", "When should we call you?"),
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
            reply="Got your details ✅ Which meal services do you need?",
            fields=session.fields,
            enquiry_fields_complete=True,
        )


ai_agent = AIAgent()
