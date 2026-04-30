from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.chunker import build_destination_chunks
from app.rag.embedder import embed_texts
from app.rag.loader import load_destination_rows
from app.rag.store import count_destination_chunks, replace_destination_chunks


async def ingest_destinations(
    csv_path: str | Path,
    session: AsyncSession,
    embedder: Any,
) -> dict[str, Any]:
    rows = load_destination_rows(csv_path)

    chunks = build_destination_chunks(
        rows=rows,
        chunk_size=800,
        overlap=150,
    )

    texts = [chunk["text"] for chunk in chunks]

    embeddings = embed_texts(
        texts=texts,
        embedder=embedder,
    )

    chunks_ingested = await replace_destination_chunks(
        session=session,
        chunks=chunks,
        embeddings=embeddings,
    )

    total_chunks = await count_destination_chunks(session)

    return {
        "status": "success",
        "rows_loaded": len(rows),
        "chunks_created": len(chunks),
        "chunks_ingested": chunks_ingested,
        "table_count": total_chunks,
    }
