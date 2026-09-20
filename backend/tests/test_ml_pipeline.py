from pathlib import Path

import pandas as pd
import pytest

from app.ml.artifacts import file_sha256, load_artifact, save_artifact
from app.ml.constants import FEATURE_NAMES, NUMERIC_FEATURES
from app.ml.evaluation import probabilities, select_f1_threshold
from app.ml.preprocessing import (
    build_dummy_pipeline,
    build_logistic_pipeline,
    build_random_forest_pipeline,
)
from app.services.prediction_service import risk_level_for_score
from app.models.enums import RiskLevel


def feature_row(index: int, stage="LEAD"):
    row = {name: float(index) for name in NUMERIC_FEATURES}
    row.update(
        {
            "current_stage_code": stage,
            "previous_stage_code": None if index == 0 else "CONTACTED",
            "source": "WEB",
            "current_resource": "Asesor",
            "assigned_resource": "Asesor",
        }
    )
    return {name: row[name] for name in FEATURE_NAMES}


@pytest.mark.parametrize(
    "factory",
    [build_dummy_pipeline, build_logistic_pipeline, build_random_forest_pipeline],
)
def test_all_models_train_and_return_probabilities(factory) -> None:
    frame = pd.DataFrame([feature_row(index) for index in range(8)], columns=FEATURE_NAMES)
    target = [0, 1, 0, 1, 0, 1, 0, 1]
    model = factory().fit(frame, target)
    scores = probabilities(model, frame)
    assert len(scores) == len(frame)
    assert all(0 <= score <= 1 for score in scores)


def test_unknown_categories_missing_values_and_column_order_are_supported() -> None:
    training = pd.DataFrame([feature_row(index) for index in range(6)], columns=FEATURE_NAMES)
    model = build_logistic_pipeline().fit(training, [0, 1, 0, 1, 0, 1])
    unknown = feature_row(2, stage="UNSEEN_STAGE")
    unknown["source"] = None
    score = probabilities(model, pd.DataFrame([unknown], columns=FEATURE_NAMES))[0]
    assert 0 <= score <= 1


def test_threshold_and_risk_levels_are_independent() -> None:
    threshold = select_f1_threshold([0, 0, 1, 1], pd.Series([0.1, 0.2, 0.6, 0.9]).to_numpy())
    assert 0.05 <= threshold <= 0.95
    assert risk_level_for_score(0.39) == RiskLevel.LOW
    assert risk_level_for_score(0.40) == RiskLevel.MEDIUM
    assert risk_level_for_score(0.70) == RiskLevel.HIGH


def test_artifact_round_trip_and_sha256(tmp_path: Path) -> None:
    frame = pd.DataFrame([feature_row(index) for index in range(6)], columns=FEATURE_NAMES)
    model = build_logistic_pipeline().fit(frame, [0, 1, 0, 1, 0, 1])
    before = probabilities(model, frame)
    path, digest = save_artifact(tmp_path, "test-v1", model, {"feature_schema_version": "v1"})
    loaded = load_artifact(path, digest)
    after = probabilities(loaded["pipeline"], frame)
    assert before.tolist() == pytest.approx(after.tolist())
    assert digest == file_sha256(path)
    with pytest.raises(ValueError):
        load_artifact(path, "0" * 64)
