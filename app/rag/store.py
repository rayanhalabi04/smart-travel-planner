from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DestinationChunk


async def replace_destination_chunks(
    session: AsyncSession,
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("Number of chunks must match number of embeddings.")

    await session.execute(delete(DestinationChunk))

    if not chunks:
        await session.commit()
        return 0

    entities = [
        DestinationChunk(
            destination_name=chunk["destination_name"],
            country=chunk["country"],
            source_name=chunk["source_name"],
            source_url=chunk["source_url"],
            title=chunk["title"],
            travel_style=chunk["travel_style"],
            chunk_index=chunk["chunk_index"],
            text=chunk["text"],
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    session.add_all(entities)
    await session.commit()

    return len(entities)


async def count_destination_chunks(session: AsyncSession) -> int:
    result = await session.execute(select(func.count(DestinationChunk.id)))
    return int(result.scalar_one())
