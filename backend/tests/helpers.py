from fastapi.testclient import TestClient


def create_stage(
    client: TestClient,
    *,
    code: str = "LEAD",
    name: str = "Lead",
    sequence: int = 1,
    sla_hours: int = 1,
    active: bool = True,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/process-stages",
        json={
            "code": code,
            "name": name,
            "sequence": sequence,
            "sla_hours": sla_hours,
            "active": active,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_case(
    client: TestClient,
    stage_id: str,
    *,
    case_code: str = "CASE-001",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/cases",
        json={
            "case_code": case_code,
            "current_stage_id": stage_id,
            "assigned_resource": "Asesor 01",
            "source": "META_ADS",
            "status": "ACTIVE",
            "started_at": "2026-09-19T09:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
