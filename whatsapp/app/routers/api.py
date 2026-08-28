from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.meal_sessions import dish_category_label
from app.data.seed_demo_data import seed_demo_data
from app.data.seed_excel_reference_orders import seed_excel_reference_orders
from app.database import get_db
from app.datetime_util import as_naive_utc
from app.models import Dish, Enquiry, EnquiryDish, EnquiryPayment, EnquiryStatus, Expense, InvoiceUpload, Notification, NotificationType, Vendor, Worker, WorkerAssignment
from app.quantity_units import normalize_quantity, normalize_quantity_unit
from app.schemas import (
    AIAssistantRequest,
    AIAssistantResponse,
    DashboardStats,
    DishOut,
    EnquiryCreateIn,
    EnquiryDishOut,
    EnquiryOut,
    EnquiryPaymentIn,
    EnquiryPaymentOut,
    EnquiryUpdateIn,
    NotificationOut,
    NotificationReadIn,
    OrderExcelImportIn,
    OrderExcelImportOut,
    OrderExcelPreviewOut,
    OwnerPhoneIn,
    UpdateEnquiryStatus,
)
from app.config import settings
from app.services.dashboard_assistant import answer_dashboard_query
from app.services.gemini_conversation import is_gemini_configured
from app.services.order_excel_import import import_normalized_order, parse_order_excel_bytes
from app.services.order_billing import billing_total_from_notes
from app.services.profit import order_amount
from app.services.whatsapp_client import is_whatsapp_configured

router = APIRouter(prefix="/api", tags=["api"])


def _block_in_production() -> None:
    if settings.is_production:
        raise HTTPException(status_code=404, detail="Not found")


def _enquiry_billing_figures(e: Enquiry, menu_prices: dict[str, float] | None = None) -> tuple[float, float, float]:
    """Return (billing_total, amount_paid, amount_due)."""
    prices = menu_prices or {}
    from_notes = billing_total_from_notes(e.notes)
    if from_notes is not None and from_notes > 0:
        billing = from_notes
    else:
        billing = order_amount(e, prices) if e.dish_items is not None else 0.0
    discount = max(0.0, float(getattr(e, "discountAmount", 0) or 0))
    paid = sum(float(p.amount or 0) for p in (getattr(e, "payments", None) or []))
    due = max(0.0, billing - discount - paid)
    return billing, paid, due


def _enquiry_to_out(e: Enquiry, menu_prices: dict[str, float] | None = None) -> EnquiryOut:
    billing, paid, due = _enquiry_billing_figures(e, menu_prices)
    payments = [
        EnquiryPaymentOut(
            id=p.id,
            amount=p.amount,
            payerName=p.payerName,
            notes=p.notes,
            paidAt=p.paidAt,
        )
        for p in (getattr(e, "payments", None) or [])
    ]
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
        deliveredAt=getattr(e, "deliveredAt", None),
        paymentReceived=bool(getattr(e, "paymentReceived", False)),
        discountAmount=float(getattr(e, "discountAmount", 0) or 0),
        billingTotal=billing,
        amountPaid=paid,
        amountDue=due,
        payments=payments,
        createdAt=e.createdAt,
        dateStatus=getattr(e, "dateStatus", None),
        venueName=getattr(e, "venueName", None),
        venueArea=getattr(e, "venueArea", None),
        mealPreference=getattr(e, "mealPreference", None),
        specialRequirements=getattr(e, "specialRequirements", None),
        callbackDate=getattr(e, "callbackDate", None),
        callbackTime=getattr(e, "callbackTime", None),
        notificationStatus=getattr(e, "notificationStatus", None),
        notificationAttempts=int(getattr(e, "notificationAttempts", 0) or 0),
        notificationSentAt=getattr(e, "notificationSentAt", None),
        notificationError=getattr(e, "notificationError", None),
        reminderSent=bool(getattr(e, "reminderSent", False)),
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
            for d in (e.dish_items or [])
        ],
    )


def _enquiry_load_options():
    return (selectinload(Enquiry.dish_items), selectinload(Enquiry.payments))


