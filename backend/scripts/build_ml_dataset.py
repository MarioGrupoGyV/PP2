import json
from dataclasses import asdict

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ml.dataset import build_dataset


def main() -> None:
    settings = get_settings()
    with SessionLocal() as db:
        dataset = build_dataset(
            db,
            snapshot_interval_hours=settings.ml_snapshot_interval_hours,
            inactivity_hours=settings.deviation_inactivity_hours,
        )
    print("ML DATASET AUDIT")
    print(json.dumps({**asdict(dataset.audit), "dataset_hash": dataset.dataset_hash}, indent=2))


if __name__ == "__main__":
    main()
