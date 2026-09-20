"""Add predictive operational alerts and their audit trail.

Revision ID: 20260920_0005
Revises: 20260920_0004
Create Date: 2026-09-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260920_0005"
down_revision: str | Sequence[str] | None = "20260920_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

alert_status = postgresql.ENUM(
    "ACTIVE", "ATTENDED", "RESOLVED", "DISMISSED", name="alert_status", create_type=False
)
alert_evaluation_mode = postgresql.ENUM(
    "LATEST_OBSERVATION", "HISTORICAL_REPLAY", name="alert_evaluation_mode", create_type=False
)
alert_action_type = postgresql.ENUM(
    "CREATED", "ATTENDED", "NOTE", "RISK_REEVALUATED", "RESOLVED", "DISMISSED",
    name="alert_action_type", create_type=False,
)
risk_level = postgresql.ENUM("LOW", "MEDIUM", "HIGH", name="risk_level", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("ACTIVE", "ATTENDED", "RESOLVED", "DISMISSED", name="alert_status").create(bind)
    postgresql.ENUM(
        "LATEST_OBSERVATION", "HISTORICAL_REPLAY", name="alert_evaluation_mode"
    ).create(bind)
    postgresql.ENUM(
        "CREATED", "ATTENDED", "NOTE", "RISK_REEVALUATED", "RESOLVED", "DISMISSED",
        name="alert_action_type",
    ).create(bind)
    op.execute(sa.schema.CreateSequence(sa.Sequence("alert_code_seq", start=1)))

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "alert_code",
            sa.String(length=20),
            server_default=sa.text("'ALR-' || lpad(nextval('alert_code_seq')::text, 6, '0')"),
            nullable=False,
        ),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("origin_prediction_id", sa.Uuid(), nullable=False),
        sa.Column("latest_prediction_id", sa.Uuid(), nullable=False),
        sa.Column("status", alert_status, nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("evaluation_mode", alert_evaluation_mode, nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_alerts_risk_score_range"),
        sa.ForeignKeyConstraint(["case_id"], ["commercial_cases.id"], name="fk_alerts_case_id_commercial_cases", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["origin_prediction_id"], ["predictions.id"], name="fk_alerts_origin_prediction_id_predictions", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["latest_prediction_id"], ["predictions.id"], name="fk_alerts_latest_prediction_id_predictions", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
    )
    op.create_index("uq_alerts_alert_code", "alerts", ["alert_code"], unique=True)
    op.create_index("uq_alerts_fingerprint", "alerts", ["fingerprint"], unique=True)
    op.create_index("ix_alerts_case_id", "alerts", ["case_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_risk_level", "alerts", ["risk_level"])
    op.create_index("ix_alerts_triggered_at", "alerts", ["triggered_at"])
    op.create_index("ix_alerts_latest_prediction_id", "alerts", ["latest_prediction_id"])
    op.create_index(
        "uq_alerts_one_open_per_case",
        "alerts",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('ACTIVE', 'ATTENDED')"),
    )

    op.create_table(
        "alert_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", alert_action_type, nullable=False),
        sa.Column("actor", sa.String(length=150), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("previous_status", alert_status, nullable=True),
        sa.Column("new_status", alert_status, nullable=True),
        sa.Column("prediction_id", sa.Uuid(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], name="fk_alert_actions_alert_id_alerts", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"], name="fk_alert_actions_prediction_id_predictions", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_alert_actions"),
    )
    op.create_index("ix_alert_actions_alert_id", "alert_actions", ["alert_id"])
    op.create_index("ix_alert_actions_created_at", "alert_actions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_actions_created_at", table_name="alert_actions")
    op.drop_index("ix_alert_actions_alert_id", table_name="alert_actions")
    op.drop_table("alert_actions")
    op.drop_index("uq_alerts_one_open_per_case", table_name="alerts")
    op.drop_index("ix_alerts_latest_prediction_id", table_name="alerts")
    op.drop_index("ix_alerts_triggered_at", table_name="alerts")
    op.drop_index("ix_alerts_risk_level", table_name="alerts")
    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_case_id", table_name="alerts")
    op.drop_index("uq_alerts_fingerprint", table_name="alerts")
    op.drop_index("uq_alerts_alert_code", table_name="alerts")
    op.drop_table("alerts")
    op.execute(sa.schema.DropSequence(sa.Sequence("alert_code_seq")))
    bind = op.get_bind()
    postgresql.ENUM(name="alert_action_type").drop(bind)
    postgresql.ENUM(name="alert_evaluation_mode").drop(bind)
    postgresql.ENUM(name="alert_status").drop(bind)
