from pathlib import Path
from typing import Any

from app.rag.retriever import retrieve_destinations_by_style


TOOL_NAME = "destination_search"


def destination_search_tool(
    arguments: dict[str, Any],
    model: Any = None,
    feature_columns: list[str] | None = None,
    embedder: Any = None,
    chroma_path: str | Path | None = None,
    collection_name: str | None = None,
    top_k: int = 5,
    **kwargs: Any,
) -> dict[str, Any]:
    travel_style = arguments.get("travel_style")

    if not travel_style:
        return {"destinations": []}

    if embedder is None:
        raise ValueError("embedder is required for destination_search tool.")

    if chroma_path is None:
        raise ValueError("chroma_path is required for destination_search tool.")

    if collection_name is None:
        raise ValueError("collection_name is required for destination_search tool.")

    results = retrieve_destinations_by_style(
        travel_style=str(travel_style).strip().title(),
        embedder=embedder,
        chroma_path=chroma_path,
        collection_name=collection_name,
        top_k=top_k,
    )

    destinations = [
        {
            "destination_name": item["destination_name"],
            "country": item["country"],
        }
        for item in results
    ]

    return {"destinations": destinations}