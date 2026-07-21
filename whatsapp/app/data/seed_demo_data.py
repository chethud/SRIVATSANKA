"""Populate dashboard with realistic dummy data for UI testing."""

from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.seed_dishes import CATEGORY_LABELS, seed_dishes
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
    WorkerAssignment,
)

DEMO_MARKER = "[demo]"


def _dish_category_label(dish: Dish) -> str:
    from app.data.meal_sessions import dish_category_label

    return dish_category_label(dish.category)


async def _load_all_dishes(session: AsyncSession) -> list[Dish]:
    dishes = list((await session.execute(select(Dish).order_by(Dish.name))).scalars().all())
    if not dishes:
        await seed_dishes(session)
        dishes = list((await session.execute(select(Dish).order_by(Dish.name))).scalars().all())
    return dishes


def _add_order_lines(
    session: AsyncSession,
    enquiry_id: str,
    dishes: list[Dish],
    mode: bool | str,
) -> int:
    if mode == "all":
        subset = dishes
    elif mode == "sample":
        subset = dishes[:10]
    elif mode:
        subset = dishes[:6]
    else:
        return 0
    for i, dish in enumerate(subset):
        session.add(
            EnquiryDish(
                enquiryId=enquiry_id,
                dishId=dish.id,
                dishName=dish.name,
                category=_dish_category_label(dish),
                quantity=1 + (i % 3),
                unitPrice=dish.price,
            )
        )
    return len(subset)


async def clear_demo_rows(session: AsyncSession) -> dict:
    """Remove all rows marked as demo. Leaves dish catalog and real data intact."""
    demo_enquiries = (
        await session.execute(
            select(Enquiry.id).where(Enquiry.notes.isnot(None)).where(Enquiry.notes.contains(DEMO_MARKER))
        )
    ).scalars().all()
    if demo_enquiries:
        await session.execute(delete(EnquiryDish).where(EnquiryDish.enquiryId.in_(demo_enquiries)))
        await session.execute(delete(InvoiceUpload).where(InvoiceUpload.enquiryId.in_(demo_enquiries)))
        await session.execute(delete(WorkerAssignment).where(WorkerAssignment.enquiryId.in_(demo_enquiries)))
        await session.execute(delete(Enquiry).where(Enquiry.id.in_(demo_enquiries)))

    demo_worker_ids = (
        await session.execute(select(Worker.id).where(Worker.role.contains(DEMO_MARKER)))
    ).scalars().all()
    if demo_worker_ids:
        await session.execute(delete(WorkerAssignment).where(WorkerAssignment.workerId.in_(demo_worker_ids)))

    notif = await session.execute(delete(Notification).where(Notification.message.contains(DEMO_MARKER)))
    vendor = await session.execute(delete(Vendor).where(Vendor.notes.contains(DEMO_MARKER)))
    worker = await session.execute(delete(Worker).where(Worker.role.contains(DEMO_MARKER)))
    expense = await session.execute(delete(Expense).where(Expense.description.contains(DEMO_MARKER)))
    await session.execute(
        delete(InvoiceUpload).where(
            InvoiceUpload.notes.isnot(None),
            InvoiceUpload.notes.contains(DEMO_MARKER),
        )
    )
    await session.commit()
    return {
        "enquiriesRemoved": len(demo_enquiries),
        "notificationsRemoved": notif.rowcount or 0,
        "vendorsRemoved": vendor.rowcount or 0,
        "workersRemoved": worker.rowcount or 0,
        "expensesRemoved": expense.rowcount or 0,
        "marker": DEMO_MARKER,
    }


async def seed_demo_data(session: AsyncSession, *, force: bool = True) -> dict:
    """Insert dummy enquiries, orders, vendors, workers, expenses, notifications."""
    if force:
        await clear_demo_rows(session)

    dishes = await _load_all_dishes(session)
    now = datetime.now()
    enquiries_data = [
        {
            "customerName": "Demo: Kazin Kumar",
            "phoneNumber": "919900112233",
            "eventType": "Wedding",
            "eventDate": now + timedelta(days=30),
            "eventLocation": "Palace Grounds, Bengaluru",
            "guestCount": 500,
            "preferredCallbackAt": now - timedelta(days=2),
            "status": EnquiryStatus.CONVERTED,
            "cuisines": [
                "Multi Cuisine",
                "South Indian",
                "North Indian",
                "Chinese",
                "Snacks",
                "Desserts",
                "Beverages",
            ],
            "order_dishes": "all",
        },
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
            "order_dishes": "sample",
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
        {
            "customerName": "Demo: Sunitha Nair",
            "phoneNumber": "918877665544",
            "eventType": "Birthday",
            "eventDate": now - timedelta(days=14),
            "eventLocation": "Koramangala, Bengaluru",
            "guestCount": 40,
            "preferredCallbackAt": now - timedelta(days=20),
            "status": EnquiryStatus.NOT_CONVERTED,
            "cuisines": ["Snacks", "Desserts"],
        },
    ]

    created_enquiries = 0
    menu_lines = 0
    kazin_enquiry_id: str | None = None
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

        if "Kazin" in row["customerName"]:
            kazin_enquiry_id = enquiry.id

        for label in row.get("cuisines", []):
            session.add(
                EnquiryDish(
                    enquiryId=enquiry.id,
                    dishName=label,
                    category="Cuisine Preference",
                )
            )

        if row.get("order_dishes") and dishes:
            menu_lines += _add_order_lines(session, enquiry.id, dishes, row["order_dishes"])

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

    workers_data = [
        ("Demo: Ravi", "918004445566", "Head Chef", 1200),
        ("Demo: Lakshmi", "918005556677", "Service Lead", 900),
        ("Demo: Kumar", "918006667788", "Helper", 600),
    ]
    created_workers: list[Worker] = []
    for name, phone, role, wage in workers_data:
        worker = Worker(
            name=name,
            phoneNumber=phone,
            role=f"{role} {DEMO_MARKER}",
            dailyWage=wage,
        )
        session.add(worker)
        created_workers.append(worker)
    await session.flush()

    assignments_created = 0
    if kazin_enquiry_id and created_workers:
        duty_specs = [
            (created_workers[0], "Kitchen", 1800),
            (created_workers[1], "Service", 1200),
            (created_workers[2], "Setup & breakdown", 800),
        ]
        for worker, duty_type, wage in duty_specs:
            session.add(
                WorkerAssignment(
                    workerId=worker.id,
                    enquiryId=kazin_enquiry_id,
                    dutyDate=now + timedelta(days=28),
                    dutyType=duty_type,
                    wage=wage,
                )
            )
            assignments_created += 1

    expenses = [
        ("Transport", 4500, "Demo veg delivery runs"),
        ("Gas & fuel", 2800, "Demo kitchen fuel"),
        ("Packaging", 1500, "Demo biodegradable boxes"),
        ("Wages", 3800, "Demo event crew payout"),
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
                fileName="demo-events-bill.pdf",
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
        "menuLines": menu_lines,
        "dishesInCatalog": len(dishes),
        "vendors": len(vendors),
        "workers": len(workers_data),
        "workerAssignments": assignments_created,
        "expenses": len(expenses),
        "marker": DEMO_MARKER,
    }
