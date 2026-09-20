import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.health import DatabaseHealthResponse, HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=HealthResponse)
def check_health() -> HealthResponse:
    return HealthResponse(status="ok", service="backend")


@router.get("/database", response_model=DatabaseHealthResponse)
def check_database(
    db: Annotated[Session, Depends(get_db)],
) -> DatabaseHealthResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        ) from exc

    return DatabaseHealthResponse(status="ok", database="connected")
