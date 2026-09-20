from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commercial_case import CommercialCase
from app.models.event import Event
from app.models.event_log_import import EventLogImport
from app.models.process_stage import ProcessStage
from scripts.seed_process_stages import seed_process_stages
from tests.csv_helpers import build_csv, event_row


def upload_preview(client: TestClient, content: bytes, filename: str = "events.csv"):
    return client.post(
        "/api/v1/imports/preview",
        files={"file": (filename, content, "text/csv")},
    )


def test_valid_preview_does_not_persist(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = build_csv(
        [
            event_row(),
            event_row(
                stage_code="CONTACTED",
                activity="Lead contactado",
                timestamp="2026-09-01T10:00:00-05:00",
                metadata='{"channel":"whatsapp"}',
            ),
        ]
    )

    response = upload_preview(client, content)

    assert response.status_code == 200
    assert response.json()["can_import"] is True
    assert response.json()["total_rows"] == 2
    assert response.json()["valid_rows"] == 2
    assert response.json()["invalid_rows"] == 0
    assert db_session.scalar(select(func.count()).select_from(CommercialCase)) == 0
    assert db_session.scalar(select(func.count()).select_from(Event)) == 0
    assert db_session.scalar(select(func.count()).select_from(EventLogImport)) == 0


def test_preview_rejects_empty_file(client: TestClient) -> None:
    response = upload_preview(client, b"")

    assert response.status_code == 422
    assert response.json() == {"detail": "El archivo CSV está vacío"}


def test_preview_rejects_non_csv_extension(client: TestClient) -> None:
    response = upload_preview(client, b"case_code\nCASE-001\n", "events.txt")

    assert response.status_code == 422


def test_preview_rejects_file_over_10_mb(client: TestClient) -> None:
    response = upload_preview(client, b"x" * (10 * 1024 * 1024 + 1))

    assert response.status_code == 413


def test_preview_reports_missing_required_column(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = b"case_code,stage_code,activity\nCASE-1,LEAD,Lead\n"

    response = upload_preview(client, content)

    assert response.status_code == 200
    assert response.json()["can_import"] is False
    assert response.json()["invalid_rows"] == 1
    assert response.json()["errors"][0]["row"] == 1
    assert "timestamp" in response.json()["errors"][0]["message"]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"stage_code": "UNKNOWN"}, "stage_code"),
        ({"timestamp": "not-a-date"}, "timestamp"),
        ({"event_type": "UNKNOWN"}, "event_type"),
        ({"metadata": "{invalid"}, "metadata"),
    ],
)
def test_preview_reports_invalid_row_fields(
    client: TestClient,
    db_session: Session,
    overrides: dict[str, str],
    field: str,
) -> None:
    seed_process_stages(db_session)
    row = event_row()
    row.update(overrides)

    response = upload_preview(client, build_csv([row]))

    assert response.status_code == 200
    assert response.json()["can_import"] is False
    assert response.json()["invalid_rows"] == 1
    assert any(error["field"] == field for error in response.json()["errors"])


def test_preview_rejects_inactive_stage(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    lead = db_session.scalar(select(ProcessStage).where(ProcessStage.code == "LEAD"))
    assert lead is not None
    lead.active = False
    db_session.commit()

    response = upload_preview(client, build_csv([event_row()]))

    assert response.status_code == 200
    assert response.json()["can_import"] is False
    assert response.json()["errors"][0]["field"] == "stage_code"


def test_preview_reports_fully_empty_row(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = build_csv([event_row()]) + b",,,,,,,\n"

    response = upload_preview(client, content)

    assert response.status_code == 200
    assert response.json()["invalid_rows"] == 1
    assert any("vacía" in error["message"] for error in response.json()["errors"])


def test_preview_reports_duplicate_inside_file(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    row = event_row()

    response = upload_preview(client, build_csv([row, row]))

    assert response.status_code == 200
    assert response.json()["can_import"] is False
    assert response.json()["duplicate_rows"] == 1
    assert response.json()["invalid_rows"] == 1
    assert response.json()["valid_rows"] == 1
