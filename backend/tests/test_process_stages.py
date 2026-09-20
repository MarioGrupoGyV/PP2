from fastapi.testclient import TestClient

from tests.helpers import create_stage


def test_create_get_and_update_process_stage(client: TestClient) -> None:
    stage = create_stage(client)

    get_response = client.get(f"/api/v1/process-stages/{stage['id']}")
    patch_response = client.patch(
        f"/api/v1/process-stages/{stage['id']}",
        json={"sla_hours": 2, "active": False},
    )

    assert get_response.status_code == 200
    assert get_response.json()["code"] == "LEAD"
    assert patch_response.status_code == 200
    assert patch_response.json()["sla_hours"] == 2
    assert patch_response.json()["active"] is False


def test_list_process_stages_is_ordered_by_sequence(client: TestClient) -> None:
    create_stage(client, code="CONTACTED", name="Contactado", sequence=2)
    create_stage(client, code="LEAD", name="Lead", sequence=1)

    response = client.get("/api/v1/process-stages")

    assert response.status_code == 200
    assert [stage["code"] for stage in response.json()] == ["LEAD", "CONTACTED"]


def test_rejects_duplicate_process_stage_code(client: TestClient) -> None:
    create_stage(client)

    response = client.post(
        "/api/v1/process-stages",
        json={
            "code": "lead",
            "name": "Otro lead",
            "sequence": 2,
            "sla_hours": 2,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Process stage code already exists"}


def test_rejects_duplicate_process_stage_sequence(client: TestClient) -> None:
    create_stage(client)

    response = client.post(
        "/api/v1/process-stages",
        json={
            "code": "CONTACTED",
            "name": "Contactado",
            "sequence": 1,
            "sla_hours": 48,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Process stage sequence already exists"}


def test_rejects_non_positive_sla(client: TestClient) -> None:
    response = client.post(
        "/api/v1/process-stages",
        json={
            "code": "LEAD",
            "name": "Lead",
            "sequence": 1,
            "sla_hours": 0,
        },
    )

    assert response.status_code == 422
