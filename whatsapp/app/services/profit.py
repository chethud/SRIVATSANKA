from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Dish, Enquiry, EnquiryDish, EnquiryStatus, InvoiceUpload


def line_price(item: EnquiryDish, menu_prices: dict[str, float]) -> float:
    unit = item.unitPrice if item.unitPrice is not None else menu_prices.get(item.dishId or "", 0)
    return unit * max(1, item.quantity or 1)


def order_amount(enquiry: Enquiry, menu_prices: dict[str, float]) -> float:
    line_sum = sum(line_price(d, menu_prices) for d in enquiry.dish_items)
    return line_sum * max(1, enquiry.guestCount)


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
    # Revenue only after owner confirms payment was received
    paid_orders = [e for e in converted if bool(getattr(e, "paymentReceived", False))]

    order_revenue = 0.0
    monthly_rev: dict[str, float] = defaultdict(float)
    revenue_items: list[dict] = []
    for e in paid_orders:
        rev = order_amount(e, menu_prices)
        order_revenue += rev
        mk = _month_key(e.eventDate)
        monthly_rev[mk] += rev
        if rev > 0:
            paid_dt = getattr(e, "deliveredAt", None) or e.eventDate
            revenue_items.append({
                "label": f"{e.customerName} – {e.eventType}",
                "amount": rev,
                "date": paid_dt.strftime("%d %b %Y"),
                "enquiryId": e.id,
                "source": "order",
            })

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

    # Newest revenue first
    revenue_items.sort(key=lambda x: x.get("date") or "", reverse=True)
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

    if not monthly and (order_revenue or order_expenses or uploaded_revenue):
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
        "paid_orders": len(paid_orders),
        "by_status": by_status,
        "by_event_type": by_event,
        "expense_items": expense_items,
        "profit_items": profit_items,
        "revenue_items": revenue_items,
        "monthly": monthly,
    }
