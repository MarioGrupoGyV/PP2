from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from scripts.seed_process_stages import seed_process_stages
from tests.csv_helpers import build_csv, event_row


def test_normalized_event_log_is_ordered_and_has_expected_columns(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    content = build_csv(
        [
            event_row(
                case_code="B-CASE",
                stage_code="CONTACTED",
                activity="B Contactado",
                timestamp="2026-09-02T10:00:00Z",
            ),
            event_row(
                case_code="A-CASE",
                stage_code="CONTACTED",
                activity="A Contactado",
                timestamp="2026-09-02T10:00:00Z",
            ),
            event_row(
                case_code="A-CASE",
                activity="A Lead",
                timestamp="2026-09-01T10:00:00Z",
            ),
        ]
    )
    commit = client.post(
        "/api/v1/imports/commit",
        files={"file": ("ordered.csv", content, "text/csv")},
    )

    response = client.get("/api/v1/event-log")

    assert commit.status_code == 201
    assert response.status_code == 200
    assert [(row["case_code"], row["activity"]) for row in response.json()] == [
        ("A-CASE", "A Lead"),
        ("A-CASE", "A Contactado"),
        ("B-CASE", "B Contactado"),
    ]
    assert set(response.json()[0]) == {
        "case_code",
        "stage_code",
        "activity",
        "timestamp",
        "resource",
        "event_type",
    }


def test_csv_template_is_downloadable(client: TestClient) -> None:
    response = client.get("/api/v1/imports/template")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.content.startswith(b"case_code,stage_code,activity,timestamp")
