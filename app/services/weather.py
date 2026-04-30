import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.schemas.weather import WeatherResponse


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    reraise=True,
)
async def get_weather_for_city(city: str) -> WeatherResponse:
    async with httpx.AsyncClient(timeout=10.0) as client:
        geo_response = await client.get(
            GEOCODING_URL,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()

        results = geo_data.get("results", [])

        if not results:
            raise ValueError(f"City not found: {city}")

        location = results[0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        resolved_city = location["name"]

        weather_response = await client.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m,weather_code",
            },
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        current = weather_data["current"]

        return WeatherResponse(
            city=resolved_city,
            latitude=latitude,
            longitude=longitude,
            temperature_c=current["temperature_2m"],
            wind_speed_kmh=current.get("wind_speed_10m"),
            weather_code=current.get("weather_code"),
        )