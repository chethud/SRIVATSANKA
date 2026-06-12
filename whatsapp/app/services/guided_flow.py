"""Structured WhatsApp enquiry flow before cuisine selection."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    EVENT_TYPE_DETAILS,
    match_event_type,
)
from app.schemas import AgentTurnResult, EnquiryFields, MediaAttachment
from app.services.guided_conversation import (
    answer_details_question,
    answer_showcase_question,
    customer_wants_to_proceed,
)
from app.services.gemini_conversation import is_likely_field_answer, looks_like_question
from app.services.session_store import ConversationSession, GuidedStep
from app.services.website_gallery import customer_wants_photos, prepare_gallery_photos
from app.services.whatsapp_client import normalize_phone

logger = logging.getLogger(__name__)

DETAIL_STEPS: list[tuple[str, str]] = [
    ("event_date", "When is the event?"),
    ("event_location", "Which area in Bengaluru?"),
    ("preferred_callback", "When should we call you?"),
]


def _welcome_message() -> str:
    return f"Hi! Welcome to *{COMPANY['brand_name']}* 🌿 What's your name?"


def _company_intro_message(name: str) -> str:
    return f"Nice to meet you, *{name}*! What event are you planning?"


def _event_showcase_message(event_type: str, *, with_images: bool) -> str:
    details = EVENT_TYPE_DETAILS.get(event_type, EVENT_TYPE_DETAILS["General"])
    hook = details.get("short_reply") or f"We'd love to help with your {details['title'].lower()}!"
    if with_images:
        return f"{hook} Sharing a few photos 👇 Reply *ok* when ready to continue."
    return f"{hook} Questions? Or reply *ok* to share date & call time."


def _store_detail_field(session: ConversationSession, key: str, user_text: str) -> bool:
    value: str | int | None = user_text.strip()
    if not value:
        return False
    session.fields = EnquiryFields(**{**session.fields.model_dump(), key: value})
    return True


def _next_detail_prompt(session: ConversationSession) -> str | None:
    for key, prompt in DETAIL_STEPS:
        if getattr(session.fields, key) is None:
            return prompt
    return None


def _details_complete(session: ConversationSession) -> bool:
    return all(getattr(session.fields, key) is not None for key, _ in DETAIL_STEPS)


def _start_detail_collection(session: ConversationSession) -> AgentTurnResult:
    session.guided_step = GuidedStep.COLLECT_DETAILS
    first_prompt = _next_detail_prompt(session)
    name = session.fields.customer_name or "there"
    return AgentTurnResult(
        reply=f"Sure, *{name}*! {first_prompt}",
        fields=session.fields,
    )


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
        session.guided_step = GuidedStep.AWAIT_NAME
        return AgentTurnResult(reply=_welcome_message(), fields=session.fields)

    if step == GuidedStep.AWAIT_NAME:
        name = text[:80] if len(text) >= 2 else ""
        skip_names = {"hi", "hello", "hey", "hii", "namaste", "vanakkam", "start", "help"}
        if not name or name.lower() in skip_names:
            return AgentTurnResult(
                reply="Your name please? 😊",
                fields=session.fields,
            )
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
        session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
        return AgentTurnResult(reply=_company_intro_message(name), fields=session.fields)

    if step == GuidedStep.AWAIT_EVENT_TYPE:
        event_type = match_event_type(text)
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
        session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
        return AgentTurnResult(
            reply=_event_showcase_message(event_type, with_images=False),
            fields=session.fields,
            media=[],
        )

    if step == GuidedStep.AWAIT_POST_SHOWCASE:
        if customer_wants_to_proceed(text):
            return _start_detail_collection(session)

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
                return AgentTurnResult(
                    reply=f"Sorry — {retry}",
                    fields=session.fields,
                )
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                return AgentTurnResult(reply=f"Noted 👍 {next_prompt}", fields=session.fields)
            break

        if not _details_complete(session):
            prompt = _next_detail_prompt(session)
            return AgentTurnResult(reply=prompt or "Please share the remaining details.", fields=session.fields)

        phone = normalize_phone(whatsapp_id)
        session.fields = EnquiryFields(
            **{**session.fields.model_dump(), "phone_number": session.fields.phone_number or phone}
        )
        session.guided_step = GuidedStep.DONE
        name = session.fields.customer_name or "there"
        return AgentTurnResult(
            reply=(
                f"All set, *{name}* ✅ Our team will call you then.\n"
                f"Which meal services do you need? (e.g. breakfast, lunch, dinner)"
            ),
            fields=session.fields,
            enquiry_fields_complete=True,
        )

    return None
