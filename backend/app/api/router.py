from fastapi import APIRouter

from app.api.routes import commercial_cases, events, health, process_stages

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(
    process_stages.router,
    prefix="/process-stages",
    tags=["process-stages"],
)
api_router.include_router(
    commercial_cases.router,
    prefix="/cases",
    tags=["commercial-cases"],
)
api_router.include_router(events.router, tags=["events"])
