"""Add predictive model runs and case predictions.

Revision ID: 20260920_0004
Revises: 20260920_0003
Create Date: 2026-09-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260920_0004"
down_revision: str | Sequence[str] | None = "20260920_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

risk_level = sa.Enum("LOW", "MEDIUM", "HIGH", name="risk_level")


def upgrade() -> None:
    op.create_table(
        "ml_model_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("algorithm", sa.String(length=50), nullable=False),
        sa.Column("target_name", sa.String(length=50), nullable=False),
        sa.Column("feature_schema_version", sa.String(length=50), nullable=False),
        sa.Column("dataset_hash", sa.String(length=64), nullable=False),
        sa.Column("decision_threshold", sa.Float(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("hyperparameters", postgresql.JSONB(), nullable=False),
        sa.Column("training_summary", postgresql.JSONB(), nullable=False),
        sa.Column("artifact_path", sa.String(length=500), nullable=False),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("decision_threshold >= 0 AND decision_threshold <= 1", name="ck_ml_model_runs_decision_threshold_range"),
        sa.PrimaryKeyConstraint("id", name="pk_ml_model_runs"),
    )
    op.create_index("uq_ml_model_runs_model_version", "ml_model_runs", ["model_version"], unique=True)
    op.create_index("ix_ml_model_runs_is_active", "ml_model_runs", ["is_active"])
    op.create_index("uq_ml_model_runs_single_active", "ml_model_runs", ["is_active"], unique=True, postgresql_where=sa.text("is_active"))

    op.create_table(
        "predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("model_run_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_event_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prediction_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("predicted_label", sa.Boolean(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_predictions_risk_score_range"),
        sa.ForeignKeyConstraint(["case_id"], ["commercial_cases.id"], name="fk_predictions_case_id_commercial_cases", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["model_run_id"], ["ml_model_runs.id"], name="fk_predictions_model_run_id_ml_model_runs", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["snapshot_event_id"], ["events.id"], name="fk_predictions_snapshot_event_id_events", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_predictions"),
    )
    op.create_index("ix_predictions_case_id", "predictions", ["case_id"])
    op.create_index("ix_predictions_model_run_id", "predictions", ["model_run_id"])
    op.create_index("ix_predictions_predicted_at", "predictions", ["predicted_at"])
    op.create_index("ix_predictions_risk_level", "predictions", ["risk_level"])
    op.create_index("uq_predictions_fingerprint", "predictions", ["prediction_fingerprint"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_predictions_fingerprint", table_name="predictions")
    op.drop_index("ix_predictions_risk_level", table_name="predictions")
    op.drop_index("ix_predictions_predicted_at", table_name="predictions")
    op.drop_index("ix_predictions_model_run_id", table_name="predictions")
    op.drop_index("ix_predictions_case_id", table_name="predictions")
    op.drop_table("predictions")
    risk_level.drop(op.get_bind(), checkfirst=True)
    op.drop_index("uq_ml_model_runs_single_active", table_name="ml_model_runs")
    op.drop_index("ix_ml_model_runs_is_active", table_name="ml_model_runs")
    op.drop_index("uq_ml_model_runs_model_version", table_name="ml_model_runs")
    op.drop_table("ml_model_runs")
