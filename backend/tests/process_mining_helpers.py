from fastapi.testclient import TestClient

from tests.helpers import create_case, create_stage


def create_process_mining_data(client: TestClient) -> None:
    lead = create_stage(client, code="LEAD", name="Lead", sequence=1)
    contacted = create_stage(
        client,
        code="CONTACTED",
        name="Contactado",
        sequence=2,
    )
    qualified = create_stage(
        client,
        code="QUALIFIED",
        name="Calificado",
        sequence=3,
    )

    cases = [
        create_case(client, str(lead["id"]), case_code="CASE-A"),
        create_case(client, str(lead["id"]), case_code="CASE-B"),
        create_case(client, str(lead["id"]), case_code="CASE-C"),
    ]
    paths = {
        "CASE-A": [
            (lead, "Lead", "2026-09-01T09:00:00Z"),
            (contacted, "Contactado", "2026-09-01T10:00:00Z"),
            (qualified, "Calificado", "2026-09-01T12:00:00Z"),
        ],
        "CASE-B": [
            (lead, "Lead", "2026-09-02T09:00:00Z"),
            (contacted, "Contactado", "2026-09-02T11:00:00Z"),
            (qualified, "Calificado", "2026-09-02T15:00:00Z"),
        ],
        "CASE-C": [
            (lead, "Lead", "2026-09-03T09:00:00Z"),
            (qualified, "Calificado", "2026-09-03T14:00:00Z"),
        ],
    }

    for commercial_case in cases:
        case_code = str(commercial_case["case_code"])
        for stage, activity, timestamp in reversed(paths[case_code]):
            response = client.post(
                f"/api/v1/cases/{commercial_case['id']}/events",
                json={
                    "stage_id": stage["id"],
                    "activity": activity,
                    "event_type": "STAGE_CHANGE",
                    "resource": "Asesor QA",
                    "timestamp": timestamp,
                    "metadata": {},
                },
            )
            assert response.status_code == 201, response.text

    interaction = client.post(
        f"/api/v1/cases/{cases[0]['id']}/events",
        json={
            "stage_id": contacted["id"],
            "activity": "Llamada de seguimiento",
            "event_type": "INTERACTION",
            "resource": "Asesor QA",
            "timestamp": "2026-09-01T10:30:00Z",
            "metadata": {},
        },
    )
    assert interaction.status_code == 201, interaction.text
