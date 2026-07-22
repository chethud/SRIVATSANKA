from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.meal_sessions import dish_category_label
from app.data.seed_demo_data import seed_demo_data
from app.data.seed_excel_reference_orders import seed_excel_reference_orders
from app.database import get_db
from app.datetime_util import as_naive_utc
from app.models import Dish, Enquiry, EnquiryStatus, Expense, Notification, NotificationType, Vendor, Worker
from app.quantity_units import normalize_quantity, normalize_quantity_unit
from app.schemas import (
    AIAssistantRequest,
    AIAssistantResponse,
    DashboardStats,
    DishOut,
    EnquiryCreateIn,
    EnquiryDishOut,
    EnquiryOut,
    EnquiryUpdateIn,
    NotificationOut,
    NotificationReadIn,
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
        ownerViewedAt=e.ownerViewedAt,
        notes=e.notes,
        createdAt=e.createdAt,
        dishes=[
            EnquiryDishOut(
                id=d.id,
                dishId=d.dishId,
                dishName=d.dishName,
                category=d.category,
                customizations=d.customizations,
                notes=d.notes,
                quantity=normalize_quantity(getattr(d, "quantity", 1)),
                quantityUnit=normalize_quantity_unit(getattr(d, "quantityUnit", None)),
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
        select(func.count())
        .select_from(Enquiry)
        .where(Enquiry.status == EnquiryStatus.NEW, Enquiry.ownerViewedAt.is_(None))
    )
    new_orders = await db.scalar(
        select(func.count())
        .select_from(Enquiry)
        .where(Enquiry.status == EnquiryStatus.CONVERTED, Enquiry.ownerViewedAt.is_(None))
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
        new_orders=new_orders or 0,
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
            category=dish_category_label(d.category),
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
    name = payload.customerName.strip()
    phone = payload.phoneNumber.strip()
    event_type = payload.eventType.strip()
    location = payload.eventLocation.strip()
    if not name or not phone or not event_type or not location:
        raise HTTPException(status_code=400, detail="Name, phone, event type, and location are required")

    enquiry = Enquiry(
        customerName=name,
        phoneNumber=phone,
        eventType=event_type,
        eventDate=as_naive_utc(payload.eventDate),
        eventLocation=location,
        guestCount=max(0, payload.guestCount),
        preferredCallbackAt=as_naive_utc(payload.preferredCallbackAt),
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
            enquiryId=enquiry.id,
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

    if new_status == EnquiryStatus.NEW:
        raise HTTPException(status_code=400, detail="Cannot set status to NEW")

    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    prev_status = enquiry.status
    enquiry.status = new_status
    if new_status == EnquiryStatus.CONVERTED and prev_status != EnquiryStatus.CONVERTED:
        enquiry.ownerViewedAt = None
    await db.commit()
    await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


@router.patch("/enquiries/{enquiry_id}", response_model=EnquiryOut)
async def update_enquiry(
    enquiry_id: str,
    payload: EnquiryUpdateIn,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if payload.notes is not None:
        enquiry.notes = payload.notes
    await db.commit()
    await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


@router.post("/enquiries/{enquiry_id}/viewed", response_model=EnquiryOut)
async def mark_enquiry_viewed(
    enquiry_id: str,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    changed = False
    if enquiry.status == EnquiryStatus.NEW:
        enquiry.status = EnquiryStatus.SEEN
        changed = True
    if enquiry.ownerViewedAt is None:
        enquiry.ownerViewedAt = datetime.now()
        changed = True
    if changed:
        await db.commit()
        await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


@router.post("/seed-excel-refs")
async def seed_excel_reference_orders_api(db: AsyncSession = Depends(get_db)) -> dict:
    """Load 4 Excel-reference CONVERTED orders (Nithin, Muralidharan, Casagrand, RA)."""
    return await seed_excel_reference_orders(db, replace=True)


@router.post("/seed-demo")
async def seed_demo_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    """Load demo enquiries, vendors, workers, expenses, and notifications."""
    return await seed_demo_data(db, force=True)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(db: AsyncSession = Depends(get_db)) -> list[Notification]:
    result = await db.execute(
        select(Notification).order_by(Notification.createdAt.desc()).limit(20)
    )
    return list(result.scalars().all())


@router.post("/notifications/read")
async def mark_notifications_read(
    payload: NotificationReadIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Notification).where(Notification.read.is_(False))
    if payload.ids:
        query = query.where(Notification.id.in_(payload.ids))
    result = await db.execute(query)
    rows = list(result.scalars().all())
    for row in rows:
        row.read = True
    if rows:
        await db.commit()
    return {"marked": len(rows)}


@router.post("/ai-assistant", response_model=AIAssistantResponse)
async def dashboard_ai_assistant(
    payload: AIAssistantRequest,
    db: AsyncSession = Depends(get_db),
) -> AIAssistantResponse:
    reply = await answer_dashboard_query(payload.query, db, rule_id=payload.ruleId)
    return AIAssistantResponse(reply=reply)
