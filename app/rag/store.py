from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection


DEFAULT_COLLECTION_NAME = "destinations"


def get_chroma_client(chroma_dir: str | Path) -> chromadb.PersistentClient:
    chroma_dir = Path(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(path=str(chroma_dir))


def get_or_create_collection(
    client: chromadb.PersistentClient,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Collection:
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"description": "Destination documents for Smart Travel Planner"},
    )


def add_documents_to_collection(
    collection: Collection,
    documents: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> None:
    if not documents:
        return

    if len(documents) != len(embeddings):
        raise ValueError("Number of documents must match number of embeddings.")

    ids = [doc["id"] for doc in documents]
    texts = [doc["text"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]

    collection.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def load_collection(
    chroma_dir: str | Path,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Collection:
    client = get_chroma_client(chroma_dir)
    return get_or_create_collection(client, collection_name)