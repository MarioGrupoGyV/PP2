from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmptyInput(StrictToolInput):
    pass


class CaseCodeInput(StrictToolInput):
    case_code: str = Field(min_length=1, max_length=100)

    @field_validator("case_code")
    @classmethod
    def normalize_case_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("case_code no puede estar vacío")
        return normalized


class CaseListInput(CaseCodeInput):
    limit: int = Field(default=20, ge=1, le=50)


class VariantListInput(StrictToolInput):
    limit: int = Field(default=5, ge=1, le=20)


class TransitionListInput(StrictToolInput):
    limit: int = Field(default=5, ge=1, le=50)
    sort_by: Literal["frequency", "average_duration"] = "frequency"
