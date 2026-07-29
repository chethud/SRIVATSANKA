import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AgentTurnResult
from app.services.ai_agent import AIAgent, _all_fields_filled
from app.services.chat_handoff import resume_bot_for_phone
from app.services.guided_flow import process_guided_flow
from app.services.dish_flow import handle_dish_flow, start_dish_flow
from app.services.enquiry_service import save_enquiry
from app.services.human_style import warm_enquiry_signoff
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

    if user_text.strip().lower() in {"new", "start over", "restart", "reset", "begin again"}:
        session_store.reset(whatsapp_id)
        await resume_bot_for_phone(db, whatsapp_id)
        session = session_store.get(whatsapp_id)
        user_text = "Hi"

    if session.completed and session._saved:
        return (
            AgentTurnResult(
                reply=warm_enquiry_signoff(
                    name=session.fields.customer_name,
                    event_type=session.fields.event_type,
                ),
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
