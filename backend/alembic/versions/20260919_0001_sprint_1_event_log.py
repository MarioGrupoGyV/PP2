"""Create Sprint 1 commercial event log tables.

Revision ID: 20260919_0001
Revises:
Create Date: 2026-09-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260919_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

case_status_enum = postgresql.ENUM(
    "ACTIVE",
    "CLOSED",
    "CANCELLED",
    name="case_status",
    create_type=False,
)
event_type_enum = postgresql.ENUM(
    "STAGE_CHANGE",
    "INTERACTION",
    "SYSTEM",
    name="event_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    case_status_enum.create(bind, checkfirst=True)
    event_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "process_stages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("sla_hours", sa.Integer(), nullable=False),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "sequence > 0",
            name="ck_process_stages_sequence_positive",
        ),
        sa.CheckConstraint(
            "sla_hours > 0",
            name="ck_process_stages_sla_hours_positive",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_process_stages"),
    )
    op.create_index(
        "uq_process_stages_code",
        "process_stages",
        ["code"],
        unique=True,
    )
    op.create_index(
        "uq_process_stages_sequence",
        "process_stages",
        ["sequence"],
        unique=True,
    )

    op.create_table(
        "commercial_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_code", sa.String(length=100), nullable=False),
        sa.Column("current_stage_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_resource", sa.String(length=150), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("status", case_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["current_stage_id"],
            ["process_stages.id"],
            name="fk_commercial_cases_current_stage_id_process_stages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_commercial_cases"),
    )
    op.create_index(
        "uq_commercial_cases_case_code",
        "commercial_cases",
        ["case_code"],
        unique=True,
    )
    op.create_index(
        "ix_commercial_cases_current_stage_id",
        "commercial_cases",
        ["current_stage_id"],
        unique=False,
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("stage_id", sa.Uuid(), nullable=False),
        sa.Column("activity", sa.String(length=200), nullable=False),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("resource", sa.String(length=150), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["commercial_cases.id"],
            name="fk_events_case_id_commercial_cases",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["process_stages.id"],
            name="fk_events_stage_id_process_stages",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index(
        "ix_events_timestamp",
        "events",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_events_case_id_timestamp",
        "events",
        ["case_id", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("events")
    op.drop_table("commercial_cases")
    op.drop_table("process_stages")

    bind = op.get_bind()
    event_type_enum.drop(bind, checkfirst=True)
    case_status_enum.drop(bind, checkfirst=True)
