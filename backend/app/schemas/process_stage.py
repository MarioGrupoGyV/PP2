from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import NonEmptyString


class ProcessStageCreate(BaseModel):
    code: NonEmptyString = Field(max_length=50)
    name: NonEmptyString = Field(max_length=100)
    sequence: int = Field(gt=0)
    sla_hours: int = Field(gt=0)
    active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class ProcessStageUpdate(BaseModel):
    code: NonEmptyString | None = Field(default=None, max_length=50)
    name: NonEmptyString | None = Field(default=None, max_length=100)
    sequence: int | None = Field(default=None, gt=0)
    sla_hours: int | None = Field(default=None, gt=0)
    active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def reject_empty_or_null_patch(self) -> "ProcessStageUpdate":
        values = self.model_dump(exclude_unset=True)
        if not values:
            raise ValueError("At least one field must be provided")
        if any(value is None for value in values.values()):
            raise ValueError("Fields cannot be null")
        return self


class ProcessStageRead(BaseModel):
    id: UUID
    code: str
    name: str
    sequence: int
    sla_hours: int
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
