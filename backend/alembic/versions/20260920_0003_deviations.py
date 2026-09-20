"""Add detected process deviations.

Revision ID: 20260920_0003
Revises: 20260919_0002
Create Date: 2026-09-20
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260920_0003"
down_revision: str | Sequence[str] | None = "20260919_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

deviation_type = sa.Enum(
    "SLA_BREACH",
    "STAGE_SKIP",
    "BACKTRACK",
    "REWORK",
    "INACTIVITY",
    name="deviation_type",
)
deviation_severity = sa.Enum(
    "LOW",
    "MEDIUM",
    "HIGH",
    name="deviation_severity",
)


def upgrade() -> None:
    op.create_table(
        "deviations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("stage_id", sa.Uuid(), nullable=True),
        sa.Column("type", deviation_type, nullable=False),
        sa.Column("severity", deviation_severity, nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("expected_value", postgresql.JSONB(), nullable=True),
        sa.Column("actual_value", postgresql.JSONB(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["commercial_cases.id"],
            name="fk_deviations_case_id_commercial_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_deviations_event_id_events",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["process_stages.id"],
            name="fk_deviations_stage_id_process_stages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deviations"),
    )
    op.create_index("ix_deviations_case_id", "deviations", ["case_id"])
    op.create_index("ix_deviations_type", "deviations", ["type"])
    op.create_index("ix_deviations_severity", "deviations", ["severity"])
    op.create_index(
        "ix_deviations_detected_at",
        "deviations",
        ["detected_at"],
    )
    op.create_index(
        "uq_deviations_fingerprint",
        "deviations",
        ["fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_deviations_fingerprint", table_name="deviations")
    op.drop_index("ix_deviations_detected_at", table_name="deviations")
    op.drop_index("ix_deviations_severity", table_name="deviations")
    op.drop_index("ix_deviations_type", table_name="deviations")
    op.drop_index("ix_deviations_case_id", table_name="deviations")
    op.drop_table("deviations")
    deviation_severity.drop(op.get_bind(), checkfirst=True)
    deviation_type.drop(op.get_bind(), checkfirst=True)
