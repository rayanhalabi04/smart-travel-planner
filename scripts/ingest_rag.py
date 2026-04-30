from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import asyncio

from sqlalchemy import text

from app.config import get_settings
from app.db.models import Base
from app.db.session import create_engine, create_session_maker
from app.rag.embedder import load_embedding_model
from app.rag.ingestion import ingest_destinations


async def main() -> None:
    settings = get_settings()
    engine = create_engine(settings)
    session_maker = create_session_maker(engine)

    csv_path = settings.rag_documents_path
    embedder = load_embedding_model(settings.embedding_model)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        result = await ingest_destinations(
            csv_path=csv_path,
            session=session,
            embedder=embedder,
        )

    await engine.dispose()

    print("RAG ingestion completed.")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
