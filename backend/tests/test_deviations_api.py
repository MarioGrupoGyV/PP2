from sqlalchemy.orm import Session

from tests.helpers import create_case, create_stage


def test_analyze_is_idempotent_and_endpoints_report_conformance(client, db_session: Session) -> None:
    lead = create_stage(client, code="LEAD", name="Lead", sequence=1, sla_hours=1)
    contacted = create_stage(client, code="CONTACTED", name="Contactado", sequence=2, sla_hours=48)
    visit = create_stage(client, code="VISIT", name="Visita", sequence=3, sla_hours=48)
    commercial_case = create_case(client, str(lead["id"]), case_code="CASE-DEVIATION")
    for stage, timestamp in [(lead, "2026-09-01T08:00:00Z"), (visit, "2026-09-05T08:00:00Z")]:
        response = client.post(
            f"/api/v1/cases/{commercial_case['id']}/events",
            json={"stage_id": stage["id"], "activity": stage["name"], "event_type": "STAGE_CHANGE", "timestamp": timestamp, "metadata": {}},
        )
        assert response.status_code == 201

    first = client.post("/api/v1/deviations/analyze")
    second = client.post("/api/v1/deviations/analyze")
    assert first.status_code == second.status_code == 200
    assert first.json()["deviations_created"] == 3
    assert second.json()["deviations_created"] == 0
    assert second.json()["deviations_existing"] == 3

    listing = client.get("/api/v1/deviations?type=STAGE_SKIP").json()
    assert listing["total"] == 1
    detail = client.get(f"/api/v1/deviations/{listing['items'][0]['id']}")
    assert detail.status_code == 200
    case_conformance = client.get(f"/api/v1/cases/{commercial_case['id']}/conformance").json()
    assert case_conformance["observed_sequence"] == ["LEAD", "VISIT"]
    assert case_conformance["structurally_conforming"] is False

    expected = client.get("/api/v1/process-mining/expected-model").json()
    assert [stage["code"] for stage in expected["stages"]] == ["LEAD", "CONTACTED", "VISIT"]
    conformance = client.get("/api/v1/process-mining/conformance").json()
    assert conformance["structurally_nonconforming_cases"] == 1
    summary = client.get("/api/v1/deviations/summary").json()
    assert summary["total_deviations"] == 3
