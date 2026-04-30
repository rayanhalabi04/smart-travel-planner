from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.schemas.tools import ClassifyStyleToolInput, DestinationSearchToolInput
from app.tools.classify_style import TOOL_NAME as CLASSIFY_STYLE_TOOL_NAME
from app.tools.classify_style import classify_style_tool
from app.tools.destination_search import TOOL_NAME as DESTINATION_SEARCH_TOOL_NAME
from app.tools.destination_search import destination_search_tool
from app.tools.weather_tool import WeatherToolInput, weather_tool


ToolFunction = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    function: ToolFunction
    input_schema: type[BaseModel]


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    "weather": ToolDefinition(
        name="weather",
        description="Fetches live weather conditions for a city.",
        function=weather_tool,
        input_schema=WeatherToolInput,
    ),
    DESTINATION_SEARCH_TOOL_NAME: ToolDefinition(
        name=DESTINATION_SEARCH_TOOL_NAME,
        description=(
            "Retrieves destination knowledge and ranked candidates from RAG "
            "based on query/style."
        ),
        function=destination_search_tool,
        input_schema=DestinationSearchToolInput,
    ),
    CLASSIFY_STYLE_TOOL_NAME: ToolDefinition(
        name=CLASSIFY_STYLE_TOOL_NAME,
        description="Predicts the travel style using the trained ML classifier.",
        function=classify_style_tool,
        input_schema=ClassifyStyleToolInput,
    ),
}


def list_tools() -> list[dict[str, Any]]:
    tools = []
    for definition in TOOL_REGISTRY.values():
        required_arguments = [
            field_name
            for field_name, field_info in definition.input_schema.model_fields.items()
            if field_info.is_required()
        ]
        tools.append(
            {
                "name": definition.name,
                "description": definition.description,
                "input_schema": definition.input_schema.__name__,
                "required_arguments": required_arguments,
            }
        )
    return tools


def get_tool(tool_name: str) -> ToolDefinition | None:
    return TOOL_REGISTRY.get(tool_name)


def is_tool_allowed(tool_name: str) -> bool:
    return tool_name in TOOL_REGISTRY
