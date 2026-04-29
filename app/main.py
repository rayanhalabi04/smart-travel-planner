from fastapi import FastAPI

from app.api.routers.health import router as health_router

app = FastAPI(title="Smart Travel Planner")

app.include_router(health_router)
