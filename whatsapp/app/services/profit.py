from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Dish, Enquiry, EnquiryDish, EnquiryStatus, InvoiceUpload


def line_price(item: EnquiryDish, menu_prices: dict[str, float]) -> float:
    unit = item.unitPrice if item.unitPrice is not None else menu_prices.get(item.dishId or "", 0)
    return unit * max(1, item.quantity or 1)


def _month_key(dt: datetime) -> str:
    return dt.strftime("%b %Y")


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
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.status == EnquiryStatus.CONVERTED)
    )
    converted = list(result.scalars().all())

    order_revenue = 0.0
    monthly_rev: dict[str, float] = defaultdict(float)
    for e in converted:
        line_sum = sum(line_price(d, menu_prices) for d in e.dish_items)
        rev = line_sum * max(1, e.guestCount)
        order_revenue += rev
        mk = _month_key(e.eventDate)
        monthly_rev[mk] += rev

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
                profit_items.append({"label": label, "amount": amt, "date": date_str})
        elif u.docType == "expense":
            order_expenses += amt
            monthly_exp[mk] += amt
            desc = (u.notes or "").strip() or (u.fileName or "Expense")
            expense_items.append({
                "label": desc[:80],
                "amount": amt,
                "date": date_str,
                "purpose": (u.purpose or "").strip() or None,
            })
    profit_items = profit_items[:8]

    all_months = sorted(
        set(monthly_rev) | set(monthly_exp) | set(monthly_profit_upload),
        key=lambda m: datetime.strptime(m, "%b %Y"),
    )
    monthly = []
    for m in all_months[-6:]:
        rev = monthly_rev[m] + monthly_profit_upload[m]
        exp = monthly_exp[m]
        monthly.append({"month": m, "revenue": rev, "expenses": exp, "profit": rev - exp})

    if not monthly and (order_revenue or order_expenses):
        now = _month_key(datetime.now())
        monthly = [{
            "month": now,
            "revenue": order_revenue + uploaded_revenue,
            "expenses": order_expenses,
            "profit": (order_revenue + uploaded_revenue) - order_expenses,
        }]

    total_expenses = order_expenses
    total_revenue = order_revenue + uploaded_revenue
    net_profit = total_revenue - total_expenses

    return {
        "total_revenue": total_revenue,
        "order_revenue": order_revenue,
        "uploaded_revenue": uploaded_revenue,
        "total_expenses": total_expenses,
        "global_expenses": 0.0,
        "order_expenses": order_expenses,
        "net_profit": net_profit,
        "converted_orders": len(converted),
        "by_status": by_status,
        "by_event_type": by_event,
        "expense_items": expense_items,
        "profit_items": profit_items,
        "monthly": monthly,
    }
