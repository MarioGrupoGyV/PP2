from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.csv_import_service import preview_csv
from scripts.generate_demo_event_log import SCENARIOS, generate_dataset
from scripts.seed_process_stages import seed_process_stages
from tests.csv_helpers import build_csv


def test_generator_creates_requested_case_count_and_multiple_scenarios() -> None:
    dataset = generate_dataset(cases=100, seed=42)

    assert len(dataset.ground_truth) == 100
    assert len({row["case_code"] for row in dataset.rows}) == 100
    assert len({row["scenario"] for row in dataset.ground_truth}) > 1


def test_generator_is_deterministic_for_same_seed() -> None:
    first = generate_dataset(cases=25, seed=7)
    second = generate_dataset(cases=25, seed=7)

    assert first == second


def test_generator_uses_valid_stages_and_chronological_timestamps() -> None:
    dataset = generate_dataset(cases=50, seed=11)
    timestamps_by_case: dict[str, list[datetime]] = defaultdict(list)

    for row in dataset.rows:
        assert row["stage_code"] in {
            stage for stages in SCENARIOS.values() for stage in stages
        }
        timestamps_by_case[row["case_code"]].append(
            datetime.fromisoformat(row["timestamp"])
        )

    assert all(
        timestamps == sorted(timestamps)
        for timestamps in timestamps_by_case.values()
    )


def test_generator_csv_is_compatible_with_import_preview(
    db_session: Session,
) -> None:
    seed_process_stages(db_session)
    dataset = generate_dataset(cases=20, seed=42)

    preview = preview_csv(
        db_session,
        filename="demo.csv",
        content=build_csv(dataset.rows),
    )

    assert preview.can_import is True
    assert preview.invalid_rows == 0
    assert preview.total_rows == len(dataset.rows)
