from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.retriever import retrieve_destinations_by_style
from app.schemas.tools import DestinationSearchToolInput
from app.utils.travel_style import normalize_travel_style


TOOL_NAME = "destination_search"


async def destination_search_tool(
    payload: DestinationSearchToolInput,
    model: Any = None,
    feature_columns: list[str] | None = None,
    embedder: Any = None,
    session: AsyncSession | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    normalized_style = normalize_travel_style(payload.travel_style)
    if normalized_style is None:
        normalized_style = normalize_travel_style(payload.query)

    if normalized_style is None:
        return {
            "query": payload.query,
            "resolved_search": None,
            "destinations": [],
            "matches": [],
        }

    if embedder is None:
        raise ValueError("embedder is required for destination_search tool.")

    if session is None:
        raise ValueError("session is required for destination_search tool.")

    results = await retrieve_destinations_by_style(
        travel_style=normalized_style,
        embedder=embedder,
        session=session,
        top_k=payload.top_k,
    )

    seen: set[tuple[str, str]] = set()
    destinations = []
    matches = []

    for item in results:
        destination_name = str(item["destination_name"])
        country = str(item["country"])
        key = (destination_name, country)
        snippet = " ".join(str(item["document"]).split())[:240]

        if key in seen:
            # Keep additional chunk-level evidence even for known destinations.
            matches.append(
                {
                    "destination_name": destination_name,
                    "country": country,
                    "travel_style": str(item["travel_style"]),
                    "snippet": snippet,
                    "source_name": item["source_name"],
                    "source_url": item["source_url"],
                    "distance": round(float(item["distance"]), 5),
                }
            )
            continue

        seen.add(key)
        destinations.append({"destination_name": destination_name, "country": country})
        matches.append(
            {
                "destination_name": destination_name,
                "country": country,
                "travel_style": str(item["travel_style"]),
                "snippet": snippet,
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "distance": round(float(item["distance"]), 5),
            }
        )

    return {
        "query": payload.query,
        "resolved_search": normalized_style,
        "destinations": destinations,
        "matches": matches,
    }
