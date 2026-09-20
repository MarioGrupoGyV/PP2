from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import CaseStatus
from app.schemas.common import NonEmptyString


class CommercialCaseCreate(BaseModel):
    case_code: NonEmptyString = Field(max_length=100)
    current_stage_id: UUID
    assigned_resource: NonEmptyString | None = Field(default=None, max_length=150)
    source: NonEmptyString | None = Field(default=None, max_length=100)
    status: CaseStatus
    started_at: datetime
    closed_at: datetime | None = None

    @field_validator("case_code")
    @classmethod
    def normalize_case_code(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_dates(self) -> "CommercialCaseCreate":
        if self.closed_at is None:
            return self
        try:
            if self.closed_at < self.started_at:
                raise ValueError("closed_at cannot be earlier than started_at")
        except TypeError as exc:
            raise ValueError(
                "started_at and closed_at must use compatible time zones"
            ) from exc
        return self


class CommercialCaseRead(BaseModel):
    id: UUID
    case_code: str
    current_stage_id: UUID
    assigned_resource: str | None
    source: str | None
    status: CaseStatus
    started_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommercialCaseList(BaseModel):
    items: list[CommercialCaseRead]
    page: int
    page_size: int
    total: int
