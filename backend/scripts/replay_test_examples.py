import json

import pandas as pd

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ml.artifacts import load_artifact
from app.ml.constants import FEATURE_NAMES
from app.ml.dataset import build_dataset, split_dataset
from app.ml.evaluation import probabilities
from app.repositories import ml_repository
from app.services.prediction_service import predict_case


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        dataset = build_dataset(
            db,
            snapshot_interval_hours=settings.ml_snapshot_interval_hours,
            inactivity_hours=settings.deviation_inactivity_hours,
        )
        split = split_dataset(dataset.samples)
        model_run = ml_repository.get_active_model_run(db)
        if model_run is None:
            raise SystemExit("No active model")
        artifact = load_artifact(model_run.artifact_path, model_run.artifact_sha256)
        frame = pd.DataFrame(
            [{name: sample.features[name] for name in FEATURE_NAMES} for sample in split.test],
            columns=FEATURE_NAMES,
        )
        scores = probabilities(artifact["pipeline"], frame)
        positives = [index for index, sample in enumerate(split.test) if sample.target == 1]
        negatives = [index for index, sample in enumerate(split.test) if sample.target == 0]
        positive_index = max(positives, key=lambda index: scores[index])
        negative_index = min(negatives, key=lambda index: scores[index])
        output = {}
        for label, index in (("positive", positive_index), ("negative", negative_index)):
            sample = split.test[index]
            prediction = predict_case(db, sample.case_id, sample.snapshot_timestamp)
            output[label] = {
                "case_code": sample.case_code,
                "snapshot_timestamp": sample.snapshot_timestamp.isoformat(),
                "current_stage": sample.features["current_stage_code"],
                "historical_target": sample.target,
                "historical_target_types": sample.target_types,
                "next_stage_change_timestamp": sample.next_stage_change_timestamp.isoformat(),
                "risk_score": prediction.risk_score,
                "risk_level": prediction.risk_level,
                "predicted_label": prediction.predicted_label,
            }
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
