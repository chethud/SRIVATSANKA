"""Vendor categories and multi-phone helpers."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Vendor
from app.services.app_settings import get_setting, set_setting

DEFAULT_VENDOR_CATEGORIES = [
    "Marriage Halls",
    "Event Organizers",
    "Decorators",
    "Photographers",
    "DJs",
    "Vegetable Suppliers",
    "Rice Suppliers",
    "Transport Providers",
]

VENDOR_CATEGORIES_KEY = "vendor_categories"


def parse_vendor_phones(phone_number: str, phone_numbers_json: str | None) -> list[str]:
    if phone_numbers_json:
        try:
            data = json.loads(phone_numbers_json)
            if isinstance(data, list):
                phones = [str(p).strip() for p in data if str(p).strip()]
                if phones:
                    return phones
        except json.JSONDecodeError:
            pass
    primary = (phone_number or "").strip()
    return [primary] if primary else []


def serialize_vendor_phones(phones: list[str]) -> tuple[str, str]:
    cleaned = [p.strip() for p in phones if p and p.strip()]
    if not cleaned:
        raise ValueError("At least one phone number is required")
    return cleaned[0], json.dumps(cleaned)


async def list_vendor_category_names(db: AsyncSession) -> list[str]:
    names: set[str] = set(DEFAULT_VENDOR_CATEGORIES)
    raw = await get_setting(db, VENDOR_CATEGORIES_KEY)
    if raw:
        try:
            stored = json.loads(raw)
            if isinstance(stored, list):
                for item in stored:
                    label = str(item).strip()
                    if label:
                        names.add(label)
        except json.JSONDecodeError:
            pass
    result = await db.execute(select(Vendor.category).distinct())
    for (category,) in result.all():
        label = (category or "").strip()
        if label:
            names.add(label)
    return sorted(names, key=lambda s: s.lower())


async def add_vendor_category_name(db: AsyncSession, name: str) -> list[str]:
    label = (name or "").strip()
    if not label:
        raise ValueError("Category name cannot be empty")
    categories = await list_vendor_category_names(db)
    if label not in categories:
        custom = [c for c in categories if c not in DEFAULT_VENDOR_CATEGORIES]
        custom.append(label)
        custom = sorted(set(custom), key=lambda s: s.lower())
        await set_setting(db, VENDOR_CATEGORIES_KEY, json.dumps(custom))
        categories = await list_vendor_category_names(db)
    return categories
