"""Run: python scripts/seed_demo.py (from whatsapp/)"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, init_db
from app.data.seed_demo_data import seed_demo_data


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        result = await seed_demo_data(session, force=True)
    print("Demo data seeded:", result)


if __name__ == "__main__":
    asyncio.run(main())
