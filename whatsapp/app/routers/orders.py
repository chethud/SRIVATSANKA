import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.seed_dishes import CATEGORY_LABELS
from app.database import get_db
from app.models import Dish, DishCategory, Enquiry, EnquiryDish, EnquiryStatus, InvoiceUpload
from app.schemas import (
    DishIn,
    DishOut,
    EnquiryDishOut,
    EnquiryOut,
    InvoiceUploadOut,
    OrderDishIn,
    OrderDishUpdate,
)
from app.services.bill_recognition import recognize_bill

router = APIRouter(prefix="/api", tags=["orders"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

LABEL_TO_CATEGORY: dict[str, DishCategory] = {v: k for k, v in CATEGORY_LABELS.items()}
LABEL_TO_CATEGORY.update({
    "South Indian": DishCategory.SOUTH_INDIAN,
    "North Indian": DishCategory.NORTH_INDIAN,
    "Chinese": DishCategory.CHINESE,
    "Snacks": DishCategory.SNACKS,
    "Desserts": DishCategory.DESSERTS,
    "Beverages": DishCategory.BEVERAGES,
})


def _dish_out(d: EnquiryDish) -> EnquiryDishOut:
    return EnquiryDishOut(
        id=d.id,
        dishId=d.dishId,
        dishName=d.dishName,
        category=d.category,
        customizations=d.customizations,
        notes=d.notes,
        quantity=d.quantity,
        unitPrice=d.unitPrice,
        served=d.served,
    )


def _enquiry_out(e: Enquiry) -> EnquiryOut:
    from app.routers.api import _enquiry_to_out

    return _enquiry_to_out(e)


async def _get_converted_enquiry(enquiry_id: str, db: AsyncSession) -> Enquiry:
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items))
        .where(Enquiry.id == enquiry_id)
    )
    enquiry = result.scalar_one_or_none()
    if not enquiry:
        raise HTTPException(404, "Order not found")
    if enquiry.status != EnquiryStatus.CONVERTED:
        raise HTTPException(400, "Dishes can only be managed on CONVERTED orders")
    return enquiry


@router.post("/dishes", response_model=DishOut)
async def create_dish(payload: DishIn, db: AsyncSession = Depends(get_db)) -> DishOut:
    cat = LABEL_TO_CATEGORY.get(payload.category)
    if not cat:
        try:
            cat = DishCategory(payload.category.upper().replace(" ", "_"))
        except ValueError as exc:
            raise HTTPException(400, "Invalid category") from exc

    dish = Dish(
        name=payload.name.strip(),
        category=cat,
        price=payload.price,
        description=payload.description,
        isActive=True,
    )
    db.add(dish)
    await db.commit()
    await db.refresh(dish)
    return DishOut(
        id=dish.id,
        name=dish.name,
        category=CATEGORY_LABELS.get(dish.category, str(dish.category)),
        price=dish.price,
        description=dish.description,
    )


@router.post("/enquiries/{enquiry_id}/dishes", response_model=EnquiryOut)
async def add_order_dish(
    enquiry_id: str,
    payload: OrderDishIn,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    enquiry = await _get_converted_enquiry(enquiry_id, db)
    menu = await db.get(Dish, payload.dishId)
    if not menu or not menu.isActive:
        raise HTTPException(404, "Dish not found in menu")

    item = EnquiryDish(
        enquiryId=enquiry.id,
        dishId=menu.id,
        dishName=menu.name,
        category=CATEGORY_LABELS.get(menu.category, str(menu.category)),
        customizations=payload.customizations,
        notes=payload.notes,
        quantity=max(1, payload.quantity),
        unitPrice=payload.unitPrice if payload.unitPrice is not None else menu.price,
        served=False,
    )
    db.add(item)
    await db.commit()
    await db.refresh(enquiry, ["dish_items"])
    return _enquiry_out(enquiry)


@router.patch("/enquiries/{enquiry_id}/dishes/{dish_item_id}", response_model=EnquiryOut)
async def update_order_dish(
    enquiry_id: str,
    dish_item_id: str,
    payload: OrderDishUpdate,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    enquiry = await _get_converted_enquiry(enquiry_id, db)
    item = next((d for d in enquiry.dish_items if d.id == dish_item_id), None)
    if not item:
        raise HTTPException(404, "Order dish not found")

    data = payload.model_dump(exclude_unset=True)
    for key, val in data.items():
        setattr(item, key, val)
    await db.commit()
    await db.refresh(enquiry, ["dish_items"])
    return _enquiry_out(enquiry)


@router.delete("/enquiries/{enquiry_id}/dishes/{dish_item_id}", response_model=EnquiryOut)
async def delete_order_dish(
    enquiry_id: str,
    dish_item_id: str,
    db: AsyncSession = Depends(get_db),
) -> EnquiryOut:
    enquiry = await _get_converted_enquiry(enquiry_id, db)
    item = next((d for d in enquiry.dish_items if d.id == dish_item_id), None)
    if not item:
        raise HTTPException(404, "Order dish not found")
    await db.delete(item)
    await db.commit()
    await db.refresh(enquiry, ["dish_items"])
    return _enquiry_out(enquiry)


@router.post("/invoices/upload", response_model=InvoiceUploadOut)
async def upload_expense_invoice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> InvoiceUploadOut:
    """Upload expense invoice — auto-recognized, feeds Analytics only (no order link)."""
    ext = Path(file.filename or "file").suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"):
        raise HTTPException(400, "Upload an image (JPG/PNG) or PDF")

    safe_name = f"expense_{uuid4().hex[:8]}{ext}"
    dest = UPLOAD_DIR / safe_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    recognized = await recognize_bill(dest, expense_only=True)
    upload = InvoiceUpload(
        enquiryId=None,
        docType="expense",
        fileName=file.filename or safe_name,
        filePath=str(dest),
        amount=recognized.get("amount"),
        notes=recognized.get("notes"),
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return InvoiceUploadOut(
        id=upload.id,
        enquiryId=None,
        docType=upload.docType,
        fileName=upload.fileName,
        amount=upload.amount,
        notes=upload.notes,
        createdAt=upload.createdAt,
        recognized=bool(recognized.get("recognized")),
    )


@router.get("/uploads/{upload_id}/file")
async def download_upload(upload_id: str, db: AsyncSession = Depends(get_db)) -> FileResponse:
    upload = await db.get(InvoiceUpload, upload_id)
    if not upload:
        raise HTTPException(404, "File not found")
    path = Path(upload.filePath)
    if not path.exists():
        raise HTTPException(404, "File missing on disk")
    return FileResponse(path, filename=upload.fileName)
