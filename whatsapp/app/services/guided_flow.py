"""Structured WhatsApp enquiry flow before cuisine selection."""

import logging

from app.data.company_knowledge import (
    COMPANY,
    EVENT_TYPE_DETAILS,
    GALLERY_IMAGE_URLS,
    SERVICES,
    WEBSITE_URL,
    WELCOME_IMAGE_CAPTIONS,
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
from app.services.whatsapp_client import normalize_phone, send_whatsapp_image

logger = logging.getLogger(__name__)

DETAIL_STEPS: list[tuple[str, str]] = [
    ("event_date", "When is your event? (e.g. 15 June 2026)"),
    ("event_location", "Which area or venue in Bengaluru will the event be held?"),
    (
        "preferred_callback",
        "When should Mr. Kannan's team call you with menu ideas and pricing? (e.g. today 4 PM, tomorrow morning)",
    ),
]


def _welcome_message() -> str:
    services = ", ".join(SERVICES[:3])
    return (
        f"Vanakkam! Welcome to *{COMPANY['brand_name']}* 🌿\n\n"
        f"We are *{COMPANY['legal_name']}* — pure vegetarian catering in Bengaluru "
        f"since {COMPANY['established']}. {COMPANY['tagline']}.\n\n"
        f"Our team handles {services}, and more — with hygiene, transparency, and a personal "
        f"touch from {COMPANY['managing_director']}.\n\n"
        f"May I know your *name*, please?"
    )


def _company_intro_message(name: str) -> str:
    return (
        f"Thank you, *{name}*! 🙏\n\n"
        f"We at *{COMPANY['brand_name']}* are glad you reached out. We specialise in memorable "
        f"pure-veg celebrations — weddings, house warmings, naming ceremonies, receptions, and corporate events.\n\n"
        f"📍 {COMPANY['address']}\n"
        f"📞 {COMPANY['phone']}\n"
        f"🌐 {WEBSITE_URL}\n\n"
        f"What type of celebration are you looking for?"
    )


def _event_showcase_message(event_type: str, *, with_images: bool) -> str:
    details = EVENT_TYPE_DETAILS.get(event_type, EVENT_TYPE_DETAILS["General"])
    image_note = (
        "Sharing a few photos from events we have catered 👇\n\n"
        if with_images
        else f"View event photos on our website: {WEBSITE_URL}\n\n"
    )
    return (
        f"Wonderful — *{details['title']}* is close to our heart! 💚\n\n"
        f"{details['description']}\n\n"
        f"{image_note}"
        "Ask us anything about our experience, menus, or service — we are happy to chat.\n\n"
        "When you are ready, reply *ok* and we will note your event date, venue, "
        "and the best time for our team to call you."
    )


async def _send_event_images(whatsapp_id: str, event_type: str) -> list[MediaAttachment]:
    details = EVENT_TYPE_DETAILS.get(event_type, EVENT_TYPE_DETAILS["General"])
    captions = details.get("image_captions") or WELCOME_IMAGE_CAPTIONS
    sent: list[MediaAttachment] = []
    for i, url in enumerate(GALLERY_IMAGE_URLS[:3]):
        cap = captions[i] if i < len(captions) else details["title"]
        ok = await send_whatsapp_image(whatsapp_id, url, caption=cap)
        sent.append(MediaAttachment(url=url, caption=cap))
        if not ok:
            logger.warning("Event gallery image failed: %s", url)
    return sent


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
        reply=(
            f"Thank you, *{name}*! Let us note your event details. 🌿\n\n"
            f"{first_prompt}"
        ),
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
                reply="Please share your name so we can assist you better 😊",
                fields=session.fields,
            )
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
        session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
        return AgentTurnResult(reply=_company_intro_message(name), fields=session.fields)

    if step == GuidedStep.AWAIT_EVENT_TYPE:
        event_type = match_event_type(text)
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
        media = await _send_event_images(whatsapp_id, event_type)
        session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
        return AgentTurnResult(
            reply=_event_showcase_message(event_type, with_images=bool(media)),
            fields=session.fields,
            media=media,
        )

    if step == GuidedStep.AWAIT_POST_SHOWCASE:
        if customer_wants_to_proceed(text):
            return _start_detail_collection(session)

        reply = await answer_showcase_question(session, text)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.COLLECT_DETAILS:
        for key, prompt in DETAIL_STEPS:
            if getattr(session.fields, key) is not None:
                continue

            if looks_like_question(text) and not is_likely_field_answer(text, key):
                reply = await answer_details_question(session, text, prompt)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not _store_detail_field(session, key, text):
                retry = dict(DETAIL_STEPS)[key]
                return AgentTurnResult(
                    reply=f"I didn't catch that — {retry}",
                    fields=session.fields,
                )
            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                return AgentTurnResult(reply=f"Noted, thank you! ✅\n\n{next_prompt}", fields=session.fields)
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
                f"Perfect, *{name}*! We have your enquiry details ✅\n\n"
                f"• Event: {session.fields.event_type}\n"
                f"• Date: {session.fields.event_date}\n"
                f"• Venue: {session.fields.event_location}\n"
                f"• Call back: {session.fields.preferred_callback}\n\n"
                "Pax per meal (breakfast, lunch, etc.) is confirmed when we plan your menu.\n\n"
                "Next, tell us which *cuisine styles* you prefer (e.g. Multi Cuisine, South Indian)."
            ),
            fields=session.fields,
            enquiry_fields_complete=True,
        )

    return None
