from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EventType
from app.schemas.common import NonEmptyString


class EventCreate(BaseModel):
    stage_id: UUID
    activity: NonEmptyString = Field(max_length=200)
    event_type: EventType
    resource: NonEmptyString | None = Field(default=None, max_length=150)
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventRead(BaseModel):
    id: UUID
    case_id: UUID
    stage_id: UUID
    activity: str
    event_type: EventType
    resource: str | None
    timestamp: datetime
    metadata: dict[str, Any] = Field(validation_alias="metadata_")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventList(BaseModel):
    items: list[EventRead]
    page: int
    page_size: int
    total: int
