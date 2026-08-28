from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import EventPhoto
from app.schemas import EventPhotoAlbumOut, EventPhotoAlbumsOut, EventPhotoOut
from app.services.event_photos import (
    ALLOWED_IMAGE_EXTS,
    MAX_PHOTO_BYTES,
    MAX_PHOTOS_PER_EVENT,
    PHOTO_EVENT_TYPES,
    canonical_photo_event,
    event_photo_dashboard_url,
    guess_image_type,
    sniff_image_type,
)

router = APIRouter(prefix="/api", tags=["event-photos"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "event-photos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _to_out(photo: EventPhoto) -> EventPhotoOut:
    return EventPhotoOut(
        id=photo.id,
        eventType=photo.eventType,
        fileName=photo.fileName,
        caption=photo.caption,
        url=event_photo_dashboard_url(photo.id),
        createdAt=photo.createdAt or datetime.utcnow(),
    )


@router.get("/event-photos", response_model=EventPhotoAlbumsOut)
async def list_event_photo_albums(db: AsyncSession = Depends(get_db)) -> EventPhotoAlbumsOut:
    result = await db.execute(select(EventPhoto).order_by(EventPhoto.createdAt.desc()))
    photos = list(result.scalars().all())
    by_event: dict[str, list[EventPhoto]] = {event: [] for event in PHOTO_EVENT_TYPES}
    for photo in photos:
        key = canonical_photo_event(photo.eventType) or photo.eventType
        by_event.setdefault(key, []).append(photo)
    albums = [
        EventPhotoAlbumOut(
            eventType=event,
            count=len(by_event.get(event, [])),
            photos=[_to_out(p) for p in by_event.get(event, [])],
        )
        for event in PHOTO_EVENT_TYPES
    ]
    extra = [key for key in by_event if key not in PHOTO_EVENT_TYPES and by_event[key]]
    for key in extra:
        albums.append(
            EventPhotoAlbumOut(
                eventType=key,
                count=len(by_event[key]),
                photos=[_to_out(p) for p in by_event[key]],
            )
        )
    return EventPhotoAlbumsOut(albums=albums)


@router.post("/event-photos", response_model=list[EventPhotoOut])
async def upload_event_photos(
    eventType: str = Form(...),
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> list[EventPhotoOut]:
    event = canonical_photo_event(eventType)
    if not event:
        raise HTTPException(400, "Unknown event type")
    if not files:
        raise HTTPException(400, "Choose at least one photo")

    existing = await db.execute(select(EventPhoto))
    current = [
        row
        for row in existing.scalars().all()
        if canonical_photo_event(row.eventType) == event
    ]
    remaining = MAX_PHOTOS_PER_EVENT - len(current)
    if remaining <= 0:
        raise HTTPException(400, f"{event} already has {MAX_PHOTOS_PER_EVENT} photos")

    saved: list[EventPhoto] = []
    for upload in files:
        if len(saved) >= remaining:
            break
        name = upload.filename or "photo.jpg"
        ext = Path(name).suffix.lower()
        if ext == ".jpeg":
            ext = ".jpg"
        data = await upload.read()
        if not data:
            continue
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(400, f"{name} is larger than 10 MB")
        sniffed = sniff_image_type(data)
        if not sniffed and ext not in ALLOWED_IMAGE_EXTS:
            raise HTTPException(400, f"{name} must be a JPG, PNG, WEBP, or GIF photo")
        if ext not in ALLOWED_IMAGE_EXTS:
            ext = { "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif" }.get(
                sniffed or "", ".jpg"
            )
        dest = UPLOAD_DIR / f"event_{uuid4().hex[:12]}{ext}"
        dest.write_bytes(data)
        row = EventPhoto(
            eventType=event,
            fileName=name,
            filePath=str(dest),
            fileData=data,
            caption=f"{event} by Srivatsanka",
        )
        db.add(row)
        saved.append(row)

    if not saved:
        raise HTTPException(400, "No photos could be saved")
    await db.commit()
    for row in saved:
        await db.refresh(row)
    return [_to_out(row) for row in saved]


@router.delete("/event-photos/{photo_id}")
async def delete_event_photo(photo_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    photo = await db.get(EventPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    path = Path(photo.filePath) if photo.filePath else None
    await db.delete(photo)
    await db.commit()
    if path and path.exists():
        path.unlink(missing_ok=True)
    return {"ok": True, "id": photo_id}


@router.get("/public/event-photos/{photo_id}")
async def public_event_photo(photo_id: str, db: AsyncSession = Depends(get_db)):
    """Public file URL so WhatsApp Cloud API can fetch the image."""
    photo = await db.get(EventPhoto, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    data = bytes(photo.fileData) if photo.fileData else None
    path = Path(photo.filePath) if photo.filePath else None
    if data is None and path and path.exists():
        data = path.read_bytes()
        if data and not photo.fileData:
            photo.fileData = data
            try:
                await db.commit()
            except Exception:
                await db.rollback()
    if not data:
        raise HTTPException(404, "Photo file missing")
    media = sniff_image_type(data) or guess_image_type(photo.fileName)
    safe_name = (photo.fileName or "photo.jpg").replace('"', "")
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"', "Cache-Control": "public, max-age=86400"},
    )
