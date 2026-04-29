from typing import Any

from fastapi import Request

from app.config import Settings, get_settings


def get_app_settings() -> Settings:
    return get_settings()


def get_ml_model(request: Request) -> Any:
    return request.app.state.model


def get_embedder(request: Request) -> Any:
    return request.app.state.embedder


def get_http_client(request: Request) -> Any:
    return request.app.state.http_client


def get_llm_client(request: Request) -> Any:
    return request.app.state.llm_client


def get_db_engine(request: Request) -> Any:
    return request.app.state.db_engine