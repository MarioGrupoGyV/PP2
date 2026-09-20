from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.artifacts import save_artifact
from app.ml.constants import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    RISK_THRESHOLDS,
    TARGET_NAME,
)
from app.ml.dataset import build_dataset, split_dataset
from app.ml.domain import DatasetSplit, MlDataset, SnapshotSample
from app.ml.evaluation import (
    choose_model,
    evaluate_model,
    probabilities,
    select_f1_threshold,
)
from app.ml.preprocessing import (
    build_dummy_pipeline,
    build_logistic_pipeline,
    build_random_forest_pipeline,
)
from app.models.ml_model_run import MlModelRun
from app.repositories import ml_repository


@dataclass(slots=True)
class TrainingResult:
    model_run: MlModelRun
    dataset: MlDataset
    split: DatasetSplit
    report: dict[str, Any]


def _frame(samples: list[SnapshotSample]) -> pd.DataFrame:
    return pd.DataFrame(
        [{name: item.features[name] for name in FEATURE_NAMES} for item in samples],
        columns=FEATURE_NAMES,
    )


def _targets(samples: list[SnapshotSample]) -> list[int]:
    return [item.target for item in samples]


def _split_summary(split: DatasetSplit) -> dict[str, Any]:
    return {
        "train_cases": len(split.train_case_ids),
        "validation_cases": len(split.validation_case_ids),
        "test_cases": len(split.test_case_ids),
        "train_snapshots": len(split.train),
        "validation_snapshots": len(split.validation),
        "test_snapshots": len(split.test),
        "train_positive": sum(item.target for item in split.train),
        "validation_positive": sum(item.target for item in split.validation),
        "test_positive": sum(item.target for item in split.test),
    }


def train_and_activate(
    db: Session,
    *,
    model_dir: Path,
    snapshot_interval_hours: int,
    inactivity_hours: int,
) -> TrainingResult:
    dataset = build_dataset(
        db,
        snapshot_interval_hours=snapshot_interval_hours,
        inactivity_hours=inactivity_hours,
    )
    if not dataset.audit.leakage_checks_passed:
        raise ValueError("Leakage audit failed; training stopped")
    if not dataset.audit.dataset_usable:
        raise ValueError("Dataset is not viable for supervised training")
    split = split_dataset(dataset.samples)
    train_features = _frame(split.train)
    validation_features = _frame(split.validation)
    test_features = _frame(split.test)
    train_target = _targets(split.train)
    validation_target = _targets(split.validation)
    test_target = _targets(split.test)

    pipelines = {
        "dummy": build_dummy_pipeline(),
        "logistic_regression": build_logistic_pipeline(),
        "random_forest": build_random_forest_pipeline(),
    }
    validation_metrics: dict[str, dict[str, Any]] = {}
    thresholds: dict[str, float] = {"dummy": 0.5}
    for name, pipeline in pipelines.items():
        pipeline.fit(train_features, train_target)
        scores = probabilities(pipeline, validation_features)
        if name != "dummy":
            thresholds[name] = select_f1_threshold(validation_target, scores)
        validation_metrics[name] = evaluate_model(
            pipeline,
            validation_features,
            validation_target,
            thresholds[name],
        )

    selected_name, selection_reason = choose_model(validation_metrics)
    selected_pipeline = pipelines[selected_name]
    selected_threshold = thresholds[selected_name]
    test_metrics = evaluate_model(
        selected_pipeline, test_features, test_target, selected_threshold
    )
    selected_pr = validation_metrics[selected_name]["pr_auc"] or 0.0
    baseline_pr = validation_metrics["dummy"]["pr_auc"] or 0.0
    predictive_quality_warning = selected_pr <= baseline_pr + 0.02
    trained_at = datetime.now(UTC)
    model_version = (
        f"next-deviation-v1-{trained_at.strftime('%Y%m%dT%H%M%S%fZ')}"
        f"-{dataset.dataset_hash[:8]}"
    )
    split_summary = _split_summary(split)
    metrics = {
        "validation": validation_metrics,
        "selected_model": selected_name,
        "selected_validation_threshold": selected_threshold,
        "test": test_metrics,
    }
    hyperparameters = {
        key: value
        for key, value in selected_pipeline.named_steps["classifier"].get_params(deep=False).items()
        if isinstance(value, (str, int, float, bool, type(None)))
    }
    training_summary = {
        "dataset_audit": asdict(dataset.audit),
        "split": split_summary,
        "selection_reason": selection_reason,
        "predictive_quality_warning": predictive_quality_warning,
        "test_set_used_after_selection": True,
        "checkpoints_are_in_memory_only": True,
    }
    metadata = {
        "model_version": model_version,
        "algorithm": selected_name,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "target_definition": (
            "At snapshot T, at least one persisted deviation is detected in "
            "(T, next STAGE_CHANGE timestamp]"
        ),
        "target_name": TARGET_NAME,
        "dataset_hash": dataset.dataset_hash,
        "trained_at": trained_at.isoformat(),
        "decision_threshold": selected_threshold,
        "risk_thresholds": RISK_THRESHOLDS,
        "metrics": metrics,
        "feature_names": FEATURE_NAMES,
        "hyperparameters": hyperparameters,
        "training_summary": training_summary,
    }
    artifact_path, artifact_sha256 = save_artifact(
        model_dir, model_version, selected_pipeline, metadata
    )
    model_run = MlModelRun(
        model_version=model_version,
        algorithm=selected_name,
        target_name=TARGET_NAME,
        feature_schema_version=FEATURE_SCHEMA_VERSION,
        dataset_hash=dataset.dataset_hash,
        decision_threshold=selected_threshold,
        metrics=metrics,
        hyperparameters=hyperparameters,
        training_summary=training_summary,
        artifact_path=str(artifact_path),
        artifact_sha256=artifact_sha256,
        is_active=True,
        trained_at=trained_at,
    )
    try:
        ml_repository.activate_model_run(db, model_run)
        db.commit()
        db.refresh(model_run)
    except Exception:
        db.rollback()
        raise
    report = {
        "dataset_hash": dataset.dataset_hash,
        "audit": asdict(dataset.audit),
        "split": split_summary,
        "validation": validation_metrics,
        "selected_model": selected_name,
        "selection_reason": selection_reason,
        "decision_threshold": selected_threshold,
        "test": test_metrics,
        "artifact_path": str(artifact_path),
        "artifact_sha256": artifact_sha256,
        "model_version": model_version,
        "predictive_quality_warning": predictive_quality_warning,
    }
    return TrainingResult(model_run=model_run, dataset=dataset, split=split, report=report)
