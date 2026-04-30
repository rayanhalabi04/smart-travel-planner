from pathlib import Path
from typing import Any

from app.rag.embedder import embed_query
from app.rag.store import load_collection


def retrieve_destinations_by_style(
    travel_style: str,
    embedder: Any,
    chroma_path: str | Path,
    collection_name: str,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    if not travel_style or not travel_style.strip():
        raise ValueError("travel_style must not be empty.")

    collection = load_collection(
        chroma_dir=chroma_path,
        collection_name=collection_name,
    )

    if collection.count() == 0:
        return []

    query_embedding = embed_query(
        query=travel_style,
        embedder=embedder,
    )

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"travel_style": travel_style},
        include=["documents", "metadatas", "distances"],
    )

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    destinations = []

    for document, metadata, distance in zip(documents, metadatas, distances):
        destinations.append(
            {
                "destination_name": metadata.get("destination_name"),
                "country": metadata.get("country"),
                "travel_style": metadata.get("travel_style"),
                "distance": distance,
                "document": document,
            }
        )

    return destinations