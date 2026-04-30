from pydantic import BaseModel


class TravelStyleRequest(BaseModel):
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


class TravelStyleResponse(BaseModel):
    predicted_style: str