from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "destination_name",
    "country",
    "travel_style",
}


def load_destination_rows(csv_path: str | Path) -> list[dict[str, Any]]:
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"RAG dataset not found: {csv_path}")

    df = pd.read_csv(csv_path)

    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing columns in RAG dataset: {missing_columns}")

    df = df[list(REQUIRED_COLUMNS)].copy()

    df = df.dropna()
    df = df.drop_duplicates()

    return df.to_dict(orient="records")