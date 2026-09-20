from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import CaseStatus

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.process_stage import ProcessStage


class CommercialCase(Base):
    __tablename__ = "commercial_cases"
    __table_args__ = (
        Index("uq_commercial_cases_case_code", "case_code", unique=True),
        Index("ix_commercial_cases_current_stage_id", "current_stage_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_code: Mapped[str] = mapped_column(String(100), nullable=False)
    current_stage_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("process_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_resource: Mapped[str | None] = mapped_column(String(150))
    source: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[CaseStatus] = mapped_column(
        Enum(
            CaseStatus,
            name="case_status",
            native_enum=True,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    current_stage: Mapped["ProcessStage"] = relationship(
        back_populates="commercial_cases",
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="commercial_case",
        passive_deletes=True,
    )
