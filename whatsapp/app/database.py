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


def _recreate_invoice_upload_nullable_enquiry(connection) -> None:
    """SQLite cannot ALTER COLUMN nullability — recreate InvoiceUpload for standalone expenses."""
    import sqlalchemy as sa

    connection.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS InvoiceUpload_new (
                id VARCHAR PRIMARY KEY,
                enquiryId VARCHAR,
                docType VARCHAR NOT NULL,
                fileName VARCHAR NOT NULL,
                filePath VARCHAR NOT NULL,
                amount FLOAT,
                notes TEXT,
                purpose VARCHAR,
                expenseDate DATETIME,
                createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(enquiryId) REFERENCES Enquiry(id) ON DELETE SET NULL
            )
            """
        )
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO InvoiceUpload_new (
                id, enquiryId, docType, fileName, filePath, amount, notes, purpose, expenseDate, createdAt
            )
            SELECT
                id, enquiryId, docType, fileName, filePath, amount, notes, purpose, expenseDate, createdAt
            FROM InvoiceUpload
            """
        )
    )
    connection.execute(sa.text("DROP TABLE InvoiceUpload"))
    connection.execute(sa.text("ALTER TABLE InvoiceUpload_new RENAME TO InvoiceUpload"))


async def _migrate_sqlite_columns() -> None:
    """Add new columns to existing SQLite DBs without full reset."""
    import sqlalchemy as sa

    from app.models import EnquiryDish, Worker

    async with engine.begin() as conn:
        def run(connection):
            insp = sa.inspect(connection)
            tables = insp.get_table_names()
            alters: list[str] = []
            if "Enquiry" in tables:
                ecols = {c["name"] for c in insp.get_columns("Enquiry")}
                if "ownerViewedAt" not in ecols:
                    alters.append("ALTER TABLE Enquiry ADD COLUMN ownerViewedAt DATETIME")
            if "EnquiryDish" in tables:
                cols = {c["name"] for c in insp.get_columns("EnquiryDish")}
                if "quantity" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN quantity INTEGER DEFAULT 1")
                if "unitPrice" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN unitPrice FLOAT")
                if "served" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN served BOOLEAN DEFAULT 0")
                if "quantityUnit" not in cols:
                    alters.append("ALTER TABLE EnquiryDish ADD COLUMN quantityUnit VARCHAR DEFAULT 'pcs'")
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
                icols = list(insp.get_columns("InvoiceUpload"))
                icol_names = {c["name"] for c in icols}
                if "purpose" not in icol_names:
                    connection.execute(sa.text("ALTER TABLE InvoiceUpload ADD COLUMN purpose VARCHAR"))
                if "expenseDate" not in icol_names:
                    connection.execute(sa.text("ALTER TABLE InvoiceUpload ADD COLUMN expenseDate DATETIME"))
                icols = list(insp.get_columns("InvoiceUpload"))
                enquiry_col = next((c for c in icols if c["name"] == "enquiryId"), None)
                if enquiry_col is not None and enquiry_col.get("nullable") is False:
                    _recreate_invoice_upload_nullable_enquiry(connection)
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

            if "Dish" in tables:
                from app.data.meal_sessions import OLD_DISH_ENUM_MAP, OLD_ENQUIRY_CATEGORY_MAP

                for old_val, new_val in OLD_DISH_ENUM_MAP.items():
                    connection.execute(
                        sa.text("UPDATE Dish SET category = :new WHERE category = :old"),
                        {"old": old_val, "new": new_val},
                    )
            if "EnquiryDish" in tables:
                from app.data.meal_sessions import OLD_ENQUIRY_CATEGORY_MAP

                for old_val, new_val in OLD_ENQUIRY_CATEGORY_MAP.items():
                    connection.execute(
                        sa.text("UPDATE EnquiryDish SET category = :new WHERE category = :old"),
                        {"old": old_val, "new": new_val},
                    )

        await conn.run_sync(run)


async def init_db() -> None:
    import app.models  # noqa: F401 — register every table before create_all

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _migrate_sqlite_columns()

    from app.data.seed_dishes import seed_dishes

    async with SessionLocal() as session:
        await seed_dishes(session)
