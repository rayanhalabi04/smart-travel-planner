from typing import Any

from pydantic import BaseModel, Field

from app.schemas.weather import WeatherResponse
from app.services.weather import get_weather_for_city


class WeatherToolInput(BaseModel):
    city: str = Field(..., min_length=1)


class WeatherToolOutput(BaseModel):
    tool_name: str = "weather"
    city: str
    result: WeatherResponse


async def weather_tool(
    payload: WeatherToolInput,
    **kwargs: Any,
) -> dict[str, Any]:
    weather = await get_weather_for_city(payload.city.strip())

    output = WeatherToolOutput(
        city=payload.city,
        result=weather,
    )

    return output.model_dump()
