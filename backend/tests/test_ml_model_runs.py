from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ml_model_run import MlModelRun
from app.repositories import ml_repository


def model_run(version: str) -> MlModelRun:
    return MlModelRun(
        model_version=version,
        algorithm="logistic_regression",
        target_name="NEXT_DEVIATION",
        feature_schema_version="v1",
        dataset_hash="a" * 64,
        decision_threshold=0.5,
        metrics={},
        hyperparameters={},
        training_summary={},
        artifact_path=f"/models/{version}.joblib",
        artifact_sha256="b" * 64,
        is_active=True,
        trained_at=datetime.now(UTC),
    )


def test_activating_new_model_preserves_history_and_deactivates_previous(
    db_session: Session,
) -> None:
    first = model_run("v1")
    ml_repository.activate_model_run(db_session, first)
    db_session.commit()
    second = model_run("v2")
    ml_repository.activate_model_run(db_session, second)
    db_session.commit()

    assert db_session.scalar(select(func.count()).select_from(MlModelRun)) == 2
    assert db_session.scalar(
        select(func.count()).select_from(MlModelRun).where(MlModelRun.is_active.is_(True))
    ) == 1
    assert ml_repository.get_active_model_run(db_session).model_version == "v2"
