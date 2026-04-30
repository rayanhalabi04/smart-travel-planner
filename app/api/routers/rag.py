from typing import Any

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.dependencies import get_embedder
from app.rag.retriever import retrieve_destinations_by_style
from app.schemas.rag import RagSearchRequest, RagSearchResponse

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/search", response_model=RagSearchResponse)
def search_destinations(
    request: RagSearchRequest,
    embedder: Any = Depends(get_embedder),
):
    settings = get_settings()

    results = retrieve_destinations_by_style(
        travel_style=request.travel_style.strip().title(),
        embedder=embedder,
        chroma_path=settings.chroma_path,
        collection_name=settings.chroma_collection_name,
        top_k=settings.rag_top_k,
    )

    cleaned_results = [
        {
            "destination_name": item["destination_name"],
            "country": item["country"],
        }
        for item in results
    ]

    return {"destinations": cleaned_results}