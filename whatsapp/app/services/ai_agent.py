import asyncio
import json

import google.generativeai as genai

from app.config import settings
from app.data.company_knowledge import COMPANY, WEBSITE_URL, build_agent_context, build_short_company_context
from app.schemas import AgentTurnResult, EnquiryFields
from app.services.gemini_conversation import is_gemini_configured, trim_whatsapp_reply
from app.services.conversation_turns import is_greeting_only
from app.services.human_style import (
    HUMAN_CONSULTANT_STYLE,
    callback_pivot_prompt,
    detail_question,
    planning_date_prompt,
    warm_enquiry_signoff,
    welcome_message,
)
from app.services.session_store import ConversationSession

AGENT_SYSTEM_PROMPT = f"""You are an experienced celebration consultant for {COMPANY['brand_name']} on WhatsApp
(catering, décor, rituals, venues, guest hospitality).

You represent {COMPANY['legal_name']}, celebration services since {COMPANY['established']}.
Always use the full company name \"Srivatsanka Events & Services\" when introducing the company.
Official site: {WEBSITE_URL}

{build_agent_context()}

{build_short_company_context()}

{HUMAN_CONSULTANT_STYLE}

INFORMATION TO COLLECT (gently, one at a time, never like a form)
1. customer_name
2. phone_number (use WhatsApp number if customer confirms)
3. event_type (occasion; say wedding/house warming/naming ceremony etc. once known)
4. event_date (tentative date or month; keep full relative phrases like "3rd week of next month")
5. event_location (always ask venue status and location; if venue is fixed, collect venue name and area. If not fixed, collect preferred city or locality)
6. guest_count (keep FULL ranges like "30 to 50"; never drop to one number)
7. preferred_callback (when our team should call)

CONVERSATION RULES
- Acknowledge what they said before asking the next thing.
- Accept casual spelling (e.g. weding, hsr laytout, 24th of this month).
- If they ask price/menu: customised per celebration, discuss on callback.
- Custom / fusion / live counters: always respond warmly and note it for the planner/chef call. Never give restrictive rejections.
- If they say "discuss on call" / "tell me on call" / "talk on call": immediately ask for preferred_callback. Do not force more meal/event questions.
- If event date is today, tomorrow, or within 7 days: skip meal/theme/extra details and say a senior executive will call immediately.
- Meal type (lunch/dinner/high tea): ask ONLY for birthdays or informal family gatherings. For weddings, engagements, receptions, upanayanam, baby showers, housewarmings: after venue/location go to callback.
- If they choose straight to planning: ask for the date immediately. Do not dump mandap/floral/menu showcase text.
- Venue replies: store a clean place name (e.g. Hundur), never echo "Yes Hundur".
- Callback "now"/"ASAP"/"right away": say the lead planning team will call ASAP. Never invent a calculated timestamp.
- Do not assume the event is in Bengaluru or Bangalore. Always ask for venue/location explicitly.
- When done, warm hospitality sign-off and is_complete=true. Never dry system text like "We've already got your enquiry".
- If they say "new" / start over, greet fresh.
- Do NOT send or mention event photos unless the customer explicitly asks.

Respond ONLY with valid JSON:
{{
  "reply": "your WhatsApp message",
  "fields": {{
    "customer_name": null or string,
    "phone_number": null or string,
    "event_type": null or string,
    "event_date": null or string,
    "event_location": null or string,
    "guest_count": null or integer or string,
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
            fields.guest_count,
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
            temperature=0.9,
            max_output_tokens=160,
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
        if user_text.strip().lower() in {"new", "start over", "restart", "reset", "begin again"}:
            session.fields = EnquiryFields()
            session.completed = False
            session.history = []
            session.welcome_media_sent = False
            from app.services.session_store import GuidedStep

            session.guided_step = GuidedStep.AWAIT_HI
            user_text = "Hi"

        if session.completed:
            return AgentTurnResult(
                reply=warm_enquiry_signoff(
                    name=session.fields.customer_name,
                    event_type=session.fields.event_type,
                ),
                fields=session.fields,
                is_complete=True,
            )

        session.history.append({"role": "user", "content": user_text})

        agent_input = user_text
        if session.welcome_media_sent and sum(1 for m in session.history if m["role"] == "user") == 1:
            agent_input = (
                "[System: You already greeted the customer and sent sample photos from our website. "
                "Do not repeat a long introduction. Continue naturally.]\n\n"
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
        if is_greeting_only(user_text) and not session.fields.customer_name:
            reply = welcome_message()
            session.history.append({"role": "assistant", "content": reply})
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_greeting_only(user_text) and session.fields.customer_name and not session.fields.event_type:
            reply = (
                f"Hello {session.fields.customer_name}! 😊 How can we help bring your celebration to life today? "
                "Are you planning a wedding, an Upanayanam, a housewarming, or another special occasion?"
            )
            session.history.append({"role": "assistant", "content": reply})
            return AgentTurnResult(reply=reply, fields=session.fields)

        if not session.history or len(session.history) <= 1:
            reply = welcome_message()
            session.history.append({"role": "assistant", "content": reply})
            return AgentTurnResult(reply=reply, fields=session.fields)

        steps = [
            ("customer_name", welcome_message()),
            (
                "event_type",
                "Lovely to connect with you! 😊 How can we help bring your celebration to life today? Are you planning a wedding, an Upanayanam, a housewarming, or another special occasion?",
            ),
            ("event_date", planning_date_prompt()),
            ("guest_count", detail_question("guest_count", event_type=session.fields.event_type)),
            ("event_location", detail_question("event_location", event_type=session.fields.event_type)),
            ("preferred_callback", callback_pivot_prompt(name=session.fields.customer_name)),
        ]

        has_assistant = any(m["role"] == "assistant" for m in session.history)
        if has_assistant:
            # Never stuff raw user text into the next empty field (corrupts slots).
            from app.services.gemini_conversation import is_likely_field_answer, looks_like_question
            from app.services.human_style import wants_more_info

            for key, _ in steps:
                if getattr(session.fields, key) is None:
                    if looks_like_question(user_text) or wants_more_info(user_text):
                        break
                    if key == "customer_name":
                        from app.services.conversation_turns import extract_name

                        name = extract_name(user_text)
                        if name:
                            session.fields = EnquiryFields(
                                **{**session.fields.model_dump(), "customer_name": name}
                            )
                        break
                    if is_likely_field_answer(user_text, key):
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
            reply=warm_enquiry_signoff(
                name=session.fields.customer_name,
                event_type=session.fields.event_type,
            ),
            fields=session.fields,
            enquiry_fields_complete=True,
        )


ai_agent = AIAgent()
