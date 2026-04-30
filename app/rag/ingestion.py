from pathlib import Path
from typing import Any

from app.rag.chunker import build_destination_documents
from app.rag.embedder import embed_texts
from app.rag.loader import load_destination_rows
from app.rag.store import add_documents_to_collection, load_collection


def ingest_destinations(
    csv_path: str | Path,
    chroma_path: str | Path,
    collection_name: str,
    embedder: Any,
) -> dict[str, Any]:
    rows = load_destination_rows(csv_path)

    documents = build_destination_documents(rows)

    texts = [document["text"] for document in documents]

    embeddings = embed_texts(
        texts=texts,
        embedder=embedder,
    )

    collection = load_collection(
        chroma_dir=chroma_path,
        collection_name=collection_name,
    )

    add_documents_to_collection(
        collection=collection,
        documents=documents,
        embeddings=embeddings,
    )

    return {
        "status": "success",
        "rows_loaded": len(rows),
        "documents_ingested": len(documents),
        "collection_name": collection_name,
        "collection_count": collection.count(),
    }