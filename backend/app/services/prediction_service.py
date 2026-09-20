import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.exceptions import DomainValidationError, PersistenceError, ResourceNotFoundError
from app.ml.artifacts import load_artifact
from app.ml.constants import (
    CATEGORICAL_FEATURES,
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    RISK_THRESHOLDS,
)
from app.ml.domain import MlCase, MlDeviation, MlEvent
from app.ml.features import build_features
from app.models.commercial_case import CommercialCase
from app.models.deviation import Deviation
from app.models.enums import RiskLevel
from app.models.event import Event
from app.models.ml_model_run import MlModelRun
from app.models.prediction import Prediction
from app.models.process_stage import ProcessStage
from app.repositories import ml_repository
from app.schemas.prediction import (
    ActiveModelRead,
    ModelEvaluationRead,
    PredictionList,
    PredictionRead,
    RiskFactor,
)

_artifact_cache: dict[str, Any] = {}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def risk_level_for_score(score: float) -> RiskLevel:
    if score >= RISK_THRESHOLDS["high"]:
        return RiskLevel.HIGH
    if score >= RISK_THRESHOLDS["medium"]:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _active_model(db: Session) -> MlModelRun:
    model_run = ml_repository.get_active_model_run(db)
    if model_run is None:
        raise ResourceNotFoundError("No existe un modelo predictivo activo")
    return model_run


def _artifact(model_run: MlModelRun) -> dict[str, Any]:
    cache_key = f"{model_run.id}:{model_run.artifact_sha256}"
    if cache_key not in _artifact_cache:
        _artifact_cache.clear()
        _artifact_cache[cache_key] = load_artifact(
            model_run.artifact_path, model_run.artifact_sha256
        )
    return _artifact_cache[cache_key]


def _load_case_context(
    db: Session, case_id: UUID
) -> tuple[MlCase, list[MlEvent], list[MlDeviation], int]:
    case = db.get(CommercialCase, case_id)
    if case is None:
        raise ResourceNotFoundError("Caso comercial no encontrado")
    stored_events = list(
        db.scalars(
            select(Event)
            .options(joinedload(Event.stage))
            .where(Event.case_id == case_id)
            .order_by(Event.timestamp, Event.created_at, Event.id)
        ).all()
    )
    if not stored_events:
        raise DomainValidationError("El caso no tiene eventos para construir un snapshot")
    events = [
        MlEvent(
            item.id, item.case_id, item.stage_id, item.stage.code,
            item.stage.sequence, item.stage.sla_hours, item.event_type,
            item.resource, _utc(item.timestamp), _utc(item.created_at),
        )
        for item in stored_events
    ]
    deviations = [
        MlDeviation(item.id, item.case_id, item.type, _utc(item.detected_at))
        for item in db.scalars(
            select(Deviation)
            .where(Deviation.case_id == case_id)
            .order_by(Deviation.detected_at, Deviation.id)
        ).all()
    ]
    maximum_sequence = db.scalar(
        select(ProcessStage.sequence)
        .where(ProcessStage.active.is_(True))
        .order_by(ProcessStage.sequence.desc())
        .limit(1)
    ) or 1
    ml_case = MlCase(
        case.id, case.case_code, case.source, case.assigned_resource, _utc(case.started_at)
    )
    return ml_case, events, deviations, maximum_sequence


def _original_feature_value(transformed_name: str, features: dict[str, Any]) -> Any:
    name = transformed_name.split("__", 1)[-1]
    if transformed_name.startswith("numeric__"):
        return features.get(name)
    for feature in CATEGORICAL_FEATURES:
        if name == feature or name.startswith(f"{feature}_"):
            return features.get(feature)
    return None


def _explain(pipeline: Any, frame: pd.DataFrame, features: dict[str, Any], algorithm: str) -> list[RiskFactor]:
    preprocessor = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]
    transformed = preprocessor.transform(frame)
    values = transformed.toarray()[0] if hasattr(transformed, "toarray") else np.asarray(transformed)[0]
    names = list(preprocessor.get_feature_names_out())
    if algorithm == "logistic_regression":
        contributions = values * classifier.coef_[0]
        indices = np.argsort(np.abs(contributions))[::-1][:5]
        return [
            RiskFactor(
                feature=names[index],
                value=_original_feature_value(names[index], features),
                influence=round(float(contributions[index]), 6),
                direction="INCREASES_RISK" if contributions[index] >= 0 else "DECREASES_RISK",
                scope="LOCAL_ASSOCIATION",
            )
            for index in indices
        ]
    importances = classifier.feature_importances_
    indices = np.argsort(importances)[::-1][:5]
    return [
        RiskFactor(
            feature=names[index],
            value=_original_feature_value(names[index], features),
            importance=round(float(importances[index]), 6),
            scope="GLOBAL_IMPORTANCE",
        )
        for index in indices
    ]


