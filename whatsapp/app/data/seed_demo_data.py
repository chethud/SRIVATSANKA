"""Populate dashboard with realistic dummy data for UI testing."""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Dish,
    Enquiry,
    EnquiryDish,
    EnquiryStatus,
    Expense,
    InvoiceUpload,
    Notification,
    NotificationType,
    Vendor,
    Worker,
)

DEMO_MARKER = "[demo]"


async def _clear_demo_rows(session: AsyncSession) -> None:
    demo_enquiries = (
        await session.execute(
            select(Enquiry.id).where(Enquiry.notes.isnot(None)).where(Enquiry.notes.contains(DEMO_MARKER))
        )
    ).scalars().all()
    if demo_enquiries:
        await session.execute(delete(EnquiryDish).where(EnquiryDish.enquiryId.in_(demo_enquiries)))
        await session.execute(delete(InvoiceUpload).where(InvoiceUpload.enquiryId.in_(demo_enquiries)))
        await session.execute(delete(Enquiry).where(Enquiry.id.in_(demo_enquiries)))

    await session.execute(delete(Notification).where(Notification.message.contains(DEMO_MARKER)))
    await session.execute(delete(Vendor).where(Vendor.notes.contains(DEMO_MARKER)))
    await session.execute(delete(Worker).where(Worker.role.contains(DEMO_MARKER)))
    await session.execute(delete(Expense).where(Expense.description.contains(DEMO_MARKER)))
    await session.commit()


