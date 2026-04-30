import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db.models import Base
from app.db.session import create_engine, create_session_maker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    logger.info("Starting %s", settings.app_name)

    app.state.settings = settings

    app.state.db_engine = create_engine(settings)
    app.state.session_maker = create_session_maker(app.state.db_engine)

    # Create tables automatically for now
    async with app.state.db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.model = None
    app.state.embedder = None
    app.state.http_client = None
    app.state.llm_client = None

    try:
        yield
    finally:
        await app.state.db_engine.dispose()
        logger.info("Shutting down %s", settings.app_name)