@router.get("/health", response_model=None)
async def health(db: AsyncSession = Depends(get_db)):
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    payload = {
        "status": "ok" if db_ok else "degraded",
        "service": "kannans-api",
        "environment": settings.environment,
        "checks": {
            "database": db_ok,
            "whatsapp": is_whatsapp_configured(),
            "gemini": is_gemini_configured(),
        },
    }
    if not db_ok:
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/whatsapp/status")
async def whatsapp_status(db: AsyncSession = Depends(get_db)) -> dict:
    from app.services.app_settings import get_owner_phone

    phone_id = settings.whatsapp_phone_number_id.strip()
    owner = await get_owner_phone(db)
    return {
        "configured": is_whatsapp_configured(),
        "phone_number_id_set": bool(phone_id),
        "phone_number_id_suffix": phone_id[-6:] if len(phone_id) >= 6 else phone_id,
        "token_set": bool(settings.whatsapp_token.strip()),
        "webhook_path": "/webhook",
        "owner_phone": owner,
    }


@router.patch("/settings/owner-phone")
async def update_owner_phone(
    payload: OwnerPhoneIn,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services.app_settings import set_owner_phone

    try:
        phone = await set_owner_phone(db, payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "owner_phone": phone}


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
        .options(*_enquiry_load_options())
        .where(Enquiry.id == enquiry.id)
    )
    row = result.scalar_one()
    return _enquiry_to_out(row)


