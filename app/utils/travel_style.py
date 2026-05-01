import re


ALLOWED_TRAVEL_STYLE_LABELS = (
    "Adventure",
    "Relaxation",
    "Culture",
    "Budget",
    "Luxury",
    "Family",
)


_STYLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Adventure", ("adventure", "hiking", "nature", "outdoor")),
    ("Relaxation", ("relaxation", "beach", "calm", "wellness", "chill")),
    ("Culture", ("culture", "cultural", "history", "museum", "museums", "temples", "heritage")),
    ("Budget", ("budget", "cheap", "affordable", "low cost")),
    ("Luxury", ("luxury", "premium", "high-end", "resort", "resorts")),
    ("Family", ("family", "kids", "children", "young kids", "theme park", "theme parks")),
)


def _to_searchable_text(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def normalize_travel_style(value: str | None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None

    searchable = _to_searchable_text(value)
    if not searchable:
        return None

    padded = f" {searchable} "

    for label, keywords in _STYLE_KEYWORDS:
        for keyword in keywords:
            searchable_keyword = _to_searchable_text(keyword)
            if f" {searchable_keyword} " in padded:
                return label

    return None
