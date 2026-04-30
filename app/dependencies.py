from collections.abc import AsyncGenerator
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings


def get_app_settings() -> Settings:
    return get_settings()


def _get_state_value(request: Request, name: str) -> Any:
    value = getattr(request.app.state, name, None)

    if value is None:
        raise HTTPException(
            status_code=500,
            detail=f"Application dependency '{name}' is not initialized.",
        )

    return value


def get_ml_model(request: Request) -> Any:
    return _get_state_value(request, "model")


def get_embedder(request: Request) -> Any:
    return _get_state_value(request, "embedder")


def get_http_client(request: Request) -> Any:
    return _get_state_value(request, "http_client")


def get_llm_client(request: Request) -> Any:
    return _get_state_value(request, "llm_client")


def get_db_engine(request: Request) -> Any:
    return _get_state_value(request, "db_engine")


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_maker = _get_state_value(request, "session_maker")

    async with session_maker() as session:
        yield session