from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, Float, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AlertActionType, AlertEvaluationMode, AlertStatus, RiskLevel

if TYPE_CHECKING:
    from app.models.commercial_case import CommercialCase
    from app.models.prediction import Prediction

json_type = JSON().with_variant(JSONB, "postgresql")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_alerts_risk_score_range"),
        Index("uq_alerts_alert_code", "alert_code", unique=True),
        Index("uq_alerts_fingerprint", "fingerprint", unique=True),
        Index("ix_alerts_case_id", "case_id"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_risk_level", "risk_level"),
        Index("ix_alerts_triggered_at", "triggered_at"),
        Index("ix_alerts_latest_prediction_id", "latest_prediction_id"),
        Index(
            "uq_alerts_one_open_per_case",
            "case_id",
            unique=True,
            postgresql_where=text("status IN ('ACTIVE', 'ATTENDED')"),
            sqlite_where=text("status IN ('ACTIVE', 'ATTENDED')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    alert_code: Mapped[str] = mapped_column(String(20), nullable=False)
    case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("commercial_cases.id", ondelete="RESTRICT"), nullable=False
    )
    origin_prediction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("predictions.id", ondelete="RESTRICT"), nullable=False
    )
    latest_prediction_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("predictions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status", native_enum=True, validate_strings=True), nullable=False
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level", native_enum=True, validate_strings=True, create_type=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    evaluation_mode: Mapped[AlertEvaluationMode] = mapped_column(
        Enum(
            AlertEvaluationMode,
            name="alert_evaluation_mode",
            native_enum=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    commercial_case: Mapped["CommercialCase"] = relationship(back_populates="alerts")
    origin_prediction: Mapped["Prediction"] = relationship(foreign_keys=[origin_prediction_id])
    latest_prediction: Mapped["Prediction"] = relationship(foreign_keys=[latest_prediction_id])
    actions: Mapped[list["AlertAction"]] = relationship(
        back_populates="alert", passive_deletes=True, order_by="AlertAction.created_at"
    )


class AlertAction(Base):
    __tablename__ = "alert_actions"
    __table_args__ = (
        Index("ix_alert_actions_alert_id", "alert_id"),
        Index("ix_alert_actions_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=False
    )
    action_type: Mapped[AlertActionType] = mapped_column(
        Enum(AlertActionType, name="alert_action_type", native_enum=True, validate_strings=True),
        nullable=False,
    )
    actor: Mapped[str | None] = mapped_column(String(150))
    notes: Mapped[str | None] = mapped_column(String(1000))
    previous_status: Mapped[AlertStatus | None] = mapped_column(
        Enum(AlertStatus, name="alert_status", native_enum=True, validate_strings=True, create_type=False)
    )
    new_status: Mapped[AlertStatus | None] = mapped_column(
        Enum(AlertStatus, name="alert_status", native_enum=True, validate_strings=True, create_type=False)
    )
    prediction_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("predictions.id", ondelete="RESTRICT")
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(json_type)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    alert: Mapped["Alert"] = relationship(back_populates="actions")
    prediction: Mapped["Prediction | None"] = relationship()
