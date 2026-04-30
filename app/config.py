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

    # LLM / OpenAI
    # Optional for now, so the backend can run even if you do not use OpenAI yet
    openai_api_key: str | None = None
    cheap_model: str = "gpt-4o-mini"
    strong_model: str = "gpt-4o"

    # Frontend / CORS
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Project paths
    project_root: Path = Path(__file__).resolve().parent.parent

    # ML paths
    # Main name used by lifespan.py
    ml_model_path: Path = (
        project_root / "app" / "ml" / "artifacts" / "travel_style_classifier.pkl"
    )

    feature_columns_path: Path = (
        project_root / "app" / "ml" / "artifacts" / "feature_columns.pkl"
    )

    # Backward-compatible name in case some older ML code uses settings.model_path
    model_path: Path = ml_model_path

    # RAG
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_top_k: int = 5
    chroma_path: Path = project_root / "chroma_db"
    chroma_collection_name: str = "destinations"

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