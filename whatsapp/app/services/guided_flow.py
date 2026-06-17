"""Structured WhatsApp enquiry flow before cuisine selection."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    EVENT_TYPE_DETAILS,
    match_event_type,
)
from app.schemas import AgentTurnResult, EnquiryFields, MediaAttachment
from app.services.conversation_turns import (
    customer_wants_to_proceed,
    extract_name,
    is_greeting_only,
    natural_continue_hint,
    natural_field_ack,
    record_exchange,
)
from app.services.guided_conversation import (
    answer_details_question,
    answer_showcase_question,
)
from app.services.gemini_conversation import is_likely_field_answer, looks_like_question
from app.services.session_store import ConversationSession, GuidedStep
from app.services.callback_time import format_callback_display, parse_callback_time
from app.services.location_normalize import normalize_location
from app.services.website_gallery import customer_wants_photos, prepare_gallery_photos
from app.services.whatsapp_client import normalize_phone

logger = logging.getLogger(__name__)

DETAIL_STEPS: list[tuple[str, str]] = [
    ("event_date", "What date is the occasion?"),
    ("event_location", "Which area in Bengaluru is the venue?"),
    ("preferred_callback", "When works best for a quick call from our team?"),
]

SKIP_NAMES = {"hi", "hello", "hey", "hii", "namaste", "vanakkam", "start", "help"}


def _welcome_message() -> str:
    return (
        f"Hi! You've reached *{COMPANY['brand_name']}* 🌿 "
        "We do pure-veg catering across Bengaluru. What should I call you?"
    )


def _company_intro_message(name: str) -> str:
    return f"Lovely to meet you, *{name}*! What occasion are you planning?"


def _event_showcase_message(event_type: str, *, with_images: bool) -> str:
    details = EVENT_TYPE_DETAILS.get(event_type, EVENT_TYPE_DETAILS["General"])
    hook = details.get("short_reply") or f"We'd love to help with your {details['title'].lower()}!"
    hint = natural_continue_hint()
    if with_images:
        return f"{hook} Sharing a few photos from similar events 👇 {hint}"
    return f"{hook} {hint}"


def _store_detail_field(session: ConversationSession, key: str, user_text: str) -> bool:
    value: str | int | None = user_text.strip()
    if not value:
        return False
    if key == "event_location":
        value = normalize_location(str(value))
    session.fields = EnquiryFields(**{**session.fields.model_dump(), key: value})
    return True


def _next_detail_prompt(session: ConversationSession) -> str | None:
    for key, prompt in DETAIL_STEPS:
        if getattr(session.fields, key) is None:
            return prompt
    return None


def _details_complete(session: ConversationSession) -> bool:
    return all(getattr(session.fields, key) is not None for key, _ in DETAIL_STEPS)


def _start_detail_collection(session: ConversationSession, user_text: str) -> AgentTurnResult:
    session.guided_step = GuidedStep.COLLECT_DETAILS
    first_prompt = _next_detail_prompt(session)
    name = session.fields.customer_name or "there"
    reply = f"Sure, *{name}* — let's get the basics. {first_prompt}"
    record_exchange(session, user_text, reply)
    return AgentTurnResult(reply=reply, fields=session.fields)


async def process_guided_flow(
    session: ConversationSession,
    whatsapp_id: str,
    user_text: str,
) -> AgentTurnResult | None:
    step = session.guided_step
    text = user_text.strip()

    if step == GuidedStep.DONE:
        return None

    if step == GuidedStep.AWAIT_HI:
        name = extract_name(text)
        event_type = match_event_type(text) if len(text) > 4 else None

        if name:
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
            if event_type:
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
                session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
                reply = _event_showcase_message(event_type, with_images=False)
            else:
                session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
                reply = f"Hi *{name}*! Great to hear from you. What occasion are you planning?"
        elif is_greeting_only(text):
            session.guided_step = GuidedStep.AWAIT_NAME
            reply = _welcome_message()
        else:
            session.guided_step = GuidedStep.AWAIT_NAME
            reply = (
                f"Hi! Welcome to *{COMPANY['brand_name']}* 🌿 "
                "May I know your name? (I'll help with your enquiry right after.)"
            )

        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_NAME:
        name = extract_name(text) or (text[:80] if len(text) >= 2 else "")
        if not name or name.lower() in SKIP_NAMES:
            reply = "Sorry, I didn't catch that — what name should I use?"
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
        session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
        reply = _company_intro_message(name)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_EVENT_TYPE:
        if customer_wants_to_proceed(text) or len(text.strip()) < 3:
            reply = "Which occasion is it? (e.g. wedding, house warming, birthday, corporate)"
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        event_type = match_event_type(text)
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
        session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
        reply = _event_showcase_message(event_type, with_images=False)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields, media=[])

    if step == GuidedStep.AWAIT_POST_SHOWCASE:
        if customer_wants_to_proceed(text):
            return _start_detail_collection(session, text)

        wants_photos = customer_wants_photos(text)
        media: list[MediaAttachment] = prepare_gallery_photos(session, limit=4) if wants_photos else []
        reply = await answer_showcase_question(session, text, sharing_photos=bool(media))
        return AgentTurnResult(reply=reply, fields=session.fields, media=media)

    if step == GuidedStep.COLLECT_DETAILS:
        for key, prompt in DETAIL_STEPS:
            if getattr(session.fields, key) is not None:
                continue

            if customer_wants_photos(text):
                media = prepare_gallery_photos(session, limit=4)
                reply = await answer_showcase_question(session, text, sharing_photos=bool(media))
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)

            if looks_like_question(text) and not is_likely_field_answer(text, key):
                reply = await answer_details_question(session, text, prompt)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not _store_detail_field(session, key, text):
                retry = dict(DETAIL_STEPS)[key]
                reply = f"I didn't quite get that — {retry.lower()}"
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                reply = natural_field_ack(next_prompt)
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            break

        if not _details_complete(session):
            prompt = _next_detail_prompt(session)
            reply = prompt or "Could you share the remaining details?"
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        phone = normalize_phone(whatsapp_id)
        session.fields = EnquiryFields(
            **{**session.fields.model_dump(), "phone_number": session.fields.phone_number or phone}
        )
        session.guided_step = GuidedStep.DONE
        name = session.fields.customer_name or "there"
        callback_when = format_callback_display(
            parse_callback_time(session.fields.preferred_callback or "in 2 hours"),
            session.fields.preferred_callback,
        )
        reply = (
            f"Perfect, *{name}* — we'll call you around *{callback_when.split(' (')[0]}*. "
            f"Last thing: which meal services do you need? (e.g. *1,3* or *breakfast, dinner*)"
        )
        record_exchange(session, text, reply)
        return AgentTurnResult(
            reply=reply,
            fields=session.fields,
            enquiry_fields_complete=True,
        )

    return None
