from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EventType

if TYPE_CHECKING:
    from app.models.commercial_case import CommercialCase
    from app.models.deviation import Deviation
    from app.models.event_log_import import EventLogImport
    from app.models.process_stage import ProcessStage

metadata_type = JSON().with_variant(JSONB, "postgresql")


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_timestamp", "timestamp"),
        Index("ix_events_case_id_timestamp", "case_id", "timestamp"),
        Index("ix_events_import_id", "import_id"),
        Index("uq_events_event_fingerprint", "event_fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("commercial_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    stage_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("process_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    import_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("event_log_imports.id", ondelete="RESTRICT"),
    )
    source_row_number: Mapped[int | None]
    event_fingerprint: Mapped[str | None] = mapped_column(String(64))
    activity: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[EventType] = mapped_column(
        Enum(
            EventType,
            name="event_type",
            native_enum=True,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    resource: Mapped[str | None] = mapped_column(String(150))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        metadata_type,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    commercial_case: Mapped["CommercialCase"] = relationship(
        back_populates="events",
    )
    stage: Mapped["ProcessStage"] = relationship(back_populates="events")
    event_log_import: Mapped["EventLogImport | None"] = relationship(
        back_populates="events"
    )
    deviations: Mapped[list["Deviation"]] = relationship(
        back_populates="event",
        passive_deletes=True,
    )
