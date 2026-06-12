from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SiteSetting
from app.schemas import BrandInfo

router = APIRouter(prefix="/api/brand", tags=["brand"])

BRAND_LOGO_KEY = "brand_logo"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"}
MAX_BYTES = 5 * 1024 * 1024


async def _get_logo_row(db: AsyncSession) -> SiteSetting | None:
    result = await db.execute(select(SiteSetting).where(SiteSetting.key == BRAND_LOGO_KEY))
    return result.scalar_one_or_none()


@router.get("", response_model=BrandInfo)
async def brand_info(db: AsyncSession = Depends(get_db)) -> BrandInfo:
    row = await _get_logo_row(db)
    if not row or not row.blob:
        return BrandInfo(customLogo=False, updatedAt=None)
    return BrandInfo(customLogo=True, updatedAt=row.updatedAt)


@router.get("/logo")
async def brand_logo(db: AsyncSession = Depends(get_db)) -> Response:
    row = await _get_logo_row(db)
    if not row or not row.blob:
        raise HTTPException(status_code=404, detail="No custom logo uploaded")
    return Response(
        content=row.blob,
        media_type=row.contentType or "image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.post("/logo", response_model=BrandInfo)
async def upload_brand_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> BrandInfo:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG, WebP, GIF, or SVG image")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 5 MB or smaller")

    now = datetime.now()
    row = await _get_logo_row(db)
    if row:
        row.blob = data
        row.contentType = content_type
        row.updatedAt = now
    else:
        db.add(
            SiteSetting(
                key=BRAND_LOGO_KEY,
                blob=data,
                contentType=content_type,
                updatedAt=now,
            )
        )
    await db.commit()
    return BrandInfo(customLogo=True, updatedAt=now)
