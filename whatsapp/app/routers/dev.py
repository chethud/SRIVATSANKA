import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.data.seed_demo_data import seed_demo_data
from app.database import get_db
from app.schemas import DevMessageRequest, DevMessageResponse
from app.services.conversation_handler import handle_conversation
from app.services.data_reset import clear_all_dashboard_data

router = APIRouter(prefix="/dev", tags=["dev"])
logger = logging.getLogger(__name__)


def _check_seed_token(x_dev_seed_token: str | None) -> None:
    required = settings.dev_seed_token.strip()
    if not required:
        return
    if x_dev_seed_token != required:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Dev-Seed-Token")


@router.post("/seed")
async def seed_dashboard_demo(
    db: AsyncSession = Depends(get_db),
    x_dev_seed_token: str | None = Header(default=None),
) -> dict:
    """Load dummy enquiries, orders, vendors, workers, and expenses for UI testing."""
    _check_seed_token(x_dev_seed_token)
    result = await seed_demo_data(db, force=True)
    logger.info("Demo data seeded via API: %s", result)
    return result


@router.post("/reset")
async def reset_dashboard_data(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    x_dev_seed_token: str | None = Header(default=None),
) -> dict:
    """Delete all enquiries, orders, menu items, vendors, workers, expenses, and uploads."""
    _check_seed_token(x_dev_seed_token)
    if payload.get("confirm") != "DELETE_ALL":
        raise HTTPException(status_code=400, detail='Send {"confirm": "DELETE_ALL"} to wipe all data')
    result = await clear_all_dashboard_data(db)
    return {"status": "cleared", **result}


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
        media=result.media,
    )
