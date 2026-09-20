from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.event import Event


class EventLogImport(Base):
    __tablename__ = "event_log_imports"
    __table_args__ = (
        Index("uq_event_log_imports_file_sha256", "file_sha256", unique=True),
        Index("ix_event_log_imports_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_events: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    events: Mapped[list["Event"]] = relationship(
        back_populates="event_log_import",
        passive_deletes=True,
    )
