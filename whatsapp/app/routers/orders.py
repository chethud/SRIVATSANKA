import json
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.data.meal_sessions import (
    MEAL_SESSION_LABELS,
    dish_category_label,
    normalize_meal_session_label,
)
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
from app.quantity_units import normalize_quantity, normalize_quantity_unit
from app.services.bill_recognition import recognize_bill

router = APIRouter(prefix="/api", tags=["orders"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _dish_out(d: EnquiryDish) -> EnquiryDishOut:
    return EnquiryDishOut(
        id=d.id,
        dishId=d.dishId,
        dishName=d.dishName,
        category=d.category,
        customizations=d.customizations,
        notes=d.notes,
        quantity=normalize_quantity(d.quantity),
        quantityUnit=normalize_quantity_unit(getattr(d, "quantityUnit", None)),
        unitPrice=d.unitPrice,
        served=d.served,
    )


def _enquiry_out(e: Enquiry) -> EnquiryOut:
    from app.routers.api import _enquiry_to_out

    return _enquiry_to_out(e)


async def _get_converted_enquiry(enquiry_id: str, db: AsyncSession) -> Enquiry:
    result = await db.execute(
        select(Enquiry)
        .options(selectinload(Enquiry.dish_items), selectinload(Enquiry.payments))
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
    label = normalize_meal_session_label(payload.category)
    if not label:
        raise HTTPException(400, "Invalid meal session — use Breakfast, Lunch, or a custom name")

    dish = Dish(
        name=payload.name.strip(),
        category=label,
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
        category=dish_category_label(dish.category),
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

    if payload.category:
        session_label = normalize_meal_session_label(payload.category)
        if not session_label:
            raise HTTPException(400, "Invalid meal session")
    else:
        session_label = MEAL_SESSION_LABELS[DishCategory.LUNCH]

    if payload.dishId:
        menu = await db.get(Dish, payload.dishId)
        if not menu or not menu.isActive:
            raise HTTPException(404, "Dish not found in menu")
        if not payload.category:
            session_label = dish_category_label(menu.category)
        item = EnquiryDish(
            enquiryId=enquiry.id,
            dishId=menu.id,
            dishName=menu.name,
            category=session_label,
            customizations=payload.customizations,
            notes=payload.notes,
            quantity=normalize_quantity(payload.quantity),
            quantityUnit=normalize_quantity_unit(payload.quantityUnit),
            unitPrice=0.0 if payload.unitPrice is None else payload.unitPrice,
            served=False,
        )
    else:
        name = (payload.dishName or "").strip()
        if not name:
            raise HTTPException(400, "Dish name is required")

        if not payload.saveToCatalog:
            item = EnquiryDish(
                enquiryId=enquiry.id,
                dishId=None,
                dishName=name,
                category=session_label,
                customizations=payload.customizations,
                notes=payload.notes,
                quantity=normalize_quantity(payload.quantity),
                quantityUnit=normalize_quantity_unit(payload.quantityUnit),
                unitPrice=0.0 if payload.unitPrice is None else payload.unitPrice,
                served=False,
            )
        else:
            result = await db.execute(
                select(Dish).where(Dish.isActive.is_(True)).where(Dish.name.ilike(name))
            )
            menu = result.scalar_one_or_none()
            if not menu:
                menu = Dish(
                    name=name,
                    category=session_label,
                    price=0.0,
                    description="Added from order menu",
                    isActive=True,
                )
                db.add(menu)
                await db.flush()
            item = EnquiryDish(
                enquiryId=enquiry.id,
                dishId=menu.id,
                dishName=menu.name,
                category=session_label,
                customizations=payload.customizations,
                notes=payload.notes,
                quantity=normalize_quantity(payload.quantity),
                quantityUnit=normalize_quantity_unit(payload.quantityUnit),
                unitPrice=0.0 if payload.unitPrice is None else payload.unitPrice,
                served=False,
            )

    db.add(item)
    await db.flush()

    column_id = (payload.menuColumnId or "").strip()
    if column_id:
        try:
            notes_data = json.loads(enquiry.notes) if enquiry.notes else {}
        except Exception:
            notes_data = {}
        if not isinstance(notes_data, dict):
            notes_data = {}
        dish_columns = notes_data.get("dishColumns")
        if not isinstance(dish_columns, dict):
            dish_columns = {}
        dish_columns[item.id] = column_id
        notes_data["dishColumns"] = dish_columns
        enquiry.notes = json.dumps(notes_data)

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
    if "category" in data and data["category"] is not None:
        session_label = normalize_meal_session_label(data["category"])
        if not session_label:
            raise HTTPException(400, "Invalid meal session")
        data["category"] = session_label
    if "quantity" in data:
        data["quantity"] = normalize_quantity(data["quantity"])
    if "quantityUnit" in data:
        data["quantityUnit"] = normalize_quantity_unit(data["quantityUnit"])
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


_MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}


def _pending_meta_path(pending_id: str) -> Path:
    return UPLOAD_DIR / "pending" / f"{pending_id}.meta.json"


def _find_pending_media(pending_id: str) -> Path | None:
    """Return the uploaded bill file — never the .meta.json sidecar."""
    pending_dir = UPLOAD_DIR / "pending"
    if not pending_dir.exists():
        return None
    for path in pending_dir.glob(f"{pending_id}.*"):
        name = path.name.lower()
        if name.endswith(".meta.json"):
            continue
        if path.suffix.lower() in _MEDIA_EXTS:
            return path
    return None


def _save_uploaded_file(file: UploadFile, *, subdir: str = "") -> tuple[str, Path]:
    ext = Path(file.filename or "file").suffix.lower() or ".jpg"
    if ext not in _MEDIA_EXTS:
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
    import json

    meta_path = _pending_meta_path(pending_id)
    meta_path.write_text(
        json.dumps({"fileName": file.filename or dest.name, "pendingId": pending_id}),
        encoding="utf-8",
    )
    recognized = await recognize_bill(dest, expense_only=True)
    ok = bool(recognized.get("recognized"))
    return InvoiceRecognizeOut(
        pendingId=pending_id,
        fileName=file.filename or dest.name,
        description=recognized.get("description") if ok else None,
        expenseDate=recognized.get("expense_date"),
        amount=recognized.get("amount"),
        purpose=recognized.get("purpose"),
        recognized=ok,
        message=None if ok else (recognized.get("notes") or "Could not read this bill."),
    )


@router.post("/invoices/confirm", response_model=InvoiceUploadOut)
async def confirm_expense_invoice(
    payload: InvoiceConfirmIn,
    db: AsyncSession = Depends(get_db),
) -> InvoiceUploadOut:
    """Save invoice after owner confirms or corrects recognized details."""
    src = _find_pending_media(payload.pendingId)
    if not src:
        raise HTTPException(404, "Upload session expired — please upload the bill again")

    meta_path = _pending_meta_path(payload.pendingId)
    display_name = src.name
    if meta_path.exists():
        try:
            import json

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            display_name = meta.get("fileName") or display_name
        except Exception:
            pass

    ext = src.suffix.lower()
    final_name = f"expense_{uuid4().hex[:8]}{ext}"
    dest = UPLOAD_DIR / final_name
    shutil.move(str(src), str(dest))
    meta_path.unlink(missing_ok=True)

    amount = payload.amount
    if amount is not None:
        try:
            amount = max(0.0, float(amount))
        except (TypeError, ValueError):
            amount = None

    upload = InvoiceUpload(
        enquiryId=None,
        docType="expense",
        fileName=display_name,
        filePath=str(dest),
        fileData=dest.read_bytes() if dest.exists() else None,
        amount=amount,
        notes=(payload.description or "").strip() or None,
        purpose=(payload.purpose or "").strip() or None,
        expenseDate=_parse_expense_date(payload.expenseDate),
    )
    try:
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
    except Exception as exc:
        await db.rollback()
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise HTTPException(500, f"Could not save invoice: {exc}") from exc
    return _invoice_upload_out(upload)


@router.delete("/invoices/pending/{pending_id}")
async def cancel_pending_invoice(pending_id: str) -> dict:
    pending_dir = UPLOAD_DIR / "pending"
    if pending_dir.exists():
        for path in pending_dir.glob(f"{pending_id}.*"):
            path.unlink(missing_ok=True)
        _pending_meta_path(pending_id).unlink(missing_ok=True)
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


def _guess_media_type(file_name: str) -> str:
    lower = (file_name or "").lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith((".png",)):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".gif"):
        return "image/gif"
    return "application/octet-stream"


def _sniff_media_type(data: bytes) -> str | None:
    if data[:4] == b"%PDF":
        return "application/pdf"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _looks_like_meta_json(data: bytes | None, file_name: str | None, file_path: str | None) -> bool:
    name = (file_name or "").lower()
    path = (file_path or "").lower()
    if name.endswith(".meta.json") or path.endswith(".meta.json"):
        return True
    if not data:
        return False
    sample = bytes(data[:200]).lstrip()
    return sample.startswith(b"{") and b"pendingId" in sample


def _recover_bill_from_meta(upload: InvoiceUpload, data: bytes | None) -> tuple[bytes, str] | None:
    """If a .meta.json sidecar was saved by mistake, recover the real bill when possible."""
    import json

    pending_id = None
    original_name = None
    if data:
        try:
            meta = json.loads(bytes(data).decode("utf-8"))
            pending_id = meta.get("pendingId")
            original_name = meta.get("fileName")
        except Exception:
            pass

    if not pending_id:
        for candidate in (upload.fileName, upload.filePath):
            stem = Path(candidate or "").name
            if stem.endswith(".meta.json"):
                pending_id = stem[: -len(".meta.json")]
                break

    if not pending_id:
        return None

    media = _find_pending_media(pending_id)
    if media and media.exists():
        return media.read_bytes(), original_name or media.name

    # Already-moved expense_* file next to a wrongly saved .json/.meta.json path
    path = Path(upload.filePath) if upload.filePath else None
    if path:
        for sibling in path.parent.glob(f"*{pending_id[:8]}*"):
            if sibling.suffix.lower() in _MEDIA_EXTS and sibling.exists():
                return sibling.read_bytes(), original_name or sibling.name

    return None


@router.get("/uploads/{upload_id}/file")
async def download_upload(upload_id: str, db: AsyncSession = Depends(get_db)):
    """Serve uploaded bill from DB bytes (preferred) or disk path."""
    upload = await db.get(InvoiceUpload, upload_id)
    if not upload:
        raise HTTPException(404, "File not found")

    data = getattr(upload, "fileData", None)
    data_bytes = bytes(data) if data else None
    path = Path(upload.filePath) if upload.filePath else None
    if data_bytes is None and path and path.exists():
        data_bytes = path.read_bytes()

    file_name = upload.fileName or (path.name if path else "document")

    if _looks_like_meta_json(data_bytes, upload.fileName, upload.filePath):
        recovered = _recover_bill_from_meta(upload, data_bytes)
        if recovered:
            data_bytes, file_name = recovered
            # Persist repair so View keeps working
            try:
                ext = Path(file_name).suffix.lower() or ".bin"
                if ext not in _MEDIA_EXTS:
                    sniffed = _sniff_media_type(data_bytes)
                    ext = {
                        "application/pdf": ".pdf",
                        "image/jpeg": ".jpg",
                        "image/png": ".png",
                        "image/webp": ".webp",
                        "image/gif": ".gif",
                    }.get(sniffed or "", ".bin")
                repaired = UPLOAD_DIR / f"expense_{uuid4().hex[:8]}{ext}"
                repaired.write_bytes(data_bytes)
                if path and path.exists() and (
                    path.suffix.lower() == ".json" or path.name.lower().endswith(".meta.json")
                ):
                    path.unlink(missing_ok=True)
                upload.fileName = file_name
                upload.filePath = str(repaired)
                upload.fileData = data_bytes
                await db.commit()
                path = repaired
            except Exception:
                await db.rollback()
        else:
            raise HTTPException(
                404,
                "Original bill file missing — only metadata was saved. Please re-upload this bill.",
            )

    if not data_bytes:
        raise HTTPException(404, "File missing — re-upload this bill")

    media = (
        _sniff_media_type(data_bytes)
        or _guess_media_type(file_name)
        or _guess_media_type(str(path) if path else "")
        or "application/octet-stream"
    )
    safe_name = file_name.replace('"', "")
    headers = {"Content-Disposition": f'inline; filename="{safe_name}"'}

    # Backfill DB from resolved bytes for older uploads
    if not getattr(upload, "fileData", None):
        try:
            upload.fileData = data_bytes
            await db.commit()
        except Exception:
            await db.rollback()

    return Response(content=data_bytes, media_type=media, headers=headers)


@router.delete("/uploads/{upload_id}")
async def delete_upload(upload_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Remove an expense or profit bill from history and storage."""
    upload = await db.get(InvoiceUpload, upload_id)
    if not upload:
        raise HTTPException(404, "File not found")
    path = Path(upload.filePath) if upload.filePath else None
    await db.delete(upload)
    await db.commit()
    if path and path.exists():
        path.unlink(missing_ok=True)
    return {"ok": True, "id": upload_id}
