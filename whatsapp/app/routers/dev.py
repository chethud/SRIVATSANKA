from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DevMessageRequest, DevMessageResponse
from app.services.conversation_handler import handle_conversation

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/message", response_model=DevMessageResponse)
async def simulate_message(
    payload: DevMessageRequest,
    db: AsyncSession = Depends(get_db),
) -> DevMessageResponse:
    result, enquiry_saved = await handle_conversation(payload.from_number, payload.text, db)

    return DevMessageResponse(
        from_number=payload.from_number,
        sent=payload.text,
        reply=result.reply,
        is_complete=result.is_complete,
        fields=result.fields,
        enquiry_saved=enquiry_saved,
    )
