from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import is_sqlite_database, settings


def _engine_connect_args() -> dict:
    if is_sqlite_database(settings.database_url):
        return {}
    args: dict = {"ssl": "require"}
    url = settings.database_url
    # Supabase Supavisor (session or transaction pooler) + asyncpg
    if ":6543" in url or "pooler.supabase.com" in url:
        args["statement_cache_size"] = 0
        args["prepared_statement_cache_size"] = 0
    return args


engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args=_engine_connect_args(),
    pool_pre_ping=not is_sqlite_database(settings.database_url),
)
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

            if "Enquiry" in tables:
                connection.execute(
                    sa.text("UPDATE Enquiry SET status = 'NOT_CONVERTED' WHERE status = 'CLOSED'")
                )

            from app.services.whatsapp_client import normalize_phone

            if "WhatsappChatMessage" in tables:
                rows = connection.execute(sa.text("SELECT id, phoneNumber FROM WhatsappChatMessage")).fetchall()
                for row_id, phone in rows:
                    normalized = normalize_phone(phone)
                    if normalized and normalized != phone:
                        connection.execute(
                            sa.text("UPDATE WhatsappChatMessage SET phoneNumber = :n WHERE id = :id"),
                            {"n": normalized, "id": row_id},
                        )

            if "Enquiry" in tables:
                rows = connection.execute(sa.text("SELECT id, phoneNumber FROM Enquiry")).fetchall()
                for row_id, phone in rows:
                    normalized = normalize_phone(phone)
                    if normalized and normalized != phone:
                        connection.execute(
                            sa.text("UPDATE Enquiry SET phoneNumber = :n WHERE id = :id"),
                            {"n": normalized, "id": row_id},
                        )

            if "Dish" in tables:
                from app.data.meal_sessions import OLD_DISH_ENUM_MAP

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


async def _migrate_dish_category_to_labels() -> None:
    """Convert Dish.category from Postgres enum → VARCHAR, then rewrite labels.

    Must alter the column type BEFORE writing display labels like \"Breakfast\",
    otherwise Postgres rejects them as invalid dishcategory enum values.
    """
    import sqlalchemy as sa

    from app.data.meal_sessions import ENUM_VALUE_TO_LABEL, OLD_DISH_ENUM_MAP

    async with engine.begin() as conn:
        def run(connection) -> None:
            inspector = sa.inspect(connection)
            if "Dish" not in inspector.get_table_names():
                return

            if connection.dialect.name == "postgresql":
                # Detect current column type — skip ALTER if already varchar/text
                row = connection.execute(
                    sa.text(
                        """
                        SELECT data_type, udt_name
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = 'Dish'
                          AND column_name = 'category'
                        """
                    )
                ).fetchone()
                data_type = (row[0] if row else "") or ""
                udt_name = (row[1] if row else "") or ""
                needs_alter = data_type == "USER-DEFINED" or "enum" in udt_name.lower() or udt_name == "dishcategory"
                if needs_alter:
                    connection.execute(
                        sa.text(
                            'ALTER TABLE "Dish" ALTER COLUMN category TYPE VARCHAR '
                            "USING category::text"
                        )
                    )

            # Legacy cuisine enum tokens → meal session enum tokens (string form)
            for old_val, new_val in OLD_DISH_ENUM_MAP.items():
                connection.execute(
                    sa.text('UPDATE "Dish" SET category = :new WHERE category = :old'),
                    {"old": old_val, "new": new_val},
                )

            # Enum tokens (BREAKFAST) → display labels (Breakfast)
            for enum_val, label in ENUM_VALUE_TO_LABEL.items():
                if enum_val == label:
                    continue
                connection.execute(
                    sa.text('UPDATE "Dish" SET category = :label WHERE category = :enum'),
                    {"enum": enum_val, "label": label},
                )

        await conn.run_sync(run)


async def init_db() -> None:
    import app.models  # noqa: F401 — register every table before create_all

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _migrate_sqlite_columns() if is_sqlite_database(settings.database_url) else None
    await _migrate_dish_category_to_labels()

    from app.data.seed_dishes import seed_dishes

    async with SessionLocal() as session:
        await seed_dishes(session)
