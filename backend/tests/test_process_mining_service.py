from sqlalchemy.orm import Session

from app.services import process_mining_service
from tests.helpers import create_case, create_stage
from tests.process_mining_helpers import create_process_mining_data


def test_event_log_transformation_uses_pm4py_columns_and_stage_changes(
    client,
    db_session: Session,
) -> None:
    create_process_mining_data(client)

    dataframe = process_mining_service.build_event_log_dataframe(db_session)

    assert {
        "case:concept:name",
        "concept:name",
        "time:timestamp",
        "org:resource",
    }.issubset(dataframe.columns)
    assert len(dataframe) == 8
    assert dataframe["case:concept:name"].nunique() == 3
    assert "Llamada de seguimiento" not in set(dataframe["concept:name"])
    assert str(dataframe["time:timestamp"].dtype).endswith("UTC]")
    for _, group in dataframe.groupby("case:concept:name"):
        assert group["time:timestamp"].is_monotonic_increasing


def test_empty_event_log_is_supported(db_session: Session) -> None:
    dataframe = process_mining_service.build_event_log_dataframe(db_session)
    analysis = process_mining_service.analyze_dataframe(dataframe)

    assert dataframe.empty
    assert list(dataframe.columns) == [
        "case:concept:name",
        "concept:name",
        "time:timestamp",
        "org:resource",
        "case:id",
    ]
    assert analysis.frequency_dfg == {}
    assert analysis.variants == {}


def test_dfg_frequencies_start_and_end_activities(client, db_session: Session) -> None:
    create_process_mining_data(client)

    result = process_mining_service.get_dfg(db_session)

    edges = {(edge.source, edge.target): edge.frequency for edge in result.edges}
    assert edges == {
        ("Contactado", "Calificado"): 2,
        ("Lead", "Contactado"): 2,
        ("Lead", "Calificado"): 1,
    }
    assert [(item.activity, item.frequency) for item in result.start_activities] == [
        ("Lead", 3)
    ]
    assert [(item.activity, item.frequency) for item in result.end_activities] == [
        ("Calificado", 3)
    ]


def test_variants_are_counted_and_identifiers_are_deterministic(
    client,
    db_session: Session,
) -> None:
    create_process_mining_data(client)

    first = process_mining_service.get_variants(db_session, limit=20)
    second = process_mining_service.get_variants(db_session, limit=20)

    assert [item.case_count for item in first] == [2, 1]
    assert [item.percentage for item in first] == [66.67, 33.33]
    assert [item.variant_id for item in first] == [
        item.variant_id for item in second
    ]
    assert first[0].activities == ["Lead", "Contactado", "Calificado"]


def test_performance_and_summary_metrics(client, db_session: Session) -> None:
    create_process_mining_data(client)

    transitions = process_mining_service.get_transitions(db_session)
    summary = process_mining_service.get_summary(db_session)

    lead_contacted = next(
        item
        for item in transitions
        if item.source == "Lead" and item.target == "Contactado"
    )
    assert lead_contacted.average_duration_seconds == 5400
    assert lead_contacted.median_duration_seconds == 5400
    assert lead_contacted.min_duration_seconds == 3600
    assert all(item.min_duration_seconds >= 0 for item in transitions)
    assert summary.total_cases == 3
    assert summary.total_events == 8
    assert summary.unique_activities == 3
    assert summary.total_variants == 2
    assert summary.average_case_duration_seconds == 16800
    assert summary.median_case_duration_seconds == 18000


def test_single_event_case_has_zero_duration(client, db_session: Session) -> None:
    stage = create_stage(client)
    commercial_case = create_case(client, str(stage["id"]), case_code="SINGLE-001")
    response = client.post(
        f"/api/v1/cases/{commercial_case['id']}/events",
        json={
            "stage_id": stage["id"],
            "activity": "Lead",
            "event_type": "STAGE_CHANGE",
            "resource": None,
            "timestamp": "2026-09-20T10:00:00Z",
            "metadata": {},
        },
    )
    assert response.status_code == 201

    summary = process_mining_service.get_summary(db_session)

    assert summary.total_cases == 1
    assert summary.total_events == 1
    assert summary.total_variants == 1
    assert summary.average_case_duration_seconds == 0
    assert summary.median_case_duration_seconds == 0
