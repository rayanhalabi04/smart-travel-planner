from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_db_session, get_embedder
from app.rag.retriever import retrieve_destinations_by_style
from app.schemas.rag import RagSearchRequest, RagSearchResponse

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/search", response_model=RagSearchResponse)
async def search_destinations(
    request: RagSearchRequest,
    embedder: Any = Depends(get_embedder),
    session: AsyncSession = Depends(get_db_session),
):
    settings = get_settings()

    results = await retrieve_destinations_by_style(
        travel_style=request.travel_style.strip().title(),
        embedder=embedder,
        session=session,
        top_k=settings.rag_top_k,
    )

    seen: set[tuple[str, str]] = set()
    cleaned_results = []

    for item in results:
        destination_name = str(item["destination_name"])
        country = str(item["country"])
        key = (destination_name, country)

        if key in seen:
            continue

        seen.add(key)
        cleaned_results.append(
            {
                "destination_name": destination_name,
                "country": country,
            }
        )

    return {"destinations": cleaned_results}
