from uuid import uuid4

from fastapi.testclient import TestClient

from tests.helpers import create_case, create_stage


def test_create_retrieve_and_list_commercial_case(client: TestClient) -> None:
    stage = create_stage(client)
    commercial_case = create_case(client, str(stage["id"]))

    by_id = client.get(f"/api/v1/cases/{commercial_case['id']}")
    by_code = client.get("/api/v1/cases/code/case-001")
    listing = client.get("/api/v1/cases?page=1&page_size=20")

    assert by_id.status_code == 200
    assert by_code.status_code == 200
    assert by_id.json()["case_code"] == "CASE-001"
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == commercial_case["id"]


def test_rejects_duplicate_case_code(client: TestClient) -> None:
    stage = create_stage(client)
    create_case(client, str(stage["id"]))

    response = client.post(
        "/api/v1/cases",
        json={
            "case_code": "case-001",
            "current_stage_id": stage["id"],
            "status": "ACTIVE",
            "started_at": "2026-09-19T09:00:00Z",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Commercial case code already exists"}


def test_rejects_case_with_unknown_stage(client: TestClient) -> None:
    response = client.post(
        "/api/v1/cases",
        json={
            "case_code": "CASE-404",
            "current_stage_id": str(uuid4()),
            "status": "ACTIVE",
            "started_at": "2026-09-19T09:00:00Z",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Process stage not found"}
