from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.commercial_case import (
    CommercialCaseCreate,
    CommercialCaseList,
    CommercialCaseRead,
)
from app.services import commercial_case_service

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=CommercialCaseList)
def list_commercial_cases(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CommercialCaseList:
    items, total = commercial_case_service.list_commercial_cases(
        db,
        page=page,
        page_size=page_size,
    )
    return CommercialCaseList(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "",
    response_model=CommercialCaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_commercial_case(
    data: CommercialCaseCreate,
    db: DbSession,
) -> CommercialCaseRead:
    return commercial_case_service.create_commercial_case(db, data)


@router.get("/code/{case_code}", response_model=CommercialCaseRead)
def get_commercial_case_by_code(
    case_code: str,
    db: DbSession,
) -> CommercialCaseRead:
    return commercial_case_service.get_commercial_case_by_code(db, case_code)


@router.get("/{case_id}", response_model=CommercialCaseRead)
def get_commercial_case(case_id: UUID, db: DbSession) -> CommercialCaseRead:
    return commercial_case_service.get_commercial_case(db, case_id)
