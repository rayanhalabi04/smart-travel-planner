from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.weather import WeatherResponse
from app.services.weather import get_weather_for_city

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("", response_model=WeatherResponse)
async def get_weather(
    city: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
) -> WeatherResponse:
    try:
        return await get_weather_for_city(city)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather service is temporarily unavailable.",
        ) from exc