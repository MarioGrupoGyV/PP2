from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import DeviationSeverity, DeviationType

if TYPE_CHECKING:
    from app.models.commercial_case import CommercialCase
    from app.models.event import Event
    from app.models.process_stage import ProcessStage

json_type = JSON().with_variant(JSONB, "postgresql")


class Deviation(Base):
    __tablename__ = "deviations"
    __table_args__ = (
        Index("ix_deviations_case_id", "case_id"),
        Index("ix_deviations_type", "type"),
        Index("ix_deviations_severity", "severity"),
        Index("ix_deviations_detected_at", "detected_at"),
        Index("uq_deviations_fingerprint", "fingerprint", unique=True),
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
    event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("events.id", ondelete="RESTRICT"),
    )
    stage_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("process_stages.id", ondelete="RESTRICT"),
    )
    type: Mapped[DeviationType] = mapped_column(
        Enum(
            DeviationType,
            name="deviation_type",
            native_enum=True,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    severity: Mapped[DeviationSeverity] = mapped_column(
        Enum(
            DeviationSeverity,
            name="deviation_severity",
            native_enum=True,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    expected_value: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    actual_value: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    details: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    commercial_case: Mapped["CommercialCase"] = relationship(
        back_populates="deviations"
    )
    event: Mapped["Event | None"] = relationship(back_populates="deviations")
    stage: Mapped["ProcessStage | None"] = relationship(back_populates="deviations")
