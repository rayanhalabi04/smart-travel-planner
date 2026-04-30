from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


def load_embedding_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    embedder: Any,
) -> list[list[float]]:
    if not texts:
        return []

    embeddings = embedder.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    return embeddings.astype(np.float32).tolist()


def embed_query(
    query: str,
    embedder: Any,
) -> list[float]:
    if not query or not query.strip():
        raise ValueError("Query must not be empty.")

    embedding = embedder.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )[0]

    return embedding.astype(np.float32).tolist()