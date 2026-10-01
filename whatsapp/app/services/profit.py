from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Dish, Enquiry, EnquiryDish, EnquiryPayment, EnquiryStatus, InvoiceUpload
from app.services.order_billing import billing_total_from_notes


def line_price(item: EnquiryDish, menu_prices: dict[str, float]) -> float:
    unit = item.unitPrice if item.unitPrice is not None else menu_prices.get(item.dishId or "", 0)
    return unit * max(1, item.quantity or 1)


def order_amount(enquiry: Enquiry, menu_prices: dict[str, float]) -> float:
    """Prefer order-copy billing in notes (grand total / sessions + extras); fall back to dish × guests."""
    from_notes = billing_total_from_notes(enquiry.notes, getattr(enquiry, "dish_items", None))
    if from_notes is not None and from_notes > 0:
        return from_notes
    line_sum = sum(line_price(d, menu_prices) for d in (enquiry.dish_items or []))
    return line_sum * max(1, enquiry.guestCount)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%b %Y")


async def _backfill_missing_payment_rows(db: AsyncSession, converted: list[Enquiry]) -> None:
    """Create ledger rows for orders marked paid before EnquiryPayment existed."""
    created = False
    for e in converted:
        payments = list(getattr(e, "payments", None) or [])
        if payments:
            continue
        if not bool(getattr(e, "paymentReceived", False)):
            continue
        billing = order_amount(e, {})
        # Recompute with empty menu is fine — notes-based billing preferred
        discount = max(0.0, float(getattr(e, "discountAmount", 0) or 0))
        amt = max(0.0, billing - discount)
        if amt <= 0:
            continue
        db.add(
            EnquiryPayment(
                enquiryId=e.id,
                amount=amt,
                payerName=e.customerName,
                notes="Backfilled confirmed payment",
                paidAt=getattr(e, "deliveredAt", None) or e.eventDate or datetime.now(),
            )
        )
        created = True
    if created:
        await db.commit()
        for e in converted:
            await db.refresh(e, attribute_names=["payments"])


