from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "doc_id",
    "destination_name",
    "country",
    "source_name",
    "source_url",
    "title",
    "text",
    "travel_style",
]

NON_EMPTY_COLUMNS = [
    "doc_id",
    "destination_name",
    "country",
    "source_name",
    "title",
    "text",
    "travel_style",
]


def load_destination_rows(csv_path: str | Path) -> list[dict[str, Any]]:
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"RAG dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)

    missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing columns in RAG dataset: {sorted(missing_columns)}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    for column in REQUIRED_COLUMNS:
        df[column] = df[column].fillna("").astype(str).str.strip()

    invalid_rows = df.index[df[NON_EMPTY_COLUMNS].eq("").any(axis=1)].tolist()
    if invalid_rows:
        csv_lines = [row_index + 2 for row_index in invalid_rows[:10]]
        raise ValueError(
            "RAG dataset has empty required values at CSV lines: "
            f"{csv_lines}. Required non-empty columns: {NON_EMPTY_COLUMNS}"
        )

    df = df.drop_duplicates(subset=REQUIRED_COLUMNS, keep="first")

    return df.to_dict(orient="records")
