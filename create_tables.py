import asyncio

from sqlalchemy import text

from app.config import get_settings
from app.db.models import Base
from app.db.session import create_engine


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()

    print("✅ Database tables created successfully")


if __name__ == "__main__":
    asyncio.run(main())
