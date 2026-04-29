import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logger.info("Starting %s", settings.app_name)

    app.state.settings = settings
    app.state.ml_model = None
    app.state.llm_client = None
    app.state.vector_store = None

    yield

    logger.info("Shutting down %s", settings.app_name)
