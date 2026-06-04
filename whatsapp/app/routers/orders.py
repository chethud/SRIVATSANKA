import shutil
from datetime import datetime
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
    InvoiceConfirmIn,
    InvoiceRecognizeOut,
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


def _parse_expense_date(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _save_uploaded_file(file: UploadFile, *, subdir: str = "") -> tuple[str, Path]:
    ext = Path(file.filename or "file").suffix.lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"):
        raise HTTPException(400, "Upload an image (JPG/PNG) or PDF")
    pending_id = uuid4().hex
    folder = UPLOAD_DIR / subdir if subdir else UPLOAD_DIR
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{pending_id}{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return pending_id, dest


def _invoice_upload_out(upload: InvoiceUpload, *, recognized: bool = True) -> InvoiceUploadOut:
    return InvoiceUploadOut(
        id=upload.id,
        enquiryId=upload.enquiryId,
        docType=upload.docType,
        fileName=upload.fileName,
        amount=upload.amount,
        notes=upload.notes,
        purpose=upload.purpose,
        expenseDate=upload.expenseDate,
        createdAt=upload.createdAt,
        recognized=recognized,
    )


@router.post("/invoices/recognize", response_model=InvoiceRecognizeOut)
async def recognize_expense_invoice(file: UploadFile = File(...)) -> InvoiceRecognizeOut:
    """Upload bill, run AI, return fields for owner review before saving."""
    pending_id, dest = _save_uploaded_file(file, subdir="pending")
    recognized = await recognize_bill(dest, expense_only=True)
    return InvoiceRecognizeOut(
        pendingId=pending_id,
        fileName=file.filename or dest.name,
        description=recognized.get("description") or recognized.get("notes"),
        expenseDate=recognized.get("expense_date"),
        amount=recognized.get("amount"),
        purpose=recognized.get("purpose"),
        recognized=bool(recognized.get("recognized")),
    )


@router.post("/invoices/confirm", response_model=InvoiceUploadOut)
async def confirm_expense_invoice(
    payload: InvoiceConfirmIn,
    db: AsyncSession = Depends(get_db),
) -> InvoiceUploadOut:
    """Save invoice after owner confirms or corrects recognized details."""
    pending_dir = UPLOAD_DIR / "pending"
    matches = list(pending_dir.glob(f"{payload.pendingId}.*")) if pending_dir.exists() else []
    if not matches:
        raise HTTPException(404, "Upload session expired — please upload the bill again")
    src = matches[0]
    ext = src.suffix
    final_name = f"expense_{uuid4().hex[:8]}{ext}"
    dest = UPLOAD_DIR / final_name
    shutil.move(str(src), str(dest))

    amount = payload.amount
    if amount is not None:
        try:
            amount = max(0.0, float(amount))
        except (TypeError, ValueError):
            amount = None

    upload = InvoiceUpload(
        enquiryId=None,
        docType="expense",
        fileName=src.name,
        filePath=str(dest),
        amount=amount,
        notes=(payload.description or "").strip() or None,
        purpose=(payload.purpose or "").strip() or None,
        expenseDate=_parse_expense_date(payload.expenseDate),
    )
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    return _invoice_upload_out(upload)


@router.delete("/invoices/pending/{pending_id}")
async def cancel_pending_invoice(pending_id: str) -> dict:
    pending_dir = UPLOAD_DIR / "pending"
    if pending_dir.exists():
        for path in pending_dir.glob(f"{pending_id}.*"):
            path.unlink(missing_ok=True)
    return {"ok": True}


@router.post("/invoices/upload", response_model=InvoiceUploadOut)
async def upload_expense_invoice(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> InvoiceUploadOut:
    """Legacy: recognize then save immediately (prefer /recognize + /confirm)."""
    preview = await recognize_expense_invoice(file)
    return await confirm_expense_invoice(
        InvoiceConfirmIn(
            pendingId=preview.pendingId,
            description=preview.description,
            expenseDate=preview.expenseDate,
            amount=preview.amount,
            purpose=preview.purpose,
        ),
        db=db,
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
