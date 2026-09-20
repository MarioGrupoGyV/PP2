from tests.process_mining_helpers import create_process_mining_data


def test_process_mining_endpoints(client) -> None:
    create_process_mining_data(client)

    dfg = client.get("/api/v1/process-mining/dfg")
    performance = client.get("/api/v1/process-mining/performance")
    variants = client.get("/api/v1/process-mining/variants?limit=1")
    summary = client.get("/api/v1/process-mining/summary")
    activities = client.get("/api/v1/process-mining/activities")
    transitions = client.get("/api/v1/process-mining/transitions")

    assert dfg.status_code == 200
    assert len(dfg.json()["nodes"]) == 3
    assert len(dfg.json()["edges"]) == 3
    assert performance.status_code == 200
    assert len(performance.json()["transitions"]) == 3
    assert variants.status_code == 200
    assert len(variants.json()) == 1
    assert summary.status_code == 200
    assert summary.json()["total_events"] == 8
    assert activities.status_code == 200
    assert activities.json()[0]["frequency"] == 3
    assert transitions.status_code == 200
    assert transitions.json()[0]["frequency"] == 2

    variant_id = variants.json()[0]["variant_id"]
    cases = client.get(
        f"/api/v1/process-mining/variants/{variant_id}/cases?page=1&page_size=1"
    )
    assert cases.status_code == 200
    assert cases.json()["case_count"] == 2
    assert len(cases.json()["cases"]) == 1
    assert cases.json()["total_pages"] == 2


def test_process_mining_empty_state_and_unknown_variant(client) -> None:
    summary = client.get("/api/v1/process-mining/summary")
    dfg = client.get("/api/v1/process-mining/dfg")
    missing = client.get(
        "/api/v1/process-mining/variants/does-not-exist/cases"
    )

    assert summary.status_code == 200
    assert summary.json()["total_events"] == 0
    assert dfg.status_code == 200
    assert dfg.json()["nodes"] == []
    assert missing.status_code == 404
    assert missing.json() == {"detail": "Variante no encontrada"}
