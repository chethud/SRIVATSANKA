from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.seed_dishes import CATEGORY_LABELS
from app.database import get_db
from app.models import Dish, Enquiry, EnquiryStatus, Expense, Notification, NotificationType, Vendor, Worker
from app.schemas import (
    AIAssistantRequest,
    AIAssistantResponse,
    DashboardStats,
    DishOut,
    EnquiryCreateIn,
    EnquiryDishOut,
    EnquiryOut,
    NotificationOut,
    UpdateEnquiryStatus,
)
from app.services.dashboard_assistant import answer_dashboard_query
from app.services.whatsapp_client import is_whatsapp_configured

router = APIRouter(prefix="/api", tags=["api"])


def _enquiry_to_out(e: Enquiry) -> EnquiryOut:
    return EnquiryOut(
        id=e.id,
        customerName=e.customerName,
        phoneNumber=e.phoneNumber,
        eventType=e.eventType,
        eventDate=e.eventDate,
        eventLocation=e.eventLocation,
        guestCount=e.guestCount,
        preferredCallbackAt=e.preferredCallbackAt,
        status=e.status.value if hasattr(e.status, "value") else str(e.status),
        createdAt=e.createdAt,
        dishes=[
            EnquiryDishOut(
                id=d.id,
                dishId=d.dishId,
                dishName=d.dishName,
                category=d.category,
                customizations=d.customizations,
                notes=d.notes,
                quantity=getattr(d, "quantity", 1) or 1,
                unitPrice=d.unitPrice,
                served=getattr(d, "served", False) or False,
            )
            for d in e.dish_items
        ],
    )


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "kannans-api"}


@router.get("/whatsapp/status")
async def whatsapp_status() -> dict:
    from app.config import settings

    return {
        "configured": is_whatsapp_configured(),
        "phone_number_id_set": bool(settings.whatsapp_phone_number_id.strip()),
        "token_set": bool(settings.whatsapp_token.strip()),
        "verify_token": settings.whatsapp_verify_token,
        "webhook_path": "/webhook",
        "owner_phone": settings.owner_phone_number,
    }


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    new_count = await db.scalar(
        select(func.count()).select_from(Enquiry).where(Enquiry.status == EnquiryStatus.NEW)
    )
    total = await db.scalar(select(func.count()).select_from(Enquiry))
    unread = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.read.is_(False))
    )
    dish_count = await db.scalar(select(func.count()).select_from(Dish).where(Dish.isActive.is_(True)))
    upcoming = await db.scalar(
        select(func.count()).select_from(Enquiry).where(Enquiry.eventDate >= datetime.now())
    )
    vendor_count = await db.scalar(select(func.count()).select_from(Vendor))
    worker_count = await db.scalar(select(func.count()).select_from(Worker))
    expense_total = await db.scalar(select(func.sum(Expense.amount))) or 0
    return DashboardStats(
        new_enquiries=new_count or 0,
        total_enquiries=total or 0,
        unread_notifications=unread or 0,
        total_dishes=dish_count or 0,
        upcoming_events=upcoming or 0,
        total_vendors=vendor_count or 0,
        total_workers=worker_count or 0,
        total_expenses=float(expense_total),
    )


@router.get("/dishes", response_model=list[DishOut])
async def list_dishes(db: AsyncSession = Depends(get_db)) -> list[DishOut]:
    result = await db.execute(
        select(Dish).where(Dish.isActive.is_(True)).order_by(Dish.category, Dish.name)
    )
    dishes = list(result.scalars().all())
    return [
        DishOut(
            id=d.id,
            name=d.name,
            category=CATEGORY_LABELS.get(d.category, str(d.category)),
            price=d.price,
            description=d.description,
        )
        for d in dishes
    ]


@router.post("/enquiries", response_model=EnquiryOut)
async def create_enquiry(
    payload: EnquiryCreateIn,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    """Owner-created enquiry (walk-in, phone, email — not from WhatsApp)."""
    enquiry = Enquiry(
        customerName=payload.customerName.strip(),
        phoneNumber=payload.phoneNumber.strip(),
        eventType=payload.eventType.strip(),
        eventDate=payload.eventDate,
        eventLocation=payload.eventLocation.strip(),
        guestCount=max(1, payload.guestCount),
        preferredCallbackAt=payload.preferredCallbackAt,
        status=EnquiryStatus.NEW,
        notes=payload.notes or "Created manually by owner",
    )
    db.add(enquiry)
    await db.flush()
    db.add(
        Notification(
            type=NotificationType.NEW_ENQUIRY,
            title="New Enquiry",
            message=f"{enquiry.customerName} – {enquiry.eventType} (manual)",
        )
    )
    await db.commit()
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.id == enquiry.id)
    )
    row = result.scalar_one()
    return _enquiry_to_out(row)


@router.get("/enquiries", response_model=list[EnquiryOut])
async def list_enquiries(db: AsyncSession = Depends(get_db)) -> list[EnquiryOut]:
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .order_by(Enquiry.createdAt.desc())
        .limit(100)
    )
    return [_enquiry_to_out(e) for e in result.scalars().all()]


@router.patch("/enquiries/{enquiry_id}/status", response_model=EnquiryOut)
async def update_enquiry_status(
    enquiry_id: str,
    payload: UpdateEnquiryStatus,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    try:
        new_status = EnquiryStatus(payload.status.upper())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid status") from exc

    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    enquiry.status = new_status
    await db.commit()
    await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(db: AsyncSession = Depends(get_db)) -> list[Notification]:
    result = await db.execute(
        select(Notification).order_by(Notification.createdAt.desc()).limit(20)
    )
    return list(result.scalars().all())


@router.post("/ai-assistant", response_model=AIAssistantResponse)
async def dashboard_ai_assistant(
    payload: AIAssistantRequest,
    db: AsyncSession = Depends(get_db),
) -> AIAssistantResponse:
    reply = await answer_dashboard_query(payload.query, db)
    return AIAssistantResponse(reply=reply)
