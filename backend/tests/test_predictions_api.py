from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.artifacts import save_artifact
from app.ml.constants import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, NUMERIC_FEATURES
from app.ml.preprocessing import build_logistic_pipeline
from app.models.ml_model_run import MlModelRun
from tests.helpers import create_case, create_stage


def feature_row(index: int):
    row = {name: float(index) for name in NUMERIC_FEATURES}
    row.update(
        {
            "current_stage_code": "LEAD" if index % 2 else "CONTACTED",
            "previous_stage_code": "LEAD",
            "source": "WEB",
            "current_resource": "Asesor",
            "assigned_resource": "Asesor",
        }
    )
    return {name: row[name] for name in FEATURE_NAMES}


def install_active_model(db: Session, tmp_path: Path) -> MlModelRun:
    frame = pd.DataFrame([feature_row(index) for index in range(8)], columns=FEATURE_NAMES)
    pipeline = build_logistic_pipeline().fit(frame, [0, 1, 0, 1, 0, 1, 0, 1])
    path, digest = save_artifact(
        tmp_path,
        "next-deviation-test-v1",
        pipeline,
        {"feature_schema_version": FEATURE_SCHEMA_VERSION},
    )
    sample_metrics = {
        "accuracy": 0.5, "precision": 0.5, "recall": 0.5, "f1": 0.5,
        "roc_auc": 0.5, "pr_auc": 0.5, "brier_score": 0.25,
        "confusion_matrix": [[1, 1], [1, 1]], "threshold": 0.5,
    }
    model_run = MlModelRun(
        model_version="next-deviation-test-v1",
        algorithm="logistic_regression",
        target_name="NEXT_DEVIATION",
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        dataset_hash="a" * 64,
        decision_threshold=0.5,
        metrics={
            "validation": {
                "dummy": sample_metrics,
                "logistic_regression": sample_metrics,
                "random_forest": sample_metrics,
            },
            "selected_model": "logistic_regression",
            "test": sample_metrics,
        },
        hyperparameters={"class_weight": "balanced"},
        training_summary={
            "dataset_audit": {
                "positive_snapshots": 40,
                "negative_snapshots": 60,
                "positive_percentage": 40.0,
            },
            "split": {"train_cases": 7, "validation_cases": 2, "test_cases": 1},
            "selection_reason": "test fixture",
            "predictive_quality_warning": False,
        },
        artifact_path=str(path),
        artifact_sha256=digest,
        is_active=True,
        trained_at=datetime.now(UTC),
    )
    db.add(model_run)
    db.commit()
    db.refresh(model_run)
    return model_run


def test_prediction_api_requires_active_model(client) -> None:
    stage = create_stage(client)
    commercial_case = create_case(client, str(stage["id"]))
    response = client.post(f"/api/v1/cases/{commercial_case['id']}/predict")
    assert response.status_code == 404
    assert "modelo predictivo activo" in response.json()["detail"]


def test_prediction_replay_idempotency_listing_and_model_endpoints(
    client, db_session: Session, tmp_path: Path
) -> None:
    stage = create_stage(client, sla_hours=1)
    commercial_case = create_case(client, str(stage["id"]), case_code="CASE-PREDICT")
    event_timestamp = datetime(2026, 9, 20, 10, tzinfo=UTC)
    event_response = client.post(
        f"/api/v1/cases/{commercial_case['id']}/events",
        json={
            "stage_id": stage["id"], "activity": "Lead",
            "event_type": "STAGE_CHANGE", "resource": "Asesor",
            "timestamp": event_timestamp.isoformat(), "metadata": {},
        },
    )
    assert event_response.status_code == 201
    install_active_model(db_session, tmp_path)

    first = client.post(f"/api/v1/cases/{commercial_case['id']}/predict")
    second = client.post(f"/api/v1/cases/{commercial_case['id']}/predict")
    assert first.status_code == second.status_code == 200
    assert first.json()["prediction_applicable"] is True
    assert 0 <= first.json()["risk_score"] <= 1
    assert first.json()["id"] == second.json()["id"]
    assert len(first.json()["top_factors"]) > 0

    replay_time = event_timestamp + timedelta(minutes=30)
    replay = client.post(
        f"/api/v1/cases/{commercial_case['id']}/predict",
        json={"as_of": replay_time.isoformat()},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] != first.json()["id"]

    too_late = client.post(
        f"/api/v1/cases/{commercial_case['id']}/predict",
        json={"as_of": (event_timestamp + timedelta(hours=2)).isoformat()},
    )
    assert too_late.status_code == 200
    assert too_late.json()["prediction_applicable"] is False
    assert too_late.json()["reason"] == "DETERMINISTIC_THRESHOLD_ALREADY_EXCEEDED"
    assert too_late.json()["id"] is None

    assert client.get(f"/api/v1/cases/{commercial_case['id']}/prediction").status_code == 200
    listing = client.get("/api/v1/predictions?risk_level=LOW&page_size=100")
    assert listing.status_code == 200
    assert client.get("/api/v1/predictions?page_size=100").json()["total"] == 2
    assert client.get("/api/v1/ml/model").json()["model_version"] == "next-deviation-test-v1"
    evaluation = client.get("/api/v1/ml/evaluation")
    assert evaluation.status_code == 200
    assert evaluation.json()["confusion_matrix"] == [[1, 1], [1, 1]]
    assert client.post(f"/api/v1/cases/{uuid4()}/predict").status_code == 404
