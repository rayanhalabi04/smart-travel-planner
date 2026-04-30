from pydantic import BaseModel


class RagSearchRequest(BaseModel):
    travel_style: str


class DestinationResult(BaseModel):
    destination_name: str
    country: str


class RagSearchResponse(BaseModel):
    destinations: list[DestinationResult]