from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.tool_executor import ToolExecutor
from app.agents.tool_registry import get_tool_registry
from app.core.config import Settings
from app.models.deviation import Deviation
from app.models.event import Event
from tests.process_mining_helpers import create_process_mining_data


def test_registry_contains_only_required_read_tools_and_strict_schemas() -> None:
    registry = get_tool_registry()
    assert set(registry.names) == {
        "get_case",
        "get_case_timeline",
        "get_case_conformance",
        "get_case_deviations",
        "get_case_prediction",
        "get_case_alerts",
        "get_process_summary",
        "get_process_variants",
        "get_process_transitions",
        "get_deviation_summary",
        "get_alert_summary",
    }
    forbidden_write_tools = {
        "run_sql",
        "run_shell",
        "create_prediction",
        "resolve_alert",
        "attend_alert",
        "dismiss_alert",
        "train_model",
    }
    assert set(registry.names).isdisjoint(forbidden_write_tools)
    for schema in registry.schemas():
        function = schema["function"]
        assert function["strict"] is True
        assert function["parameters"]["additionalProperties"] is False


def test_all_tools_read_real_services_without_mutating_protected_data(
    client,
    db_session: Session,
) -> None:
    create_process_mining_data(client)
    analysis = client.post("/api/v1/deviations/analyze")
    assert analysis.status_code == 200
    settings = Settings(analyst_max_tool_result_items=10)
    executor = ToolExecutor(registry=get_tool_registry(), settings=settings)
    before = (
        db_session.scalar(select(func.count()).select_from(Event)),
        db_session.scalar(select(func.count()).select_from(Deviation)),
    )
    calls = [
        ("get_case", {"case_code": "CASE-C"}),
        ("get_case_timeline", {"case_code": "CASE-C", "limit": 10}),
        ("get_case_conformance", {"case_code": "CASE-C"}),
        ("get_case_deviations", {"case_code": "CASE-C", "limit": 10}),
        ("get_case_prediction", {"case_code": "CASE-C"}),
        ("get_case_alerts", {"case_code": "CASE-C"}),
        ("get_process_summary", {}),
        ("get_process_variants", {"limit": 5}),
        ("get_process_transitions", {"limit": 5, "sort_by": "average_duration"}),
        ("get_deviation_summary", {}),
        ("get_alert_summary", {}),
    ]
    results = {
        name: executor.execute(db_session, name=name, arguments=arguments)
        for name, arguments in calls
    }

    assert results["get_case"].output["case_code"] == "CASE-C"
    assert results["get_case_timeline"].output["timeline"][0]["stage_code"] == "LEAD"
    assert results["get_case_conformance"].output["structurally_conforming"] is False
    assert results["get_case_deviations"].output["total"] >= 1
    assert results["get_case_prediction"].status == "not_found"
    assert results["get_case_alerts"].output["alerts"] == []
    assert results["get_process_summary"].output["total_events"] == 8
    assert results["get_process_variants"].output["variants"][0]["case_count"] == 2
    assert results["get_process_transitions"].output["sort_by"] == "average_duration"
    assert results["get_process_transitions"].output["transitions"][0]["average_duration_display"]
    assert results["get_deviation_summary"].output["total_deviations"] >= 1
    assert results["get_deviation_summary"].output["affected_cases_by_type"]["REWORK"] >= 0
    assert set(results["get_deviation_summary"].output["affected_cases_by_type"]) == {
        "SLA_BREACH", "STAGE_SKIP", "BACKTRACK", "REWORK", "INACTIVITY"
    }
    assert results["get_alert_summary"].output["total_alerts"] == 0
    assert all(result.evidence for result in results.values())

    after = (
        db_session.scalar(select(func.count()).select_from(Event)),
        db_session.scalar(select(func.count()).select_from(Deviation)),
    )
    assert after == before


def test_executor_rejects_unknown_tool_and_malformed_arguments(db_session: Session) -> None:
    executor = ToolExecutor(
        registry=get_tool_registry(),
        settings=Settings(),
    )
    unknown = executor.execute(db_session, name="execute_sql", arguments={})
    malformed = executor.execute(
        db_session,
        name="get_process_variants",
        arguments='{"limit":"five"}',
    )
    extra = executor.execute(
        db_session,
        name="get_process_summary",
        arguments={"unexpected": True},
    )
    blank_case = executor.execute(
        db_session,
        name="get_case",
        arguments={"case_code": "   "},
    )
    assert unknown.status == "error"
    assert malformed.status == "invalid_arguments"
    assert extra.status == "invalid_arguments"
    assert blank_case.status == "invalid_arguments"
