from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RiskLevel

if TYPE_CHECKING:
    from app.models.commercial_case import CommercialCase
    from app.models.event import Event
    from app.models.ml_model_run import MlModelRun

json_type = JSON().with_variant(JSONB, "postgresql")


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint(
            "risk_score >= 0 AND risk_score <= 1",
            name="ck_predictions_risk_score_range",
        ),
        Index("ix_predictions_case_id", "case_id"),
        Index("ix_predictions_model_run_id", "model_run_id"),
        Index("ix_predictions_predicted_at", "predicted_at"),
        Index("ix_predictions_risk_level", "risk_level"),
        Index("uq_predictions_fingerprint", "prediction_fingerprint", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("commercial_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_model_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_event_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("events.id", ondelete="RESTRICT")
    )
    snapshot_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prediction_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(
            RiskLevel,
            name="risk_level",
            native_enum=True,
            validate_strings=True,
            create_constraint=True,
        ),
        nullable=False,
    )
    features: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    explanation: Mapped[list[dict[str, Any]]] = mapped_column(json_type, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    commercial_case: Mapped["CommercialCase"] = relationship(back_populates="predictions")
    model_run: Mapped["MlModelRun"] = relationship(back_populates="predictions")
    snapshot_event: Mapped["Event | None"] = relationship(back_populates="snapshot_predictions")
