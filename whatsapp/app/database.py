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

    from app.models import EnquiryDish

    async with engine.begin() as conn:
        def run(connection):
            insp = sa.inspect(connection)
            if "EnquiryDish" not in insp.get_table_names():
                return
            cols = {c["name"] for c in insp.get_columns("EnquiryDish")}
            alters = []
            if "quantity" not in cols:
                alters.append("ALTER TABLE EnquiryDish ADD COLUMN quantity INTEGER DEFAULT 1")
            if "unitPrice" not in cols:
                alters.append("ALTER TABLE EnquiryDish ADD COLUMN unitPrice FLOAT")
            if "served" not in cols:
                alters.append("ALTER TABLE EnquiryDish ADD COLUMN served BOOLEAN DEFAULT 0")
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
