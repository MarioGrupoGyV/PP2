"""Add Event Log import traceability.

Revision ID: 20260919_0002
Revises: 20260919_0001
Create Date: 2026-09-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260919_0002"
down_revision: str | Sequence[str] | None = "20260919_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_log_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("imported_cases", sa.Integer(), nullable=False),
        sa.Column("imported_events", sa.Integer(), nullable=False),
        sa.Column("skipped_duplicates", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_log_imports"),
    )
    op.create_index(
        "uq_event_log_imports_file_sha256",
        "event_log_imports",
        ["file_sha256"],
        unique=True,
    )
    op.create_index(
        "ix_event_log_imports_created_at",
        "event_log_imports",
        ["created_at"],
        unique=False,
    )

    op.add_column("events", sa.Column("import_id", sa.Uuid(), nullable=True))
    op.add_column(
        "events",
        sa.Column("source_row_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column("event_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_events_import_id_event_log_imports",
        "events",
        "event_log_imports",
        ["import_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_events_import_id", "events", ["import_id"], unique=False)
    op.create_index(
        "uq_events_event_fingerprint",
        "events",
        ["event_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_events_event_fingerprint", table_name="events")
    op.drop_index("ix_events_import_id", table_name="events")
    op.drop_constraint(
        "fk_events_import_id_event_log_imports",
        "events",
        type_="foreignkey",
    )
    op.drop_column("events", "event_fingerprint")
    op.drop_column("events", "source_row_number")
    op.drop_column("events", "import_id")

    op.drop_table("event_log_imports")
