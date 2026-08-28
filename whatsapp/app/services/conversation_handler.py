import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AgentTurnResult, EnquiryFields
from app.services.ai_agent import AIAgent, _all_fields_filled
from app.services.chat_handoff import resume_bot_for_phone
from app.services.guided_flow import process_guided_flow
from app.services.dish_flow import handle_dish_flow
from app.services.enquiry_service import append_followup_note_for_phone, save_enquiry
from app.services.human_style import (
    asks_callback_timing,
    callback_timing_reply,
    completed_booking_options_reply,
    extra_detail_noted_reply,
    help_options_reply,
    is_help_message,
    is_resume_booking_choice,
    is_thanks_only,
    post_signoff_thanks_reply,
    wants_book_again,
)
from app.services.session_store import ConversationPhase, GuidedStep, session_store
from app.services.validation_layer import (
    cancel_to_main_menu,
    greeting_reset_reply,
    is_cancel_message,
    is_reset_message,
    soft_reset_session,
    sync_conversation_state,
)
from app.services.whatsapp_interactive import attach_session_ui

ai_agent = AIAgent()
logger = logging.getLogger(__name__)


async def _persist_enquiry(
    db: AsyncSession,
    session,
    whatsapp_id: str,
    result: AgentTurnResult,
) -> tuple[AgentTurnResult, bool]:
    try:
        await save_enquiry(db, session.fields, whatsapp_id, session.selected_dishes)
        session._saved = True
        sync_conversation_state(session)
        return attach_session_ui(session, result), True
    except Exception:
        logger.exception("Failed to save WhatsApp enquiry for %s", whatsapp_id)
        session.completed = False
        session._saved = False
        session.phase = ConversationPhase.SELECT_CATEGORIES
        return (
            AgentTurnResult(
                reply=(
                    "Hmm, that didn’t save. Could you share the meals again, or say *skip*?"
                ),
                fields=session.fields,
                enquiry_fields_complete=True,
            ),
            False,
        )


def _is_fresh_booking_intent(user_text: str) -> bool:
    """past setups / event / photos — never treat these as completed-booking follow-up."""
    return is_resume_booking_choice(user_text)


async def handle_conversation(
    whatsapp_id: str,
    user_text: str,
    db: AsyncSession,
    *,
    message_id: str | None = None,
    button_id: str | None = None,
) -> tuple[AgentTurnResult, bool]:
    """Returns (result, enquiry_saved)."""
    session = session_store.get(whatsapp_id)
    session.last_user_message = user_text
    if message_id:
        session.last_processed_message_id = message_id

    if session.guided_step != GuidedStep.AWAIT_HI:
        if button_id == "book_again" or wants_book_again(user_text):
            reply = soft_reset_session(session)
            await resume_bot_for_phone(db, whatsapp_id)
            sync_conversation_state(session)
            return attach_session_ui(session, AgentTurnResult(reply=reply, fields=session.fields)), False

        if is_reset_message(user_text) and button_id not in {"booking_cancel", "cancel_yes", "cancel_no"}:
            reply = greeting_reset_reply(session)
            await resume_bot_for_phone(db, whatsapp_id)
            sync_conversation_state(session)
            return attach_session_ui(session, AgentTurnResult(reply=reply, fields=session.fields)), False

        if is_cancel_message(user_text) and not button_id:
            reply = cancel_to_main_menu(session)
            await resume_bot_for_phone(db, whatsapp_id)
            sync_conversation_state(session)
            return attach_session_ui(session, AgentTurnResult(reply=reply, fields=session.fields)), False

        if is_help_message(user_text):
            reply = help_options_reply()
            sync_conversation_state(session)
            return attach_session_ui(session, AgentTurnResult(reply=reply, fields=session.fields)), False

    if session.completed and session._saved and _is_fresh_booking_intent(user_text):
        # Resume a new booking from the current message (do not send the start-fresh copy).
        soft_reset_session(session)
        await resume_bot_for_phone(db, whatsapp_id)

    elif session.completed and session._saved:
        if asks_callback_timing(user_text):
            reply = callback_timing_reply(
                preferred_callback=session.fields.preferred_callback,
                name=session.fields.customer_name,
            )
            sync_conversation_state(session)
            return (
                AgentTurnResult(
                    reply=reply,
                    fields=session.fields,
                    is_complete=True,
                ),
                False,
            )
        if is_thanks_only(user_text):
            reply = post_signoff_thanks_reply(name=session.fields.customer_name)
            sync_conversation_state(session)
            return (
                AgentTurnResult(
                    reply=reply,
                    fields=session.fields,
                    is_complete=True,
                ),
                False,
            )
        note = user_text.strip()
        extra_noted = False
        if note and len(note.split()) >= 4:
            extra_noted = True
            existing = session.fields.notes or ""
            marker = f"[Follow-up note]: {note}"
            if marker not in existing:
                session.fields = EnquiryFields(
                    **{**session.fields.model_dump(), "notes": f"{existing}\n{marker}".strip()}
                )
            try:
                await append_followup_note_for_phone(db, whatsapp_id, note)
            except Exception:
                logger.exception("Failed to append follow-up note for %s", whatsapp_id)
        reply = (
            extra_detail_noted_reply(name=session.fields.customer_name)
            if extra_noted
            else completed_booking_options_reply(name=session.fields.customer_name)
        )
        sync_conversation_state(session)
        return (
            AgentTurnResult(
                reply=reply,
                fields=session.fields,
                is_complete=True,
            ),
            False,
        )

    # Incomplete save left session stuck, send them back to meal selection.
    if session.completed and not session._saved:
        session.completed = False
        session.phase = ConversationPhase.SELECT_CATEGORIES

    # Cuisine preference (types only, no individual dishes).
    if session.phase == ConversationPhase.SELECT_CATEGORIES:
        result = await handle_dish_flow(session, user_text, db)
        if result.is_complete and not session._saved:
            return await _persist_enquiry(db, session, whatsapp_id, result)
        sync_conversation_state(session)
        return result, False

    if session.phase == ConversationPhase.ENQUIRY and session.guided_step != GuidedStep.DONE:
        guided = await process_guided_flow(session, whatsapp_id, user_text, button_id=button_id)
        if guided is not None:
            guided = attach_session_ui(session, guided)
            if guided.enquiry_fields_complete:
                session.completed = True
                return await _persist_enquiry(db, session, whatsapp_id, guided)
            sync_conversation_state(session)
            return guided, False

    # Agent-led enquiry (fallback if guided flow completed without all fields)
    result = await ai_agent.process_message(session, user_text)

    if _all_fields_filled(session.fields) and session.phase == ConversationPhase.ENQUIRY:
        session.completed = True
        return await _persist_enquiry(db, session, whatsapp_id, result)

    if result.is_complete and not session._saved:
        return await _persist_enquiry(db, session, whatsapp_id, result)

    sync_conversation_state(session)
    return result, False