def _fingerprint(
    case_id: UUID,
    model_version: str,
    snapshot_timestamp: datetime,
    features: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "case_id": str(case_id),
            "model_version": model_version,
            "snapshot_timestamp": snapshot_timestamp.isoformat(),
            "features": features,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read(prediction: Prediction, *, reused: bool = False) -> PredictionRead:
    return PredictionRead(
        id=prediction.id,
        case_id=prediction.case_id,
        case_code=prediction.commercial_case.case_code,
        snapshot_timestamp=prediction.snapshot_timestamp,
        model_version=prediction.model_run.model_version,
        algorithm=prediction.model_run.algorithm,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        predicted_label=prediction.predicted_label,
        decision_threshold=prediction.model_run.decision_threshold,
        prediction_applicable=True,
        top_factors=[RiskFactor.model_validate(item) for item in prediction.explanation],
        predicted_at=prediction.predicted_at,
        prediction_reused=reused,
    )


def predict_case(db: Session, case_id: UUID, as_of: datetime | None) -> PredictionRead:
    model_run = _active_model(db)
    artifact = _artifact(model_run)
    if artifact["metadata"].get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
        raise DomainValidationError("El esquema de features del modelo no es compatible")
    commercial_case, events, deviations, maximum_sequence = _load_case_context(db, case_id)
    snapshot_timestamp = _utc(as_of) if as_of else events[-1].timestamp
    if snapshot_timestamp < events[0].timestamp:
        raise DomainValidationError("as_of es anterior al primer evento del caso")
    try:
        features, _, _ = build_features(
            commercial_case, events, deviations, snapshot_timestamp, maximum_sequence
        )
    except ValueError as exc:
        raise DomainValidationError(str(exc)) from exc
    if (
        features["current_stage_elapsed_hours"] > features["current_stage_sla_hours"]
        or features["gap_from_previous_event_hours"]
        > get_settings().deviation_inactivity_hours
    ):
        return PredictionRead(
            id=None,
            case_id=case_id,
            case_code=commercial_case.case_code,
            snapshot_timestamp=snapshot_timestamp,
            model_version=model_run.model_version,
            algorithm=model_run.algorithm,
            risk_score=None,
            risk_level=None,
            predicted_label=None,
            decision_threshold=model_run.decision_threshold,
            prediction_applicable=False,
            reason="DETERMINISTIC_THRESHOLD_ALREADY_EXCEEDED",
        )
    fingerprint = _fingerprint(
        case_id, model_run.model_version, snapshot_timestamp, features
    )
    existing = ml_repository.get_prediction_by_fingerprint(db, fingerprint)
    if existing is not None:
        return _read(existing, reused=True)
    frame = pd.DataFrame([features], columns=FEATURE_NAMES)
    pipeline = artifact["pipeline"]
    score = float(pipeline.predict_proba(frame)[0, list(pipeline.classes_).index(1)])
    level = risk_level_for_score(score)
    factors = _explain(pipeline, frame, features, model_run.algorithm)
    observed_events = [event for event in events if event.timestamp <= snapshot_timestamp]
    snapshot_event_id = (
        observed_events[-1].id
        if observed_events and observed_events[-1].timestamp == snapshot_timestamp
        else None
    )
    prediction = Prediction(
        case_id=case_id,
        model_run_id=model_run.id,
        snapshot_event_id=snapshot_event_id,
        snapshot_timestamp=snapshot_timestamp,
        prediction_fingerprint=fingerprint,
        risk_score=score,
        predicted_label=score >= model_run.decision_threshold,
        risk_level=level,
        features=features,
        explanation=[item.model_dump(mode="json") for item in factors],
    )
    try:
        ml_repository.add_prediction(db, prediction)
        db.commit()
        db.refresh(prediction)
    except Exception as exc:
        db.rollback()
        existing = ml_repository.get_prediction_by_fingerprint(db, fingerprint)
        if existing is not None:
            return _read(existing, reused=True)
        raise PersistenceError("No fue posible persistir la predicción") from exc
    prediction.commercial_case = db.get(CommercialCase, case_id)
    prediction.model_run = model_run
    return _read(prediction)


def latest_prediction(db: Session, case_id: UUID) -> PredictionRead:
    if db.get(CommercialCase, case_id) is None:
        raise ResourceNotFoundError("Caso comercial no encontrado")
    prediction = ml_repository.latest_prediction_for_case(db, case_id)
    if prediction is None:
        raise ResourceNotFoundError("El caso no tiene predicciones")
    return _read(prediction)


def list_predictions(
    db: Session, *, risk_level: RiskLevel | None, case_code: str | None,
    predicted_label: bool | None, page: int, page_size: int,
) -> PredictionList:
    items, total = ml_repository.list_predictions(
        db, risk_level=risk_level, case_code=case_code,
        predicted_label=predicted_label, offset=(page - 1) * page_size, limit=page_size,
    )
    return PredictionList(
        items=[_read(item) for item in items], page=page, page_size=page_size, total=total
    )


def get_active_model(db: Session) -> ActiveModelRead:
    model_run = _active_model(db)
    return ActiveModelRead(
        model_version=model_run.model_version,
        algorithm=model_run.algorithm,
        target_name=model_run.target_name,
        feature_schema_version=model_run.feature_schema_version,
        dataset_hash=model_run.dataset_hash,
        trained_at=model_run.trained_at,
        decision_threshold=model_run.decision_threshold,
        test_metrics=model_run.metrics["test"],
        predictive_quality_warning=bool(
            model_run.training_summary.get("predictive_quality_warning", False)
        ),
    )


def get_evaluation(db: Session) -> ModelEvaluationRead:
    model_run = _active_model(db)
    test_metrics = model_run.metrics["test"]
    audit = model_run.training_summary["dataset_audit"]
    return ModelEvaluationRead(
        model_version=model_run.model_version,
        selected_model=model_run.algorithm,
        validation_metrics=model_run.metrics["validation"],
        test_metrics=test_metrics,
        confusion_matrix=test_metrics["confusion_matrix"],
        class_distribution={
            "positive": audit["positive_snapshots"],
            "negative": audit["negative_snapshots"],
            "positive_percentage": audit["positive_percentage"],
        },
        split_summary=model_run.training_summary["split"],
        selection_reason=model_run.training_summary["selection_reason"],
    )
