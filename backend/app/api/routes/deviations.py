from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import DeviationSeverity, DeviationType
from app.schemas.deviation import (
    AnalyzeDeviationsResult,
    CaseConformance,
    ConformanceSummary,
    DeviationList,
    DeviationRead,
    DeviationSummary,
)
from app.services import deviation_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/deviations/analyze", response_model=AnalyzeDeviationsResult)
def analyze_deviations(db: DbSession) -> AnalyzeDeviationsResult:
    return deviation_service.analyze(db)


@router.get("/deviations/summary", response_model=DeviationSummary)
def get_deviation_summary(db: DbSession) -> DeviationSummary:
    return deviation_service.get_summary(db)


@router.get("/deviations/conformance", response_model=ConformanceSummary)
def get_conformance_summary(db: DbSession) -> ConformanceSummary:
    return deviation_service.get_conformance_summary(db)


@router.get("/deviations", response_model=DeviationList)
def list_deviations(
    db: DbSession,
    deviation_type: Annotated[DeviationType | None, Query(alias="type")] = None,
    severity: DeviationSeverity | None = None,
    case_code: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DeviationList:
    return deviation_service.list_deviations(
        db, deviation_type=deviation_type, severity=severity, case_code=case_code,
        page=page, page_size=page_size,
    )


@router.get("/deviations/{deviation_id}", response_model=DeviationRead)
def get_deviation(deviation_id: UUID, db: DbSession) -> DeviationRead:
    return deviation_service.get_deviation(db, deviation_id)


@router.get("/cases/{case_id}/deviations", response_model=list[DeviationRead])
def get_case_deviations(case_id: UUID, db: DbSession) -> list[DeviationRead]:
    return deviation_service.get_case_deviations(db, case_id)


@router.get("/cases/{case_id}/conformance", response_model=CaseConformance)
def get_case_conformance(case_id: UUID, db: DbSession) -> CaseConformance:
    return deviation_service.get_case_conformance(db, case_id)
