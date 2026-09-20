from fastapi import APIRouter

from app.api.routes import (
    commercial_cases,
    event_log,
    events,
    health,
    imports,
    process_mining,
    process_stages,
    deviations,
)

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
api_router.include_router(imports.router, prefix="/imports", tags=["imports"])
api_router.include_router(event_log.router, prefix="/event-log", tags=["event-log"])
api_router.include_router(deviations.router, tags=["deviations"])
api_router.include_router(
    process_mining.router,
    prefix="/process-mining",
    tags=["process-mining"],
)
