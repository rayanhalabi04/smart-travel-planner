from typing import Any

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any]


class ToolCallResponse(BaseModel):
    tool_name: str
    result: dict[str, Any]


class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: str
    required_arguments: list[str]


class DestinationSearchToolInput(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)
    travel_style: str | None = None


class ClassifyStyleToolInput(BaseModel):
    avg_daily_cost_usd: float
    avg_hotel_price_usd: float
    tourism_density: float
    hiking_trails: float
    water_sports: float
    beach_quality: float
    historical_sites: float
    museums_galleries: float
    family_friendly_score: float
    luxury_resorts: float
    avg_temp_summer_c: float
