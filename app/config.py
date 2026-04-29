from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # App
    app_name: str = "Smart Travel Planner"
    app_env: str = "development"
    debug: bool = True

    # API
    api_prefix: str = "/api"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/smart_travel_planner"
    )

    # Auth
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # LLM models
    cheap_model: str = "gpt-4o-mini"
    strong_model: str = "gpt-4o"

    # Paths
    project_root: Path = Path(__file__).resolve().parent.parent
    model_path: Path = project_root / "app" / "ml" / "artifacts" / "best_travel_style_model.pkl"

    # RAG
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_top_k: int = 5

    # Weather
    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_cache_ttl_seconds: int = 600

    # Webhook
    webhook_timeout_seconds: float = 10.0
    webhook_max_retries: int = 3

    # Logging
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()