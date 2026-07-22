"""Structured WhatsApp enquiry flow before cuisine selection."""

import logging
import random

from app.data.company_knowledge import (
    is_known_event_type,
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
    ask_move_further_prompt,
    detail_question,
    is_small_talk,
    is_thanks_only,
    is_undecided,
    looks_like_polite_filler,
    small_talk_reply,
    thanks_reply,
    undecided_reply,
    wants_more_info,
    wants_to_move_further,
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
                "No worries 🙂 What's your name?",
                "Sure — who should I say this is from?",
                "Happy to help. May I know your name?",
            )
        )
    return random.choice(
        (
            "Could I get your name?",
            "Mind sharing your name?",
            "One quick one — what's your name?",
        )
    )


def _company_intro_message(name: str) -> str:
    return random.choice(
        (
            f"Nice to meet you, {name}! What are you planning?",
            f"Great to meet you, {name} 🙂 Is it a wedding, house warming, or something else?",
            f"Hi {name}! What occasion can I help with?",
        )
    )


def _event_showcase_message(event_type: str, *, with_images: bool) -> str:
    if not is_known_event_type(event_type):
        return random.choice(
            (
                "Got it! What occasion is this for?",
                "Sure — what are you celebrating?",
            )
        )
    label = event_type.lower()
    lead = random.choice(
        (
            f"That sounds wonderful — happy to help with your {label}.",
            f"Lovely! We can take care of your {label}.",
            f"Great — we've done many {label} celebrations.",
        )
    )
    hint = natural_continue_hint(event_type=event_type)
    if with_images:
        return f"{lead} Sharing a few photos 👇"
    return f"{lead} {hint}"


def _detect_event(text: str, *, name: str | None = None) -> str | None:
    """Return a known occasion from text, never a person's name."""
    et = match_event_type(text)
    if not is_known_event_type(et):
        return None
    if name and et.lower() == name.lower():
        return None
    # Single-word replies that are just the person's name are not occasions
    words = text.strip().split()
    if name and len(words) == 1 and words[0].lower().rstrip(".,!") == name.lower():
        return None
    return et


def _store_detail_field(session: ConversationSession, key: str, user_text: str) -> bool:
    from app.services.callback_time import normalize_callback_label

    value: str | int | None = user_text.strip()
    if not value:
        return False
    if key == "event_location":
        value = normalize_location(str(value))
    if key == "preferred_callback":
        value = normalize_callback_label(str(value))
    session.fields = EnquiryFields(**{**session.fields.model_dump(), key: value})
    return True


def _last_bot_asked_move_further(session: ConversationSession) -> bool:
    for msg in reversed(session.history):
        if msg.get("role") == "assistant":
            return "move further" in (msg.get("content") or "").lower()
        if msg.get("role") == "user":
            break
    return False


def _start_detail_collection(session: ConversationSession, user_text: str) -> AgentTurnResult:
    session.guided_step = GuidedStep.COLLECT_DETAILS
    first_prompt = _next_detail_prompt(session)
    name = session.fields.customer_name or "there"
    occasion = (_event_label(session) or "celebration").lower()
    # Prefer natural "When is your wedding?" style openers
    reply = random.choice(
        (
            f"Sure, {name}! {first_prompt}",
            f"Sounds good. {first_prompt}",
            f"Perfect. {first_prompt}",
            first_prompt or f"When is your {occasion}?",
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
        event_type = _detect_event(text, name=name)

        if name:
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
            if event_type:
                session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": event_type})
                session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
                reply = _event_showcase_message(event_type, with_images=False)
            else:
                session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
                reply = _company_intro_message(name)
        elif is_greeting_only(text):
            session.guided_step = GuidedStep.AWAIT_NAME
            reply = welcome_message()
        else:
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

        # Clear bogus event types that were actually someone's name
        stored = session.fields.event_type
        if stored and (not is_known_event_type(stored) or stored.lower() == name.lower()):
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": None})

        session.fields = EnquiryFields(**{**session.fields.model_dump(), "customer_name": name})
        maybe_event = _detect_event(text, name=name)

        if is_known_event_type(session.fields.event_type):
            session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
            showcase = _event_showcase_message(session.fields.event_type, with_images=False)
            reply = random.choice(
                (
                    f"Nice to meet you, {name}! {showcase}",
                    f"Hi {name}! {showcase}",
                )
            )
        elif maybe_event:
            session.fields = EnquiryFields(**{**session.fields.model_dump(), "event_type": maybe_event})
            session.guided_step = GuidedStep.AWAIT_POST_SHOWCASE
            showcase = _event_showcase_message(maybe_event, with_images=False)
            reply = f"Nice to meet you, {name}! {showcase}"
        else:
            session.guided_step = GuidedStep.AWAIT_EVENT_TYPE
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
                    "Sure — wedding, house warming, birthday…?",
                    "What type of event are you planning?",
                    "Is it a wedding or something else?",
                )
            )
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        event_type = _detect_event(text, name=session.fields.customer_name)
        if not event_type:
            reply = random.choice(
                (
                    "Got it — is it a wedding, house warming, birthday, or something else?",
                    "What celebration is this for?",
                )
            )
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

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

        # Understand first: info questions (even with typos) before form progress
        if wants_more_info(text) or looks_like_question(text):
            wants_photos = customer_wants_photos(text)
            media: list[MediaAttachment] = (
                prepare_gallery_photos(session, limit=4, user_text=text) if wants_photos else []
            )
            reply = await answer_showcase_question(session, text, sharing_photos=bool(media))
            return AgentTurnResult(reply=reply, fields=session.fields, media=media)

        # Explicit "move further" / continue → start collecting details
        if wants_to_move_further(text):
            return _start_detail_collection(session, text)

        # Soft "ok" / "yes" / "sure"
        if looks_like_polite_filler(text) or customer_wants_to_proceed(text):
            # If we just asked "move further?", treat ok/yes as yes — continue
            if _last_bot_asked_move_further(session):
                return _start_detail_collection(session, text)
            reply = ask_move_further_prompt()
            record_exchange(session, text, reply)
            return AgentTurnResult(reply=reply, fields=session.fields)

        # Only jump ahead when they clearly shared a date
        if is_likely_field_answer(text, "event_date"):
            session.guided_step = GuidedStep.COLLECT_DETAILS
            return await process_guided_flow(session, whatsapp_id, text)

        wants_photos = customer_wants_photos(text)
        media = prepare_gallery_photos(session, limit=4, user_text=text) if wants_photos else []
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

            # Info / questions first — never store "need more details" as a date/venue
            if wants_more_info(text) or (looks_like_question(text) and not is_likely_field_answer(text, key)):
                reply = await answer_details_question(session, text, prompt)
                return AgentTurnResult(reply=reply, fields=session.fields)

            if not is_likely_field_answer(text, key):
                reply = random.choice(
                    (
                        f"No worries — {prompt}",
                        f"Could you share that again? {prompt}",
                    )
                )
                record_exchange(session, text, reply)
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
                f"Perfect, {name}! We'll call around {when} about your {occasion}.",
                f"Got it — talk soon around {when} 🌿",
                f"Thanks {name}! Our team will ring you around {when}.",
            )
        )
        record_exchange(session, text, reply)
        return AgentTurnResult(
            reply=reply,
            fields=session.fields,
            enquiry_fields_complete=True,
        )

    return None
