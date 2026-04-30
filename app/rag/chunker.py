from typing import Any


def split_text_with_overlap(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")

    if overlap < 0:
        raise ValueError("overlap must be greater than or equal to 0.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    normalized_text = text.strip()
    if not normalized_text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(normalized_text):
        end = min(start + chunk_size, len(normalized_text))
        chunk = normalized_text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(normalized_text):
            break

        start = end - overlap

    return chunks


def build_destination_chunks(
    rows: list[dict[str, Any]],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for row in rows:
        row_chunks = split_text_with_overlap(
            text=str(row["text"]),
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for chunk_index, chunk_text in enumerate(row_chunks):
            chunks.append(
                {
                    "doc_id": str(row["doc_id"]).strip(),
                    "destination_name": str(row["destination_name"]).strip(),
                    "country": str(row["country"]).strip(),
                    "source_name": str(row["source_name"]).strip(),
                    "source_url": str(row["source_url"]).strip() or None,
                    "title": str(row["title"]).strip(),
                    "travel_style": str(row["travel_style"]).strip(),
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )

    return chunks


# Backward-compatible alias for older imports.
build_destination_documents = build_destination_chunks