async def seed_demo_data(session: AsyncSession, *, force: bool = True) -> dict:
    """Insert dummy enquiries, orders, vendors, workers, expenses, notifications."""
    if force:
        await _clear_demo_rows(session)

    dishes = list((await session.execute(select(Dish).limit(8))).scalars().all())
    if not dishes:
        from app.data.seed_dishes import seed_dishes

        await seed_dishes(session)
        dishes = list((await session.execute(select(Dish).limit(8))).scalars().all())

    now = datetime.now()
    enquiries_data = [
        {
            "customerName": "Demo: Priya Sharma",
            "phoneNumber": "919876543210",
            "eventType": "Wedding",
            "eventDate": now + timedelta(days=45),
            "eventLocation": "Jayanagar, Bengaluru",
            "guestCount": 350,
            "preferredCallbackAt": now + timedelta(hours=4),
            "status": EnquiryStatus.NEW,
            "cuisines": ["Multi Cuisine", "South Indian"],
        },
        {
            "customerName": "Demo: Rajesh Kumar",
            "phoneNumber": "919988776655",
            "eventType": "House Warming",
            "eventDate": now + timedelta(days=12),
            "eventLocation": "Whitefield, Bengaluru",
            "guestCount": 80,
            "preferredCallbackAt": now + timedelta(days=1),
            "status": EnquiryStatus.CONTACTED,
            "cuisines": ["North Indian", "Snacks & Starters"],
        },
        {
            "customerName": "Demo: Ananya Reddy",
            "phoneNumber": "917700112233",
            "eventType": "Baby Shower",
            "eventDate": now + timedelta(days=28),
            "eventLocation": "Indiranagar, Bengaluru",
            "guestCount": 120,
            "preferredCallbackAt": now + timedelta(hours=2),
            "status": EnquiryStatus.CONVERTED,
            "cuisines": ["South Indian", "Desserts"],
            "order_dishes": True,
        },
        {
            "customerName": "Demo: Vikram & Meera",
            "phoneNumber": "916655443322",
            "eventType": "Reception",
            "eventDate": now - timedelta(days=5),
            "eventLocation": "MG Road, Bengaluru",
            "guestCount": 200,
            "preferredCallbackAt": now - timedelta(days=7),
            "status": EnquiryStatus.CONVERTED,
            "cuisines": ["Multi Cuisine", "Chinese", "Beverages"],
            "order_dishes": True,
        },
        {
            "customerName": "Demo: Corporate — TechPark",
            "phoneNumber": "914433221100",
            "eventType": "Corporate Lunch",
            "eventDate": now + timedelta(days=3),
            "eventLocation": "Electronic City, Bengaluru",
            "guestCount": 60,
            "preferredCallbackAt": now + timedelta(hours=6),
            "status": EnquiryStatus.NEW,
            "cuisines": [],
        },
    ]

    created_enquiries = 0
    for row in enquiries_data:
        enquiry = Enquiry(
            customerName=row["customerName"],
            phoneNumber=row["phoneNumber"],
            eventType=row["eventType"],
            eventDate=row["eventDate"],
            eventLocation=row["eventLocation"],
            guestCount=row["guestCount"],
            preferredCallbackAt=row["preferredCallbackAt"],
            status=row["status"],
            notes=f"Cuisine preferences via demo seed {DEMO_MARKER}",
        )
        session.add(enquiry)
        await session.flush()

        for label in row.get("cuisines", []):
            session.add(
                EnquiryDish(
                    enquiryId=enquiry.id,
                    dishName=label,
                    category="Cuisine Preference",
                )
            )

        if row.get("order_dishes") and dishes:
            for i, dish in enumerate(dishes[:4]):
                session.add(
                    EnquiryDish(
                        enquiryId=enquiry.id,
                        dishId=dish.id,
                        dishName=dish.name,
                        category=dish.category.value if hasattr(dish.category, "value") else str(dish.category),
                        quantity=1 + (i % 2),
                        unitPrice=dish.price,
                    )
                )

        session.add(
            Notification(
                type=NotificationType.NEW_ENQUIRY,
                title="Demo enquiry",
                message=f"{enquiry.customerName} – {enquiry.eventType} {DEMO_MARKER}",
                read=row["status"] != EnquiryStatus.NEW,
            )
        )
        created_enquiries += 1

    vendors = [
        ("Fresh Greens Mart", "Fresh Greens Pvt Ltd", "918001112233", "Vegetables"),
        ("Spice House", "Spice House Traders", "918002223344", "Spices"),
        ("EcoServe Rentals", "EcoServe", "918003334455", "Equipment"),
    ]
    for name, business, phone, category in vendors:
        session.add(
            Vendor(
                name=name,
                businessName=business,
                phoneNumber=phone,
                category=category,
                notes=f"Demo vendor {DEMO_MARKER}",
            )
        )

    workers = [
        ("Demo: Ravi", "918004445566", "Head Chef", 1200),
        ("Demo: Lakshmi", "918005556677", "Service Lead", 900),
        ("Demo: Kumar", "918006667788", "Helper", 600),
    ]
    for name, phone, role, wage in workers:
        session.add(
            Worker(
                name=name,
                phoneNumber=phone,
                role=f"{role} {DEMO_MARKER}",
                dailyWage=wage,
            )
        )

    expenses = [
        ("Transport", 4500, "Demo veg delivery runs"),
        ("Gas & fuel", 2800, "Demo kitchen fuel"),
        ("Packaging", 1500, "Demo biodegradable boxes"),
    ]
    for category, amount, desc in expenses:
        session.add(
            Expense(
                category=category,
                amount=amount,
                description=f"{desc} {DEMO_MARKER}",
                expenseDate=now - timedelta(days=10),
            )
        )

    converted_ids = [
        e.id
        for e in (
            await session.execute(
                select(Enquiry).where(Enquiry.notes.contains(DEMO_MARKER)).where(Enquiry.status == EnquiryStatus.CONVERTED)
            )
        ).scalars().all()
    ]
    if converted_ids:
        session.add(
            InvoiceUpload(
                enquiryId=converted_ids[0],
                docType="expense",
                fileName="demo-catering-bill.pdf",
                filePath="/uploads/demo-expense.pdf",
                amount=18500,
                notes=f"Demo supplier invoice {DEMO_MARKER}",
            )
        )
        session.add(
            InvoiceUpload(
                enquiryId=converted_ids[-1],
                docType="profit",
                fileName="demo-client-payment.pdf",
                filePath="/uploads/demo-profit.pdf",
                amount=42000,
                notes=f"Demo client advance {DEMO_MARKER}",
            )
        )

    await session.commit()
    return {
        "enquiries": created_enquiries,
        "vendors": len(vendors),
        "workers": len(workers),
        "expenses": len(expenses),
        "marker": DEMO_MARKER,
    }
