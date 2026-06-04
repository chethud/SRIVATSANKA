from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def _migrate_sqlite_columns() -> None:
    """Add new columns to existing SQLite DBs without full reset."""
    import sqlalchemy as sa

    from app.models import EnquiryDish, Worker

    async with engine.begin() as conn:
        def run(connection):
            insp = sa.inspect(connection)
            tables = insp.get_table_names()
            alters: list[str] = []
            if "EnquiryDish" in tables:
                cols = {c["name"] for c in insp.get_columns("EnquiryDish")}
                if "quantity" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN quantity INTEGER DEFAULT 1")
                if "unitPrice" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN unitPrice FLOAT")
                if "served" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN served BOOLEAN DEFAULT 0")
            if "Worker" in tables:
                wcols = {c["name"] for c in insp.get_columns("Worker")}
                if "isLead" not in wcols:
                    alters.append("ALTER TABLE Worker ADD COLUMN isLead BOOLEAN DEFAULT 0")
            if "WorkerAssignment" in tables:
                acols = {c["name"] for c in insp.get_columns("WorkerAssignment")}
                if "wage" not in acols:
                    alters.append("ALTER TABLE WorkerAssignment ADD COLUMN wage FLOAT DEFAULT 0")
                if "paymentCompleted" not in acols:
                    alters.append("ALTER TABLE WorkerAssignment ADD COLUMN paymentCompleted BOOLEAN DEFAULT 0")
            if "InvoiceUpload" in tables:
                icols = {c["name"] for c in insp.get_columns("InvoiceUpload")}
                if "purpose" not in icols:
                    alters.append("ALTER TABLE InvoiceUpload ADD COLUMN purpose VARCHAR")
                if "expenseDate" not in icols:
                    alters.append("ALTER TABLE InvoiceUpload ADD COLUMN expenseDate DATETIME")
            elif "Worker" in tables:
                connection.execute(
                    sa.text(
                        """
                        CREATE TABLE IF NOT EXISTS WorkerAssignment (
                            id VARCHAR PRIMARY KEY,
                            workerId VARCHAR NOT NULL,
                            enquiryId VARCHAR,
                            dutyDate DATETIME NOT NULL,
                            dutyType VARCHAR NOT NULL,
                            wage FLOAT DEFAULT 0,
                            paymentCompleted BOOLEAN DEFAULT 0,
                            notes TEXT,
                            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY(workerId) REFERENCES Worker(id) ON DELETE CASCADE,
                            FOREIGN KEY(enquiryId) REFERENCES Enquiry(id) ON DELETE SET NULL
                        )
                        """
                    )
                )
            for sql in alters:
                connection.execute(sa.text(sql))

        await conn.run_sync(run)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _migrate_sqlite_columns()

    from app.data.seed_dishes import seed_dishes

    async with SessionLocal() as session:
        await seed_dishes(session)
