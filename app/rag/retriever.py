from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DestinationChunk
from app.rag.embedder import embed_query


async def retrieve_destinations_by_style(
    travel_style: str,
    embedder: Any,
    session: AsyncSession,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    if not travel_style or not travel_style.strip():
        raise ValueError("travel_style must not be empty.")

    query_embedding = embed_query(
        query=travel_style,
        embedder=embedder,
    )

    distance = DestinationChunk.embedding.cosine_distance(query_embedding).label(
        "distance"
    )

    statement = (
        select(DestinationChunk, distance)
        .where(DestinationChunk.travel_style == travel_style)
        .order_by(distance.asc())
        .limit(top_k)
    )

    result = await session.execute(statement)
    rows = result.all()

    return [
        {
            "destination_name": chunk.destination_name,
            "country": chunk.country,
            "travel_style": chunk.travel_style,
            "distance": float(chunk_distance),
            "document": chunk.text,
            "source_name": chunk.source_name,
            "source_url": chunk.source_url,
            "title": chunk.title,
            "chunk_index": chunk.chunk_index,
        }
        for chunk, chunk_distance in rows
    ]
