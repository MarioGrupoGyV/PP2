from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Float, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.prediction import Prediction

json_type = JSON().with_variant(JSONB, "postgresql")


class MlModelRun(Base):
    __tablename__ = "ml_model_runs"
    __table_args__ = (
        CheckConstraint(
            "decision_threshold >= 0 AND decision_threshold <= 1",
            name="ck_ml_model_runs_decision_threshold_range",
        ),
        Index("uq_ml_model_runs_model_version", "model_version", unique=True),
        Index("ix_ml_model_runs_is_active", "is_active"),
        Index(
            "uq_ml_model_runs_single_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active = 1"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    target_name: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    hyperparameters: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    training_summary: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="model_run", passive_deletes=True
    )
