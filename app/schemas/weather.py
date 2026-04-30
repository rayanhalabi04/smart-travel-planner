from pydantic import BaseModel, Field


class WeatherResponse(BaseModel):
    city: str
    latitude: float
    longitude: float
    temperature_c: float
    wind_speed_kmh: float | None = None
    weather_code: int | None = None
    source: str = "Open-Meteo"