"""Four converted orders modeled on D:\\excel / scripts/samples/excel-refs workbooks."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Enquiry, EnquiryDish, EnquiryStatus

# Do NOT use "[demo]" — startup clear_demo_rows wipes every notes row containing that substring.
DEMO_MARKER = "[excel-ref]"


def _col(cid: str, date: str, label: str, base: str, pax: int | None, t0: str | None, t1: str | None, amount: int | None):
    return {
        "id": cid,
        "date": date,
        "sessionLabel": label,
        "baseSession": base,
        "pax": pax,
        "timeFrom": t0,
        "timeTo": t1,
        "amount": amount,
    }


def _extra(eid: str, title: str, description: str, quantity: str, amount: int | None):
    return {
        "id": eid,
        "title": title,
        "description": description,
        "quantity": quantity,
        "amount": amount,
        "enabled": True,
        "isCustom": True,
    }


def excel_reference_order_defs() -> list[dict]:
    # Naive UTC — Enquiry columns are TIMESTAMP WITHOUT TIME ZONE (asyncpg rejects tz-aware).
    now = datetime.utcnow()

    nithin_cols = [
        _col("n_bf_25", "2024-08-25", "Breakfast Plantain Leaf", "Breakfast", 25, "08:00", "11:00", 4000),
        _col("n_lunch_25", "2024-08-25", "Lunch", "Lunch", 150, "12:30", "15:00", 52500),
        _col("n_bf_27", "2024-08-27", "Breakfast Plantain Leaf", "Breakfast", 100, "08:00", "11:00", 15000),
        _col("n_lunch_27", "2024-08-27", "Lunch", "Lunch", 400, "12:30", "15:00", 120000),
        _col("n_snacks_27", "2024-08-27", "Snacks Buffet", "Snacks", 400, "16:30", "18:00", 60000),
        _col("n_dinner_27", "2024-08-27", "Dinner Plantain (No Garlic)", "Dinner", 550, "19:00", "21:30", 385000),
        _col("n_coffee_28", "2024-08-28", "Coffee Counter @6 AM", "Coffee", 60, "06:00", "07:00", 7500),
        _col("n_bf_28", "2024-08-28", "Breakfast Plantain Leaf", "Breakfast", 530, "07:30", "11:00", 106000),
        _col("n_lunch_28", "2024-08-28", "Lunch", "Lunch", 650, "12:30", "15:00", 312000),
        _col("n_juice_28", "2024-08-28", "Juice Counter", "Juice", 500, "10:30", "11:30", 40000),
    ]
    nithin_dishes = [
        ("Rava Idly", "Breakfast", "n_bf_25"),
        ("Saagu", "Breakfast", "n_bf_25"),
        ("Chutney", "Breakfast", "n_bf_25"),
        ("Gojju Avalakki", "Breakfast", "n_bf_25"),
        ("Ashoka Halwa", "Breakfast", "n_bf_25"),
        ("Hesarbele Carrot Kosambri", "Lunch", "n_lunch_25"),
        ("Rice Ghee Parappu", "Lunch", "n_lunch_25"),
        ("Mixed Veg Huli", "Lunch", "n_lunch_25"),
        ("Akki Thari coconut Upma", "Breakfast", "n_bf_27"),
        ("Chutney", "Breakfast", "n_bf_27"),
        ("Vade", "Breakfast", "n_bf_27"),
        ("Sambar", "Breakfast", "n_bf_27"),
        ("Corn Carrot Kosambri", "Lunch", "n_lunch_27"),
        ("Bisibelebath with Boondhi", "Lunch", "n_lunch_27"),
        ("Curd Rice", "Lunch", "n_lunch_27"),
        ("Assorted Bajji", "Snacks", "n_snacks_27"),
        ("Mangalore Bajji", "Snacks", "n_snacks_27"),
        ("Chutney", "Snacks", "n_snacks_27"),
        ("Tender Coconut Juice", "Dinner", "n_dinner_27"),
        ("Tomato Shorba", "Dinner", "n_dinner_27"),
        ("Malai Kofta", "Dinner", "n_dinner_27"),
        ("Rumali Roti", "Dinner", "n_dinner_27"),
        ("Coffee (Sugarless)", "Coffee", "n_coffee_28"),
        ("Thari Thatte Idly", "Breakfast", "n_bf_28"),
        ("Mulbhaglu Dose", "Breakfast", "n_bf_28"),
        ("Ven pongal (Tamil Style)", "Breakfast", "n_bf_28"),
        ("Hesarbele Carrot Kosambri", "Lunch", "n_lunch_28"),
        ("Pineapple Gojju", "Lunch", "n_lunch_28"),
        ("Puliyogare", "Lunch", "n_lunch_28"),
        ("Jigarthanda", "Juice", "n_juice_28"),
    ]

    mural_cols = [
        _col("m_packed_17", "2025-01-17", "Lunch for 18 pax Packed", "Lunch", 18, "12:30", "14:00", 2000),
        _col("m_snacks_17", "2025-01-17", "Snacks Counter", "Snacks", 50, "15:30", "17:00", 4000),
        _col("m_dinner_17", "2025-01-17", "Dinner Buffet", "Dinner", 100, "19:00", "20:30", 30000),
        _col("m_bf_18", "2025-01-18", "Breakfast Plantain Leaf", "Breakfast", 100, "08:00", "11:00", 18000),
        _col("m_snacks_18", "2025-01-18", "Snacks Buffet", "Snacks", 350, "16:30", "18:00", 42000),
        _col("m_dinner_18", "2025-01-18", "Dinner Plantain (No Garlic)", "Dinner", 550, "19:00", "21:30", 385000),
        _col("m_lunch_18", "2025-01-18", "Lunch", "Lunch", 275, "12:30", "15:00", 110000),
        _col("m_bf_19", "2025-01-19", "Breakfast Plantain Leaf", "Breakfast", 550, "07:30", "10:00", 137500),
        _col("m_snacks_19", "2025-01-19", "Snacks Buffet", "Snacks", 100, "15:30", "18:00", 8000),
        _col("m_lunch_19", "2025-01-19", "Lunch", "Lunch", 560, "11:00", "15:00", 280000),
        _col("m_dinner_19", "2025-01-19", "Dinner", "Dinner", 50, "19:30", "21:00", 15000),
    ]
    mural_dishes = [
        ("Kabul Usli", "Lunch", "m_packed_17"),
        ("Tomato Peas Bath", "Lunch", "m_packed_17"),
        ("Curd Rice", "Lunch", "m_packed_17"),
        ("Pulpy Watermelon", "Snacks", "m_snacks_17"),
        ("Veg Spring rollz", "Snacks", "m_snacks_17"),
        ("Sprouts carrot Kosambri", "Dinner", "m_dinner_17"),
        ("Phulka", "Dinner", "m_dinner_17"),
        ("Paneer Butter masala", "Dinner", "m_dinner_17"),
        ("Thari Idly", "Breakfast", "m_bf_18"),
        ("Vade", "Breakfast", "m_bf_18"),
        ("Sambar", "Breakfast", "m_bf_18"),
        ("Badam Halwa", "Snacks", "m_snacks_18"),
        ("Mangalore Bajji", "Snacks", "m_snacks_18"),
        ("Aloo Tikki", "Snacks", "m_snacks_18"),
        ("Pineapple Pudina Sharbath", "Dinner", "m_dinner_18"),
        ("Masala Puri", "Dinner", "m_dinner_18"),
        ("Tomato Shorba", "Dinner", "m_dinner_18"),
        ("Hesarbele Carrot Kosambri", "Lunch", "m_lunch_18"),
        ("Rice Ghee Parappu", "Lunch", "m_lunch_18"),
        ("Thatte Idly", "Breakfast", "m_bf_19"),
        ("Mulbhaglu Dose", "Breakfast", "m_bf_19"),
        ("Paddu", "Snacks", "m_snacks_19"),
        ("carrot halwa", "Snacks", "m_snacks_19"),
        ("Fruit Kosambri", "Lunch", "m_lunch_19"),
        ("Yengayi (Iyengar Style)", "Lunch", "m_lunch_19"),
        ("Mixed Dal Kosambri", "Dinner", "m_dinner_19"),
        ("chapathi", "Dinner", "m_dinner_19"),
    ]

    casa_cols = [
        _col("c_bf", "2024-05-03", "Breakfast for CG Vivacity", "Breakfast", 620, "08:00", "10:00", 155000),
        _col("c_lunch", "2024-05-03", "Lunch for CG Vivacity", "Lunch", 900, "12:30", "15:00", 256500),
        _col("c_roll", "2024-05-03", "Katti Rollz", "Snacks", 130, "16:00", "18:00", 19500),
        _col("c_bf_pack", "2024-05-02", "Breakfast Packed", "Breakfast", 120, "08:00", "09:00", 19200),
        _col("c_lunch_pack", "2024-05-02", "Lunch Packed", "Lunch", 160, "12:30", "14:00", 28800),
        _col("c_bf_a2b", "2024-05-06", "Breakfast A2B CG Vivacity", "Breakfast", 175, "08:00", "10:00", 28000),
        _col("c_nv_lunch", "2024-05-06", "Non Veg Lunch CG Vivacity", "Lunch", None, "12:30", "15:00", 75000),
        _col("c_coffee", "2024-05-04", "Coffee", "Coffee", 900, "10:00", "18:00", 18000),
        _col("c_tea", "2024-05-04", "Tea", "Tea", 900, "10:00", "18:00", 18000),
        _col("c_snacks", "2024-05-04", "Snacks for CG Vivacity", "Snacks", 750, "16:00", "18:00", 112500),
    ]
    casa_dishes = [
        ("Idly Sambar", "Breakfast", "c_bf"),
        ("Pongal", "Breakfast", "c_bf"),
        ("Coffee", "Breakfast", "c_bf"),
        ("Veg Meals", "Lunch", "c_lunch"),
        ("Rasam Rice", "Lunch", "c_lunch"),
        ("Curd Rice", "Lunch", "c_lunch"),
        ("Katti Roll", "Snacks", "c_roll"),
        ("Packed Breakfast Box", "Breakfast", "c_bf_pack"),
        ("Packed Lunch Box", "Lunch", "c_lunch_pack"),
        ("A2B Breakfast Set", "Breakfast", "c_bf_a2b"),
        ("50 KG Biryani", "Lunch", "c_nv_lunch"),
        ("25 KG Kabab", "Lunch", "c_nv_lunch"),
        ("Filter Coffee", "Coffee", "c_coffee"),
        ("Tea", "Tea", "c_tea"),
        ("Assorted Snacks", "Snacks", "c_snacks"),
    ]

    ra_cols = [
        _col("ra_event", "2024-05-16", "Catering Services for Client Event", "Lunch", 100, "12:00", "15:00", 50000),
    ]
    ra_dishes = [
        ("Event Meal Service", "Lunch", "ra_event"),
        ("Welcome Drink", "Lunch", "ra_event"),
        ("Dessert Counter", "Dessert", "ra_event"),
    ]

    return [
        {
            "customerName": "Nithin PG Wedding (Excel Ref)",
            "phoneNumber": "919999100001",
            "eventType": "Wedding",
            "eventDate": datetime(2024, 8, 27, 12, 0),
            "eventLocation": "Peacock Grove",
            "guestCount": 650,
            "preferredCallbackAt": now,
            "venueMapLink": "https://maps.app.goo.gl/peacockGroveDemo",
            "menuColumns": nithin_cols,
            "dishes": nithin_dishes,
            "scheduleDateFrom": "2024-08-25",
            "scheduleDateTo": "2024-08-28",
            "regionalStylesByDate": {
                "2024-08-25": "Karnataka style",
                "2024-08-27": "Tamil Nadu style",
                "2024-08-28": "Kerala style",
            },
            "extras": [
                _extra("e_kobri", "Kobri Design", "Traditional kobri work", "1", 2000),
                _extra("e_sweet", "Sweet Box", "Assorted sweets", "200 Box", 50000),
                _extra("e_thambula", "Thambula for Gents", "Thambula packs", "350 Pax", 35000),
                _extra("e_transport", "Transport and Cleaning", "Kitchen setup, transport, cleaning", "1", 1500),
            ],
            "ref": "Nithin Wedding PG Menu",
        },
        {
            "customerName": "Muralidharan Daughter Wedding (Excel Ref)",
            "phoneNumber": "919999100002",
            "eventType": "Wedding",
            "eventDate": datetime(2025, 1, 18, 12, 0),
            "eventLocation": "MLR Convention Center",
            "guestCount": 550,
            "preferredCallbackAt": now,
            "venueMapLink": "https://maps.app.goo.gl/mlrConventionDemo",
            "menuColumns": mural_cols,
            "dishes": mural_dishes,
            "scheduleDateFrom": "2025-01-17",
            "scheduleDateTo": "2025-01-19",
            "regionalStylesByDate": {
                "2025-01-17": "Karnataka style",
                "2025-01-18": "Tamil Nadu style",
                "2025-01-19": "Iyengar style",
            },
            "dietary": [
                "Bride Allergy to Vegan No Ghee or Dairy products",
                "Note: All items Onion No Garlic only",
            ],
            "extras": [
                _extra("e_sweet_m", "Sweet Box", "200 Box + 75 Box Groom / 400 Pax Bride", "275 Box", 80000),
                _extra("e_thambula_m", "Thambula", "18 Jan 550pax · 19 Jan 400pax", "950 Pax", 45000),
                _extra(
                    "e_garlands_m",
                    "Garlands",
                    "Day 1 & Day 2 garlands — 21 Plates for Groom · Bridal set",
                    "As listed",
                    None,
                ),
                _extra("e_transport_m", "Transport and Cleaning", "Setting up of Kitchen, Transport, Cleaning", "1", 5000),
            ],
            "ref": "Muralidharan Daughter Wedding Menu",
        },
        {
            "customerName": "Casagrand Vivacity (Excel Ref)",
            "phoneNumber": "919999100003",
            "eventType": "Corporate Event",
            "eventDate": datetime(2024, 5, 3, 9, 0),
            "eventLocation": "CG Vivacity / Usloor Lake, Bengaluru",
            "guestCount": 900,
            "preferredCallbackAt": now,
            "menuColumns": casa_cols,
            "dishes": casa_dishes,
            "scheduleDateFrom": "2024-05-02",
            "scheduleDateTo": "2024-05-06",
            "regionalStylesByDate": {
                "2024-05-02": "Karnataka style",
                "2024-05-03": "Karnataka style",
                "2024-05-06": "Tamil Nadu style",
            },
            "extras": [
                _extra("e_sweet_c", "Kanti Sweet Box", "3-4 May", "200", 50000),
                _extra("e_kaju_c", "Kanti Spl Kaju Sweet Box", "5-6 May", "250", 95000),
                _extra("e_transport_c", "Transport", "Event logistics", "1", 25000),
            ],
            "ref": "Casagrand Vivacity Sales Invoice",
        },
        {
            "customerName": "RA Hospitalities (Excel Ref)",
            "phoneNumber": "919999100004",
            "eventType": "Client Event",
            "eventDate": datetime(2024, 5, 16, 12, 0),
            "eventLocation": "Mandi Restaurant & Take-Away, 24th Main Road, Bengaluru",
            "guestCount": 100,
            "preferredCallbackAt": now,
            "menuColumns": ra_cols,
            "dishes": ra_dishes,
            "scheduleDateFrom": "2024-05-16",
            "scheduleDateTo": "2024-05-16",
            "regionalStylesByDate": {"2024-05-16": "Karnataka style"},
            "extras": [],
            "ref": "RA Hospitalities Sales Invoice",
        },
    ]


def _build_notes(order: dict, dish_columns: dict[str, str]) -> str:
    schedules: dict[str, dict] = {}
    for col in order["menuColumns"]:
        base = col["baseSession"]
        if base not in schedules and col.get("timeFrom"):
            schedules[base] = {"timeFrom": col["timeFrom"], "timeTo": col["timeTo"]}
    extras_list = order.get("extras") or []
    styles = order.get("regionalStylesByDate") or {}
    return json.dumps(
        {
            "_marker": DEMO_MARKER,
            "_excelRef": order["ref"],
            "dietary": order.get("dietary") or [],
            "liveCounters": [],
            "addOns": [],
            "scheduleDateFrom": order["scheduleDateFrom"],
            "scheduleDateTo": order["scheduleDateTo"],
            "mealSchedules": schedules,
            "menuColumns": order["menuColumns"],
            "dishColumns": dish_columns,
            "extrasEnabled": bool(extras_list),
            "extraItems": extras_list,
            "regionalStylesByDate": styles,
            "regionalStyles": list(dict.fromkeys(styles.values())),
            "regionalStyle": next(iter(styles.values()), None),
            "venueMapLink": order.get("venueMapLink") or None,
            "assignedWorkerIds": [],
            "dispatchPhase": "planned",
            "itemDispatch": {},
        }
    )


async def clear_excel_ref_orders(session: AsyncSession) -> int:
    result = await session.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.notes.contains(DEMO_MARKER))
    )
    rows = list(result.scalars().all())
    for enquiry in rows:
        await session.delete(enquiry)
    await session.commit()
    return len(rows)


async def excel_ref_order_count(session: AsyncSession) -> int:
    result = await session.execute(select(Enquiry.id).where(Enquiry.notes.contains(DEMO_MARKER)))
    return len(result.scalars().all())


async def ensure_excel_reference_orders(session: AsyncSession) -> dict:
    """Seed Excel-reference orders only when none exist (safe for every API restart)."""
    existing = await excel_ref_order_count(session)
    if existing > 0:
        return {"removed": 0, "created": 0, "orders": [], "marker": DEMO_MARKER, "skipped": True, "existing": existing}
    return await seed_excel_reference_orders(session, replace=False)


async def seed_excel_reference_orders(session: AsyncSession, *, replace: bool = True) -> dict:
    """Insert 4 CONVERTED orders matching the Excel reference workbooks."""
    removed = 0
    if replace:
        removed = await clear_excel_ref_orders(session)

    created: list[dict] = []
    for order in excel_reference_order_defs():
        enquiry = Enquiry(
            customerName=order["customerName"],
            phoneNumber=order["phoneNumber"],
            eventType=order["eventType"],
            eventDate=order["eventDate"],
            eventLocation=order["eventLocation"],
            guestCount=order["guestCount"],
            preferredCallbackAt=order["preferredCallbackAt"],
            status=EnquiryStatus.CONVERTED,
            notes=_build_notes(order, {}),
            ownerViewedAt=datetime.utcnow(),
        )
        session.add(enquiry)
        await session.flush()

        dish_columns: dict[str, str] = {}
        for name, category, column_id in order["dishes"]:
            item = EnquiryDish(
                enquiryId=enquiry.id,
                dishId=None,
                dishName=name,
                category=category,
                quantity=1.0,
                unitPrice=0.0,
                served=False,
            )
            session.add(item)
            await session.flush()
            dish_columns[item.id] = column_id

        enquiry.notes = _build_notes(order, dish_columns)
        created.append({"id": enquiry.id, "customerName": enquiry.customerName, "ref": order["ref"]})

    await session.commit()
    return {
        "removed": removed,
        "created": len(created),
        "orders": created,
        "marker": DEMO_MARKER,
    }
