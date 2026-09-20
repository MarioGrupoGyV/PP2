from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sqlalchemy_event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import PersistenceError
from app.models.commercial_case import CommercialCase
from app.models.event import Event
from app.models.event_log_import import EventLogImport
from app.services import csv_import_service
from scripts.seed_process_stages import seed_process_stages
from tests.csv_helpers import build_csv, event_row
from tests.helpers import create_case


def upload_commit(client: TestClient, content: bytes, filename: str = "events.csv"):
    return client.post(
        "/api/v1/imports/commit",
        files={"file": (filename, content, "text/csv")},
    )


def unordered_case_rows(case_code: str = "IMPORT-001") -> list[dict[str, str]]:
    return [
        event_row(
            case_code=case_code,
            stage_code="QUALIFIED",
            activity="Lead calificado",
            timestamp="2026-09-02T10:00:00-05:00",
        ),
        event_row(case_code=case_code),
        event_row(
            case_code=case_code,
            stage_code="CONTACTED",
            activity="Lead contactado",
            timestamp="2026-09-01T09:15:00-05:00",
        ),
    ]


def test_commit_creates_case_events_and_chronological_current_stage(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)

    response = upload_commit(client, build_csv(unordered_case_rows()))

    assert response.status_code == 201
    result = response.json()
    assert result["cases_created"] == 1
    assert result["events_imported"] == 3
    commercial_case = client.get("/api/v1/cases/code/IMPORT-001").json()
    timeline = client.get(
        f"/api/v1/cases/{commercial_case['id']}/events"
    ).json()
    assert [event["activity"] for event in timeline] == [
        "Lead creado",
        "Lead contactado",
        "Lead calificado",
    ]
    imported_events = list(
        db_session.scalars(select(Event).order_by(Event.timestamp)).all()
    )
    assert all(event.import_id is not None for event in imported_events)
    assert all(event.source_row_number is not None for event in imported_events)
    assert all(event.event_fingerprint is not None for event in imported_events)
    stages = client.get("/api/v1/process-stages").json()
    qualified_id = next(stage["id"] for stage in stages if stage["code"] == "QUALIFIED")
    assert commercial_case["current_stage_id"] == qualified_id


def test_commit_reuses_existing_case(client: TestClient, db_session: Session) -> None:
    seed_process_stages(db_session)
    stages = client.get("/api/v1/process-stages").json()
    lead_id = next(stage["id"] for stage in stages if stage["code"] == "LEAD")
    create_case(client, lead_id, case_code="EXISTING-001")
    content = build_csv(
        [
            event_row(
                case_code="EXISTING-001",
                stage_code="CONTACTED",
                activity="Lead contactado",
            )
        ]
    )

    response = upload_commit(client, content)

    assert response.status_code == 201
    assert response.json()["cases_created"] == 0
    assert response.json()["cases_existing"] == 1
    assert db_session.scalar(select(func.count()).select_from(CommercialCase)) == 1


def test_invalid_commit_has_no_partial_persistence(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = build_csv(
        [event_row(), event_row(case_code="BROKEN", stage_code="UNKNOWN")]
    )

    response = upload_commit(client, content)

    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(EventLogImport)) == 0
    assert db_session.scalar(select(func.count()).select_from(CommercialCase)) == 0
    assert db_session.scalar(select(func.count()).select_from(Event)) == 0


def test_commit_rejects_exact_same_file_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = build_csv([event_row()])

    first = upload_commit(client, content)
    second = upload_commit(client, content)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "Este archivo ya fue importado anteriormente."}


def test_commit_skips_existing_event_fingerprint(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    row = event_row()
    first_content = build_csv([row])
    second_row = {**row, "note": "same normalized event"}
    second_content = build_csv(
        [second_row],
        fieldnames=[*row.keys(), "note"],
    )

    first = upload_commit(client, first_content, "first.csv")
    second = upload_commit(client, second_content, "second.csv")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["events_imported"] == 0
    assert second.json()["duplicates_skipped"] == 1
    assert db_session.scalar(select(func.count()).select_from(Event)) == 1


def test_import_history_and_detail(client: TestClient, db_session: Session) -> None:
    seed_process_stages(db_session)
    result = upload_commit(client, build_csv([event_row()])).json()

    history = client.get("/api/v1/imports")
    detail = client.get(f"/api/v1/imports/{result['import_id']}")

    assert history.status_code == 200
    assert history.json()[0]["id"] == result["import_id"]
    assert detail.status_code == 200
    assert detail.json()["filename"] == "events.csv"
    assert detail.json()["imported_events"] == 1


def test_unexpected_persistence_failure_rolls_back_everything(
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = build_csv(unordered_case_rows("ROLLBACK-001"))
    flush_calls = 0

    @sqlalchemy_event.listens_for(db_session, "before_flush")
    def fail_during_event_flush(*_: object) -> None:
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 3:
            raise SQLAlchemyError("forced import failure")

    with pytest.raises(PersistenceError):
        csv_import_service.commit_csv(
            db_session,
            filename="rollback.csv",
            content=content,
        )

    sqlalchemy_event.remove(db_session, "before_flush", fail_during_event_flush)
    assert db_session.scalar(select(func.count()).select_from(EventLogImport)) == 0
    assert db_session.scalar(select(func.count()).select_from(CommercialCase)) == 0
    assert db_session.scalar(select(func.count()).select_from(Event)) == 0
