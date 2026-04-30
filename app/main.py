from fastapi import FastAPI
from app.api.routers.auth import router as auth_router
from app.api.routers.health import router as health_router

from app.config import get_settings
from app.lifespan import lifespan
from app.utils.logging import setup_logging

settings = get_settings()

setup_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)

@app.get("/")
async def root() -> dict[str, str]:
    return {"message": settings.app_name}