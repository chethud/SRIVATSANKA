from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Enquiry, EnquiryStatus, Expense, Vendor, Worker, WorkerAssignment
from app.schemas import (
    AnalyticsOut,
    ExpenseIn,
    ExpenseOut,
    VendorIn,
    VendorOut,
    WorkerAssignmentIn,
    WorkerAssignmentOut,
    WorkerAssignmentPatchIn,
    WorkerIn,
    WorkerOut,
    WorkerProfileOut,
    WorkerUpdateIn,
)

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


def _assignment_out(a: WorkerAssignment, enquiry: Enquiry | None) -> WorkerAssignmentOut:
    label = None
    if enquiry:
        label = f"{enquiry.customerName} — {enquiry.eventType}"
    return WorkerAssignmentOut(
        id=a.id,
        workerId=a.workerId,
        enquiryId=a.enquiryId,
        dutyDate=a.dutyDate,
        dutyType=a.dutyType,
        wage=float(a.wage or 0),
        paymentCompleted=bool(a.paymentCompleted),
        notes=a.notes,
        createdAt=a.createdAt,
        customerName=enquiry.customerName if enquiry else None,
        eventType=enquiry.eventType if enquiry else None,
        eventLocation=enquiry.eventLocation if enquiry else None,
        orderLabel=label,
    )


@router.get("/workers/{worker_id}/profile", response_model=WorkerProfileOut)
async def get_worker_profile(worker_id: str, db: AsyncSession = Depends(get_db)) -> WorkerProfileOut:
    w = await db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")

    result = await db.execute(
        select(WorkerAssignment, Enquiry)
        .outerjoin(Enquiry, WorkerAssignment.enquiryId == Enquiry.id)
        .where(WorkerAssignment.workerId == worker_id)
        .order_by(WorkerAssignment.dutyDate.desc(), WorkerAssignment.createdAt.desc())
    )
    rows = result.all()
    assignments = [_assignment_out(a, e) for a, e in rows]

    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    pending = [(a, e) for a, e in rows if not a.paymentCompleted]
    upcoming = sum(1 for a, _ in pending if a.dutyDate >= day_start)
    total_wages = sum(float(a.wage or 0) for a, _ in pending)

    return WorkerProfileOut(
        worker=WorkerOut(
            id=w.id, name=w.name, phoneNumber=w.phoneNumber,
            role=w.role, dailyWage=w.dailyWage, isLead=w.isLead, createdAt=w.createdAt,
        ),
        assignments=assignments,
        totalDuties=len(pending),
        upcomingDuties=upcoming,
        totalWagesEarned=total_wages,
    )


@router.post("/workers/{worker_id}/assignments", response_model=WorkerAssignmentOut)
async def create_worker_assignment(
    worker_id: str,
    payload: WorkerAssignmentIn,
    db: AsyncSession = Depends(get_db),
) -> WorkerAssignmentOut:
    w = await db.get(Worker, worker_id)
    if not w:
        raise HTTPException(404, "Worker not found")

    enquiry = None
    if payload.enquiryId:
        enquiry = await db.get(Enquiry, payload.enquiryId)
        if not enquiry:
            raise HTTPException(404, "Order / enquiry not found")

    row = WorkerAssignment(
        workerId=worker_id,
        enquiryId=payload.enquiryId,
        dutyDate=payload.dutyDate,
        dutyType=payload.dutyType.strip(),
        wage=max(0.0, float(payload.wage or 0)),
        notes=payload.notes,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    if not enquiry and row.enquiryId:
        enquiry = await db.get(Enquiry, row.enquiryId)
    return _assignment_out(row, enquiry)


@router.patch("/workers/{worker_id}/assignments/{assignment_id}", response_model=WorkerAssignmentOut)
async def patch_worker_assignment(
    worker_id: str,
    assignment_id: str,
    payload: WorkerAssignmentPatchIn,
    db: AsyncSession = Depends(get_db),
) -> WorkerAssignmentOut:
    row = await db.get(WorkerAssignment, assignment_id)
    if not row or row.workerId != worker_id:
        raise HTTPException(404, "Assignment not found")
    if payload.paymentCompleted is not None:
        row.paymentCompleted = payload.paymentCompleted
    await db.commit()
    await db.refresh(row)
    enquiry = await db.get(Enquiry, row.enquiryId) if row.enquiryId else None
    return _assignment_out(row, enquiry)


@router.delete("/workers/{worker_id}/assignments/{assignment_id}")
async def delete_worker_assignment(
    worker_id: str,
    assignment_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await db.get(WorkerAssignment, assignment_id)
    if not row or row.workerId != worker_id:
        raise HTTPException(404, "Assignment not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}


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