@router.post("/orders/import-excel/preview", response_model=OrderExcelPreviewOut)
async def preview_order_excel_import(file: UploadFile = File(...)) -> OrderExcelPreviewOut:
    filename = (file.filename or "order-import.xlsx").strip() or "order-import.xlsx"
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Upload an .xlsx file")
    try:
        parsed = parse_order_excel_bytes(await file.read(), filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this Excel file") from exc
    return OrderExcelPreviewOut(
        fileName=filename,
        layout=parsed["layout"],
        warnings=parsed.get("warnings") or [],
        order=parsed["order"],
    )


@router.post("/orders/import-excel", response_model=OrderExcelImportOut)
async def import_order_excel(
    payload: OrderExcelImportIn,
    db: AsyncSession = Depends(get_db),
) -> OrderExcelImportOut:
    try:
        enquiry, warnings = await import_normalized_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await db.execute(
        select(Enquiry)
        .options(*_enquiry_load_options())
        .where(Enquiry.id == enquiry.id)
    )
    row = result.scalar_one()
    return OrderExcelImportOut(
        mode=payload.mode,
        warnings=warnings,
        order=_enquiry_to_out(row),
    )


@router.get("/enquiries", response_model=list[EnquiryOut])
async def list_enquiries(db: AsyncSession = Depends(get_db)) -> list[EnquiryOut]:
    result = await db.execute(
        select(Enquiry)
        .options(*_enquiry_load_options())
        .order_by(Enquiry.createdAt.desc())
        .limit(100)
    )
    return [_enquiry_to_out(e) for e in result.scalars().all()]


@router.post("/enquiries/{enquiry_id}/retry-notification", response_model=EnquiryOut)
async def retry_owner_notification(enquiry_id: str, db: AsyncSession = Depends(get_db)) -> EnquiryOut:
    from app.services.enquiry_service import send_owner_lead_notification

    result = await db.execute(
        select(Enquiry).options(*_enquiry_load_options()).where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if (enquiry.notificationStatus or "") == "sent":
        return _enquiry_to_out(enquiry)
    enquiry.notificationStatus = "pending"
    await db.commit()
    await send_owner_lead_notification(db, enquiry, force=True)
    await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


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
        .options(*_enquiry_load_options())
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
        .options(*_enquiry_load_options())
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if payload.notes is not None:
        enquiry.notes = payload.notes
    if payload.customerName is not None:
        cleaned = payload.customerName.strip()
        if not cleaned:
            raise HTTPException(status_code=400, detail="Customer name cannot be empty")
        enquiry.customerName = cleaned
    await db.commit()
    await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


@router.delete("/enquiries/{enquiry_id}")
async def delete_enquiry(enquiry_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Permanently remove an order/enquiry and related menu, payments, docs, and assignments."""
    enquiry = await db.get(Enquiry, enquiry_id)
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")

    await db.execute(delete(EnquiryDish).where(EnquiryDish.enquiryId == enquiry_id))
    await db.execute(delete(EnquiryPayment).where(EnquiryPayment.enquiryId == enquiry_id))
    await db.execute(delete(InvoiceUpload).where(InvoiceUpload.enquiryId == enquiry_id))
    await db.execute(delete(WorkerAssignment).where(WorkerAssignment.enquiryId == enquiry_id))
    await db.execute(delete(Notification).where(Notification.enquiryId == enquiry_id))
    await db.delete(enquiry)
    await db.commit()
    return {"ok": True, "id": enquiry_id}


@router.post("/enquiries/{enquiry_id}/delivered", response_model=EnquiryOut)
async def mark_enquiry_delivered(
    enquiry_id: str,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    """Mark a converted order as delivered — dashboard will ask about payment."""
    result = await db.execute(
        select(Enquiry)
        .options(*_enquiry_load_options())
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if enquiry.status != EnquiryStatus.CONVERTED:
        raise HTTPException(status_code=400, detail="Only converted orders can be marked delivered")
    if enquiry.deliveredAt is None:
        enquiry.deliveredAt = datetime.now()
        await db.commit()
        await db.refresh(enquiry)
    return _enquiry_to_out(enquiry)


@router.patch("/enquiries/{enquiry_id}/payment", response_model=EnquiryOut)
async def confirm_enquiry_payment(
    enquiry_id: str,
    payload: EnquiryPaymentIn,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    """Record full/partial payment (optional discount). Revenue uses payment rows."""
    result = await db.execute(
        select(Enquiry)
        .options(*_enquiry_load_options())
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if enquiry.status != EnquiryStatus.CONVERTED:
        raise HTTPException(status_code=400, detail="Only converted orders can confirm payment")

    if payload.discountAmount is not None:
        enquiry.discountAmount = max(0.0, float(payload.discountAmount))

    dishes_result = await db.execute(select(Dish))
    menu_prices = {d.id: d.price for d in dishes_result.scalars().all()}
    billing, paid_so_far, _ = _enquiry_billing_figures(enquiry, menu_prices)
    remaining_before = max(0.0, billing - float(enquiry.discountAmount or 0) - paid_so_far)

    if payload.received is False and payload.amount is None:
        # Clear all payment progress (remove from revenue)
        for p in list(enquiry.payments or []):
            await db.delete(p)
        enquiry.paymentReceived = False
        await db.commit()
        result = await db.execute(
            select(Enquiry).options(*_enquiry_load_options()).where(Enquiry.id == enquiry_id)
        )
        return _enquiry_to_out(result.scalar_one(), menu_prices)

    installment: float | None
    if payload.amount is not None:
        try:
            installment = float(payload.amount)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid payment amount") from exc
    else:
        # Full remaining balance (or whole bill if nothing left calculated)
        installment = remaining_before if remaining_before > 0 else max(0.0, billing - float(enquiry.discountAmount or 0))

    if installment < 0:
        raise HTTPException(status_code=400, detail="Payment amount cannot be negative")

    # Always write a ledger row when confirming money received
    if installment <= 0 and remaining_before > 0:
        installment = remaining_before
    if installment <= 0 and billing > 0 and paid_so_far <= 0:
        installment = max(0.0, billing - float(enquiry.discountAmount or 0))

    if installment > 0:
        payment = EnquiryPayment(
            enquiryId=enquiry.id,
            amount=installment,
            payerName=(payload.payerName or "").strip() or enquiry.customerName,
            notes=(payload.notes or "").strip() or None,
            paidAt=datetime.now(),
        )
        db.add(payment)
        if enquiry.deliveredAt is None:
            enquiry.deliveredAt = datetime.now()
        await db.flush()
        # Ensure relationship is up to date in this session
        await db.refresh(enquiry, attribute_names=["payments"])
    elif payload.received:
        raise HTTPException(
            status_code=400,
            detail="Payment amount is 0 — set the order-copy totals or enter an amount",
        )

    billing, paid, due = _enquiry_billing_figures(enquiry, menu_prices)
    enquiry.paymentReceived = paid > 0 and due <= 0.009
    await db.commit()
    result = await db.execute(
        select(Enquiry).options(*_enquiry_load_options()).where(Enquiry.id == enquiry_id)
    )
    return _enquiry_to_out(result.scalar_one(), menu_prices)


@router.post("/enquiries/{enquiry_id}/viewed", response_model=EnquiryOut)
async def mark_enquiry_viewed(
    enquiry_id: str,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    result = await db.execute(
        select(Enquiry)
        .options(*_enquiry_load_options())
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
    _block_in_production()
    return await seed_excel_reference_orders(db, replace=True)


@router.post("/seed-demo")
async def seed_demo_dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    """Load demo enquiries, vendors, workers, expenses, and notifications."""
    _block_in_production()
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
