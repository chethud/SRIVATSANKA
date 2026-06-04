from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Expense, Vendor, Worker
from app.schemas import AnalyticsOut, ExpenseIn, ExpenseOut, VendorIn, VendorOut, WorkerIn, WorkerOut, WorkerUpdateIn

router = APIRouter(prefix="/api", tags=["resources"])


@router.get("/analytics", response_model=AnalyticsOut)
async def get_analytics(db: AsyncSession = Depends(get_db)) -> AnalyticsOut:
    from app.services.profit import compute_profit_analytics

    data = await compute_profit_analytics(db)
    return AnalyticsOut(**data)


# ─── Vendors ───────────────────────────────────────────────────────────────────

@router.get("/vendors", response_model=list[VendorOut])
async def list_vendors(db: AsyncSession = Depends(get_db)) -> list[VendorOut]:
    result = await db.execute(select(Vendor).order_by(Vendor.category, Vendor.name))
    return [
        VendorOut(
            id=v.id, name=v.name, businessName=v.businessName,
            phoneNumber=v.phoneNumber, category=v.category, notes=v.notes, createdAt=v.createdAt,
        )
        for v in result.scalars().all()
    ]


@router.post("/vendors", response_model=VendorOut)
async def create_vendor(payload: VendorIn, db: AsyncSession = Depends(get_db)) -> VendorOut:
    v = Vendor(**payload.model_dump())
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return VendorOut(
        id=v.id, name=v.name, businessName=v.businessName,
        phoneNumber=v.phoneNumber, category=v.category, notes=v.notes, createdAt=v.createdAt,
    )


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    v = await db.get(Vendor, vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    await db.delete(v)
    await db.commit()
    return {"ok": True}


# ─── Workers ───────────────────────────────────────────────────────────────────

@router.get("/workers", response_model=list[WorkerOut])
async def list_workers(db: AsyncSession = Depends(get_db)) -> list[WorkerOut]:
    result = await db.execute(select(Worker).order_by(Worker.name))
    return [
        WorkerOut(
            id=w.id, name=w.name, phoneNumber=w.phoneNumber,
            role=w.role, dailyWage=w.dailyWage, isLead=w.isLead, createdAt=w.createdAt,
        )
        for w in result.scalars().all()
    ]


@router.post("/workers", response_model=WorkerOut)
async def create_worker(payload: WorkerIn, db: AsyncSession = Depends(get_db)) -> WorkerOut:
    w = Worker(**payload.model_dump())
    db.add(w)
    await db.commit()
    await db.refresh(w)
    return WorkerOut(
        id=w.id, name=w.name, phoneNumber=w.phoneNumber,
        role=w.role, dailyWage=w.dailyWage, isLead=w.isLead, createdAt=w.createdAt,
    )


@router.patch("/workers/{worker_id}", response_model=WorkerOut)
async def update_worker(
    worker_id: str,
    payload: WorkerUpdateIn,
    db: AsyncSession = Depends(get_db),
) -> WorkerOut:
    w = await db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    if payload.isLead is not None:
        if payload.isLead:
            others = await db.execute(select(Worker).where(Worker.id != worker_id))
            for other in others.scalars().all():
                other.isLead = False
        w.isLead = payload.isLead
    await db.commit()
    await db.refresh(w)
    return WorkerOut(
        id=w.id, name=w.name, phoneNumber=w.phoneNumber,
        role=w.role, dailyWage=w.dailyWage, isLead=w.isLead, createdAt=w.createdAt,
    )


@router.delete("/workers/{worker_id}")
async def delete_worker(worker_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    w = await db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")
    await db.delete(w)
    await db.commit()
    return {"ok": True}


# ─── Expenses ──────────────────────────────────────────────────────────────────

@router.get("/expenses", response_model=list[ExpenseOut])
async def list_expenses(db: AsyncSession = Depends(get_db)) -> list[ExpenseOut]:
    result = await db.execute(select(Expense).order_by(Expense.expenseDate.desc()))
    return [
        ExpenseOut(
            id=e.id, category=e.category, amount=e.amount,
            description=e.description, expenseDate=e.expenseDate, createdAt=e.createdAt,
        )
        for e in result.scalars().all()
    ]


@router.post("/expenses", response_model=ExpenseOut)
async def create_expense(payload: ExpenseIn, db: AsyncSession = Depends(get_db)) -> ExpenseOut:
    data = payload.model_dump()
    if not data.get("expenseDate"):
        data["expenseDate"] = datetime.now()
    e = Expense(**data)
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return ExpenseOut(
        id=e.id, category=e.category, amount=e.amount,
        description=e.description, expenseDate=e.expenseDate, createdAt=e.createdAt,
    )


@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    e = await db.get(Expense, expense_id)
    if not e:
        raise HTTPException(404, "Expense not found")
    await db.delete(e)
    await db.commit()
    return {"ok": True}