async def compute_profit_analytics(db: AsyncSession) -> dict:
    dishes_result = await db.execute(select(Dish))
    menu_prices = {d.id: d.price for d in dishes_result.scalars().all()}

    all_enquiries = list((await db.execute(select(Enquiry))).scalars().all())
    by_status: dict[str, int] = {}
    by_event: dict[str, int] = {}
    for e in all_enquiries:
        st = e.status.value if hasattr(e.status, "value") else str(e.status)
        by_status[st] = by_status.get(st, 0) + 1
        by_event[e.eventType] = by_event.get(e.eventType, 0) + 1

    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items), selectinload(Enquiry.payments))
        .where(Enquiry.status == EnquiryStatus.CONVERTED)
    )
    converted = list(result.scalars().all())
    await _backfill_missing_payment_rows(db, converted)

    # Reload payments after possible backfill
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items), selectinload(Enquiry.payments))
        .where(Enquiry.status == EnquiryStatus.CONVERTED)
    )
    converted = list(result.scalars().all())

    order_revenue = 0.0
    booked_order_value = 0.0
    monthly_rev: dict[str, float] = defaultdict(float)
    revenue_items: list[dict] = []

    for e in converted:
        billing = order_amount(e, menu_prices)
        discount = max(0.0, float(getattr(e, "discountAmount", 0) or 0))
        booked_order_value += max(0.0, billing - discount)

    for e in converted:
        payments = list(getattr(e, "payments", None) or [])
        paid_sum = sum(float(p.amount or 0) for p in payments)
        if paid_sum <= 0 and not bool(getattr(e, "paymentReceived", False)):
            continue

        # Prefer actual payment ledger; fall back to full order if legacy flag only
        if paid_sum > 0:
            rev = paid_sum
            for p in payments:
                amt = float(p.amount or 0)
                if amt <= 0:
                    continue
                paid_dt = p.paidAt or e.eventDate
                mk = _month_key(paid_dt)
                monthly_rev[mk] += amt
                payer = (p.payerName or e.customerName or "Customer").strip()
                revenue_items.append({
                    "label": f"{e.customerName} – {payer}",
                    "amount": amt,
                    "date": paid_dt.strftime("%d %b %Y"),
                    "enquiryId": e.id,
                    "source": "order",
                })
        else:
            billing = order_amount(e, menu_prices)
            discount = max(0.0, float(getattr(e, "discountAmount", 0) or 0))
            rev = max(0.0, billing - discount)
            mk = _month_key(e.eventDate)
            monthly_rev[mk] += rev
            if rev > 0:
                revenue_items.append({
                    "label": f"{e.customerName} – {e.eventType}",
                    "amount": rev,
                    "date": e.eventDate.strftime("%d %b %Y"),
                    "enquiryId": e.id,
                    "source": "order",
                })

        order_revenue += rev

    paid_orders = sum(1 for e in converted if bool(getattr(e, "paymentReceived", False)))

    uploads_result = await db.execute(
        select(InvoiceUpload).order_by(InvoiceUpload.createdAt.desc())
    )
    uploads = list(uploads_result.scalars().all())

    uploaded_revenue = 0.0
    order_expenses = 0.0
    expense_items: list[dict] = []
    profit_items: list[dict] = []
    monthly_exp: dict[str, float] = defaultdict(float)
    monthly_profit_upload: dict[str, float] = defaultdict(float)

    for u in uploads:
        amt = u.amount or 0
        bill_dt = u.expenseDate or u.createdAt
        mk = _month_key(bill_dt)
        label = (u.notes or u.purpose or u.fileName)[:40]
        date_str = bill_dt.strftime("%d %b %Y")
        if u.docType == "profit":
            uploaded_revenue += amt
            monthly_profit_upload[mk] += amt
            if amt > 0:
                item = {
                    "label": label,
                    "amount": amt,
                    "date": date_str,
                    "id": u.id,
                    "fileName": u.fileName,
                    "source": "upload",
                }
                profit_items.append(item)
                revenue_items.append(item)
        elif u.docType == "expense":
            order_expenses += amt
            monthly_exp[mk] += amt
            desc = (u.notes or "").strip() or (u.fileName or "Expense")
            expense_items.append({
                "id": u.id,
                "label": desc[:80],
                "amount": amt,
                "date": date_str,
                "purpose": (u.purpose or "").strip() or None,
                "fileName": u.fileName,
                "source": "upload",
            })

    revenue_items.sort(key=lambda x: x.get("date") or "", reverse=True)
    profit_items = profit_items[:8]

    # Revenue is order payments only (uploaded "profit" bills are not counted as revenue)
    all_months = sorted(
        set(monthly_rev) | set(monthly_exp),
        key=lambda m: datetime.strptime(m, "%b %Y"),
    )
    monthly = []
    for m in all_months[-6:]:
        rev = monthly_rev[m]
        exp = monthly_exp[m]
        monthly.append({"month": m, "revenue": rev, "expenses": exp, "profit": rev - exp})

    if not monthly and (order_revenue or order_expenses):
        now = _month_key(datetime.now())
        monthly = [{
            "month": now,
            "revenue": order_revenue,
            "expenses": order_expenses,
            "profit": order_revenue - order_expenses,
        }]

    total_expenses = order_expenses
    total_revenue = order_revenue
    net_profit = total_revenue - total_expenses

    return {
        "total_revenue": total_revenue,
        "order_revenue": order_revenue,
        "booked_order_value": booked_order_value,
        "uploaded_revenue": uploaded_revenue,
        "total_expenses": total_expenses,
        "global_expenses": 0.0,
        "order_expenses": order_expenses,
        "net_profit": net_profit,
        "converted_orders": len(converted),
        "paid_orders": paid_orders,
        "by_status": by_status,
        "by_event_type": by_event,
        "expense_items": expense_items,
        "profit_items": profit_items,
        "revenue_items": [i for i in revenue_items if i.get("source") == "order"],
        "monthly": monthly,
    }
