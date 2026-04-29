from fastapi import FastAPI

from app.api.routers.health import router as health_router
from app.config import get_settings
from app.lifespan import lifespan
from app.utils.logging import setup_logging

setup_logging()
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

app.include_router(health_router)
