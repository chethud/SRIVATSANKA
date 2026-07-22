"""Structured WhatsApp enquiry flow before cuisine selection."""

import logging
import random

from app.data.company_knowledge import (
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
from app.services.human_style import (
    acknowledge_opening_without_name,
    detail_question,
    is_small_talk,
    is_thanks_only,
    is_undecided,
    looks_like_polite_filler,
    small_talk_reply,
    soft_ack,
    thanks_reply,
    undecided_reply,
    welcome_message,
)
from app.services.session_store import ConversationSession, GuidedStep
from app.services.callback_time import format_callback_display, parse_callback_time
from app.services.location_normalize import normalize_location
from app.services.website_gallery import customer_wants_photos, prepare_gallery_photos
from app.services.whatsapp_client import normalize_phone

logger = logging.getLogger(__name__)

DETAIL_KEYS = ("event_date", "event_location", "preferred_callback")

SKIP_NAMES = {
    "hi",
    "hello",
    "hey",
    "hii",
    "hiii",
    "namaste",
    "vanakkam",
    "start",
    "help",
    "yes",
    "ok",
    "okay",
}


def _event_label(session: ConversationSession) -> str | None:
    et = session.fields.event_type
    if et and et != "General":
        return et
    return None


def _next_detail_key(session: ConversationSession) -> str | None:
    for key in DETAIL_KEYS:
        if getattr(session.fields, key) is None:
            return key
    return None


def _next_detail_prompt(session: ConversationSession) -> str | None:
    key = _next_detail_key(session)
    if not key:
        return None
    return detail_question(key, event_type=session.fields.event_type)


def _details_complete(session: ConversationSession) -> bool:
    return all(getattr(session.fields, key) is not None for key in DETAIL_KEYS)


def _ask_name_again(text: str) -> str:
    if is_greeting_only(text) or text.lower().strip().rstrip("!.,") in SKIP_NAMES:
        return random.choice(
            (
                "No worries at all 🙂 May I know your name?",
                "Of course — who should I say this is from?",
                "Happy to help. May I know your name?",
            )
        )
    return random.choice(
        (
            "Could I get your name so I know who I'm chatting with?",
            "Mind sharing your name? Helps me keep things personal.",
            "One quick one — may I know your name?",
        )
    )


def _company_intro_message(name: str) -> str:
    return random.choice(
        (
            f"Nice to meet you, *{name}*! What occasion are you planning?",
            f"Hi *{name}* 🌿 Wedding, house warming, birthday…?",
            f"Great to meet you, *{name}*! What's the celebration?",
        )
    )


def _event_showcase_message(event_type: str, *, with_images: bool) -> str:
    label = event_type.lower()
    lead = random.choice(
        (
            f"That sounds wonderful — happy to help with your {label}.",
            f"Lovely! We'd love to help with your {label}.",
            f"Great — we do a lot of {label} catering.",
        )
    )
    hint = natural_continue_hint(event_type=event_type)
    if with_images:
        return f"{lead} Sharing a few photos 👇 {hint}"
    return f"{lead} {hint}"


def _store_detail_field(session: ConversationSession, key: str, user_text: str) -> bool:
    value: str | int | None = user_text.strip()
    if not value:
        return False
    if key == "event_location":
        value = normalize_location(str(value))
    session.fields = EnquiryFields(**{**session.fields.model_dump(), key: value})
    return True


def _start_detail_collection(session: ConversationSession, user_text: str) -> AgentTurnResult:
    session.guided_step = GuidedStep.COLLECT_DETAILS
    first_prompt = _next_detail_prompt(session)
    name = session.fields.customer_name or "there"
    reply = random.choice(
        (
            f"Sure, *{name}*! {first_prompt}",
            f"Sounds good, *{name}*. {first_prompt}",
            f"Perfect. {first_prompt}",
            f"Got it. {first_prompt}",
        )
    )
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
        # Don't treat "General" match on short unrelated text as a real occasion
        if event_type == "General" and not any(
            w in text.lower()
            for w in ("event", "function", "celebration", "party", "catering", "menu")
        ):
            event_type = None

        if name:
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
            if event_type:
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
                session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
                reply = _event_showcase_message(event_type, with_images=False)
            else:
                session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
                reply = random.choice(
                    (
                        f"Hi *{name}*! What occasion are you planning?",
                        f"Nice to meet you, *{name}* — wedding, house warming, or something else?",
                        f"Hey *{name}*! What's the celebration?",
                    )
                )
        elif is_greeting_only(text):
            session.guided_step = GuidedStep.AWAIT_NAME
            reply = welcome_message()
        else:
            # Acknowledge what they shared (occasion, etc.) before asking name
            if event_type:
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
            session.guided_step = GuidedStep.AWAIT_NAME
            reply = acknowledge_opening_without_name(text, event_type)

        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_NAME:
        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        name = extract_name(text) or (text[:80] if len(text) >= 2 else "")
        if not name or name.lower() in SKIP_NAMES or is_greeting_only(text):
            reply = _ask_name_again(text)
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
        # Opening may already have stored event_type
        if session.fields.event_type and session.fields.event_type != "General":
            session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
            showcase = _event_showcase_message(session.fields.event_type, with_images=False)
            reply = random.choice(
                (
                    f"Nice to meet you, *{name}*! {showcase}",
                    f"Hi *{name}*! {showcase}",
                    f"Great, *{name}*. {showcase}",
                )
            )
        else:
            session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
            # Name message may also mention occasion
            maybe_event = match_event_type(text) if len(text) > 4 else None
            if maybe_event and maybe_event != "General":
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": maybe_event})
                session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
                showcase = _event_showcase_message(maybe_event, with_images=False)
                reply = f"Nice to meet you, *{name}*! {showcase}"
            else:
                reply = _company_intro_message(name)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields)

    if step == GuidedStep.AWAIT_EVENT_TYPE:
        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_undecided(text):
            reply = undecided_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_small_talk(text):
            reply = small_talk_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if looks_like_polite_filler(text) or customer_wants_to_proceed(text) or len(text.strip()) < 3:
            reply = random.choice(
                (
                    f"{soft_ack()} Wedding, house warming, birthday…?",
                    "What type of event are you planning?",
                    "Wedding, birthday, house warming, or something else?",
                )
            )
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        event_type = match_event_type(text)
        session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
        session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
        reply = _event_showcase_message(event_type, with_images=False)
        record_exchange(session, text, reply)
        return AgentTurnResult(reply=reply, fields=session.fields, media=[])

    if step == GuidedStep.AWAIT_POST_SHOWCASE:
        if is_thanks_only(text):
            reply = thanks_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_undecided(text):
            reply = undecided_reply()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if is_small_talk(text):
            reply = small_talk_reply(event_label=_event_label(session))
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        if customer_wants_to_proceed(text) or looks_like_polite_filler(text):
            return _start_detail_collection(session, text)

        # Customer already sharing a date — jump into details and store it this turn
        if is_likely_field_answer(text, "event_date") and not looks_like_question(text):
            session.guided_step = GuidedStep.COLLECT_DETAILS
            return await process_guided_flow(session, whatsapp_id, text)

        wants_photos = customer_wants_photos(text)
        media: list[MediaAttachment] = (
            prepare_gallery_photos(session, limit=4, user_text=text) if wants_photos else []
        )
        reply = await answer_showcase_question(session, text, sharing_photos=bool(media))
        return AgentTurnResult(reply=reply, fields=session.fields, media=media)

    if step == GuidedStep.COLLECT_DETAILS:
        for key in DETAIL_KEYS:
            if getattr(session.fields, key) is not None:
                continue

            prompt = detail_question(key, event_type=session.fields.event_type)

            if is_thanks_only(text):
                reply = f"{thanks_reply()} {prompt}"
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if is_undecided(text):
                reply = f"{undecided_reply()} {prompt}"
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if is_small_talk(text):
                reply = f"{small_talk_reply(event_label=_event_label(session))} {prompt}"
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if customer_wants_photos(text):
                media = prepare_gallery_photos(session, limit=4, user_text=text)
                reply = await answer_showcase_question(session, text, sharing_photos=bool(media))
                return AgentTurnResult(reply=reply, fields=session.fields, media=media)

            if looks_like_question(text) and not is_likely_field_answer(text, key):
                reply = await answer_details_question(session, text, prompt)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not _store_detail_field(session, key, text):
                reply = random.choice(
                    (
                        f"No worries — {prompt}",
                        f"Could you share that again? {prompt}",
                    )
                )
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)

            next_prompt = _next_detail_prompt(session)
            if next_prompt:
                stored = getattr(session.fields, key) or text
                reply = natural_field_ack(
                    key,
                    str(stored),
                    next_prompt,
                    event_type=session.fields.event_type,
                )
                record_exchange(session, text, reply)
                return AgentTurnResult(reply=reply, fields=session.fields)
            break

        if not _details_complete(session):
            prompt = _next_detail_prompt(session)
            reply = prompt or "Could you share a bit more?"
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        phone = normalize_phone(whatsapp_id)
        session.fields = EnquiryFields(
            **{**session.fields.model_dump(), "phone_number": session.fields.phone_number or phone}
        )
        session.guided_step = GuidedStep.DONE
        name = session.fields.customer_name or "there"
        occasion = (_event_label(session) or "celebration").lower()
        callback_when = format_callback_display(
            parse_callback_time(session.fields.preferred_callback or "in 2 hours"),
            session.fields.preferred_callback,
        )
        when = callback_when.split(" (")[0]
        reply = random.choice(
            (
                f"Perfect, *{name}*! We'll call around *{when}* about your {occasion}.",
                f"Got it — talk soon around *{when}* 🌿",
                f"Thanks *{name}*! Our team will ring you around *{when}*.",
            )
        )
        record_exchange(session, text, reply)
        return AgentTurnResult(
            reply=reply,
            fields=session.fields,
            enquiry_fields_complete=True,
        )

    return None
