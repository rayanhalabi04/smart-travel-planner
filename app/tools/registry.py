from typing import Any, Callable

from app.tools.classify_style import TOOL_NAME as CLASSIFY_STYLE_TOOL_NAME
from app.tools.classify_style import classify_style_tool
from app.tools.destination_search import TOOL_NAME as DESTINATION_SEARCH_TOOL_NAME
from app.tools.destination_search import destination_search_tool


ToolFunction = Callable[..., dict[str, Any]]


TOOL_REGISTRY: dict[str, ToolFunction] = {
    CLASSIFY_STYLE_TOOL_NAME: classify_style_tool,
    DESTINATION_SEARCH_TOOL_NAME: destination_search_tool,
}


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "classify_style",
            "description": "Predicts the travel style using the ML classifier.",
            "required_arguments": [
                "avg_daily_cost_usd",
                "avg_hotel_price_usd",
                "tourism_density",
                "hiking_trails",
                "water_sports",
                "beach_quality",
                "historical_sites",
                "museums_galleries",
                "family_friendly_score",
                "luxury_resorts",
                "avg_temp_summer_c",
            ],
        },
        {
            "name": "destination_search",
            "description": "Retrieves destination names and countries by travel style.",
            "required_arguments": ["travel_style"],
        },
    ]


def get_tool(tool_name: str) -> ToolFunction | None:
    return TOOL_REGISTRY.get(tool_name)