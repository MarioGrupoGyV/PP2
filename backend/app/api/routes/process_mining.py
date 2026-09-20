from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.process_mining import (
    ActivityStatistic,
    DfgResponse,
    PerformanceResponse,
    ProcessMiningSummary,
    TransitionStatistic,
    VariantCasesResponse,
    VariantStatistic,
)
from app.services import process_mining_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/dfg", response_model=DfgResponse)
def get_dfg(db: DbSession) -> DfgResponse:
    return process_mining_service.get_dfg(db)


@router.get("/performance", response_model=PerformanceResponse)
def get_performance(db: DbSession) -> PerformanceResponse:
    return process_mining_service.get_performance(db)


@router.get("/variants", response_model=list[VariantStatistic])
def get_variants(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[VariantStatistic]:
    return process_mining_service.get_variants(db, limit=limit)


@router.get(
    "/variants/{variant_id}/cases",
    response_model=VariantCasesResponse,
)
def get_variant_cases(
    variant_id: str,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> VariantCasesResponse:
    return process_mining_service.get_variant_cases(
        db,
        variant_id=variant_id,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=ProcessMiningSummary)
def get_summary(db: DbSession) -> ProcessMiningSummary:
    return process_mining_service.get_summary(db)


@router.get("/activities", response_model=list[ActivityStatistic])
def get_activities(db: DbSession) -> list[ActivityStatistic]:
    return process_mining_service.get_activities(db)


@router.get("/transitions", response_model=list[TransitionStatistic])
def get_transitions(db: DbSession) -> list[TransitionStatistic]:
    return process_mining_service.get_transitions(db)
