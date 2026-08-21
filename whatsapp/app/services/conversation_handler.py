import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AgentTurnResult, EnquiryFields
from app.services.ai_agent import AIAgent, _all_fields_filled
from app.services.chat_handoff import resume_bot_for_phone
from app.services.guided_flow import process_guided_flow
from app.services.dish_flow import handle_dish_flow, start_dish_flow
from app.services.enquiry_service import append_followup_note_for_phone, save_enquiry
from app.services.human_style import (
    is_thanks_only,
    post_signoff_followup_reply,
    post_signoff_thanks_reply,
    wants_book_again,
)
from app.services.session_store import ConversationPhase, GuidedStep, session_store

ai_agent = AIAgent()
logger = logging.getLogger(__name__)


def _merge_replies(prefix: str | None, main: AgentTurnResult) -> AgentTurnResult:
    head = (prefix or "").strip()
    body = (main.reply or "").strip()
    if head and body:
        reply = f"{head}\n\n{body}"
    else:
        reply = body or head
    return main.model_copy(update={"reply": reply})


async def _persist_enquiry(
    db: AsyncSession,
    session,
    whatsapp_id: str,
    result: AgentTurnResult,
) -> tuple[AgentTurnResult, bool]:
    try:
        await save_enquiry(db, session.fields, whatsapp_id, session.selected_dishes)
        session._saved = True
        return result, True
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


async def handle_conversation(
    whatsapp_id: str, user_text: str, db: AsyncSession
) -> tuple[AgentTurnResult, bool]:
    """Returns (result, enquiry_saved)."""
    session = session_store.get(whatsapp_id)

    if user_text.strip().lower() in {"new", "start over", "restart", "reset", "begin again"} or (
        session.completed and session._saved and wants_book_again(user_text)
    ):
        from app.services.validation_layer import soft_reset_session

        soft_reset_session(session)
        await resume_bot_for_phone(db, whatsapp_id)
        reply = (
            f"Of course, {session.fields.customer_name}. We can start fresh."
            if session.name_confirmed and session.fields.customer_name
            else "Of course. We can start fresh."
        )
        if session.fields.event_type:
            reply += " Would you like a quick look at past setups, or shall we continue with your event details?"
        elif session.name_confirmed:
            reply += " What celebration would you like to plan?"
        else:
            reply += " May I have your name, please?"
        return (
            AgentTurnResult(reply=reply, fields=session.fields),
            False,
        )

    if session.completed and session._saved:
        # Post thank-you: note any extra specs; tell them a team member will call.
        if is_thanks_only(user_text):
            reply = post_signoff_thanks_reply(name=session.fields.customer_name)
        else:
            note = user_text.strip()
            if note:
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
            reply = post_signoff_followup_reply(name=session.fields.customer_name)
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
        return result, False

    if session.phase == ConversationPhase.ENQUIRY and session.guided_step != GuidedStep.DONE:
        guided = await process_guided_flow(session, whatsapp_id, user_text)
        if guided is not None:
            if guided.enquiry_fields_complete:
                session.completed = True
                return await _persist_enquiry(db, session, whatsapp_id, guided)
            return guided, False

    # Agent-led enquiry (fallback if guided flow completed without all fields)
    result = await ai_agent.process_message(session, user_text)

    if _all_fields_filled(session.fields) and session.phase == ConversationPhase.ENQUIRY:
        session.completed = True
        return await _persist_enquiry(db, session, whatsapp_id, result)

    if result.is_complete and not session._saved:
        return await _persist_enquiry(db, session, whatsapp_id, result)

    return result, False
