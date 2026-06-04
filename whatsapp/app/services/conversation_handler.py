from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import AgentTurnResult
from app.services.ai_agent import AIAgent, _all_fields_filled
from app.services.dish_flow import handle_dish_flow, start_dish_flow
from app.services.enquiry_service import save_enquiry
from app.services.session_store import ConversationPhase, ConversationSession, session_store

ai_agent = AIAgent()


async def handle_conversation(
    whatsapp_id: str, user_text: str, db: AsyncSession
) -> tuple[AgentTurnResult, bool]:
    """Returns (result, enquiry_saved)."""
    session = session_store.get(whatsapp_id)

    if user_text.strip().lower() in {"new", "start over", "restart"}:
        session_store.reset(whatsapp_id)
        session = session_store.get(whatsapp_id)
        user_text = "Hi"

    if session.completed and session._saved:
        return (
            AgentTurnResult(
                reply=(
                    "Your enquiry is already submitted ✅ Send *new* to start another enquiry."
                ),
                fields=session.fields,
                is_complete=True,
            ),
            False,
        )

    # Dish selection phases
    if session.phase in {
        ConversationPhase.SELECT_CATEGORIES,
        ConversationPhase.SELECT_DISHES,
        ConversationPhase.CUSTOMIZATIONS,
    }:
        result = await handle_dish_flow(session, user_text, db)
        if result.is_complete and not session._saved:
            await save_enquiry(db, session.fields, whatsapp_id, session.selected_dishes)
            session._saved = True
            return result, True
        return result, False

    # Enquiry collection phase
    result = await ai_agent.process_message(session, user_text)

    if _all_fields_filled(session.fields) and session.phase == ConversationPhase.ENQUIRY:
        dish_result = await start_dish_flow(session, db)
        return dish_result, False

    if result.is_complete and not session._saved:
        await save_enquiry(db, session.fields, whatsapp_id, session.selected_dishes)
        session._saved = True
        return result, True

    return result, False
