from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.commercial_case import CommercialCase
    from app.models.event import Event


class ProcessStage(Base):
    __tablename__ = "process_stages"
    __table_args__ = (
        CheckConstraint("sequence > 0", name="ck_process_stages_sequence_positive"),
        CheckConstraint("sla_hours > 0", name="ck_process_stages_sla_hours_positive"),
        Index("uq_process_stages_code", "code", unique=True),
        Index("uq_process_stages_sequence", "sequence", unique=True),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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

    commercial_cases: Mapped[list["CommercialCase"]] = relationship(
        back_populates="current_stage",
        passive_deletes=True,
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="stage",
        passive_deletes=True,
    )
