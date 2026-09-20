from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.alert import Alert, AlertAction
from app.models.commercial_case import CommercialCase
from app.models.enums import AlertEvaluationMode, AlertStatus, CaseStatus, RiskLevel
from app.models.ml_model_run import MlModelRun
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionRead
from tests.helpers import create_case, create_stage


def setup_case(client, db: Session, *, case_code: str = "CASE-ALERT"):
    stage = create_stage(client, sla_hours=200)
    commercial_case = create_case(client, str(stage["id"]), case_code=case_code)
    timestamp = datetime(2026, 9, 20, 10, tzinfo=UTC)
    response = client.post(
        f"/api/v1/cases/{commercial_case['id']}/events",
        json={
            "stage_id": stage["id"],
            "activity": "Lead",
            "event_type": "STAGE_CHANGE",
            "resource": "Asesor",
            "timestamp": timestamp.isoformat(),
            "metadata": {},
        },
    )
    assert response.status_code == 201
    model = MlModelRun(
        model_version="alert-test-v1",
        algorithm="logistic_regression",
        target_name="NEXT_DEVIATION",
        feature_schema_version="next-deviation-v1",
        dataset_hash="a" * 64,
        decision_threshold=0.685,
        metrics={},
        hyperparameters={},
        training_summary={},
        artifact_path="unused.joblib",
        artifact_sha256="b" * 64,
        is_active=True,
        trained_at=datetime.now(UTC),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return commercial_case, model, timestamp


def make_prediction(
    db: Session,
    commercial_case: dict,
    model: MlModelRun,
    timestamp: datetime,
    *,
    score: float,
    label: bool | None = None,
) -> Prediction:
    prediction = Prediction(
        case_id=UUID(commercial_case["id"]),
        model_run_id=model.id,
        snapshot_timestamp=timestamp,
        prediction_fingerprint=uuid4().hex + uuid4().hex,
        risk_score=score,
        predicted_label=score >= model.decision_threshold if label is None else label,
        risk_level=RiskLevel.HIGH if score >= 0.7 else RiskLevel.MEDIUM if score >= 0.4 else RiskLevel.LOW,
        features={"elapsed": 1},
        explanation=[
            {
                "feature": "numeric__current_stage_elapsed_hours",
                "value": 1,
                "influence": 0.5,
                "importance": None,
                "direction": "INCREASES_RISK",
                "scope": "LOCAL_ASSOCIATION",
            }
        ],
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def prediction_read(prediction: Prediction, *, reused: bool = False) -> PredictionRead:
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
        top_factors=prediction.explanation,
        predicted_at=prediction.predicted_at,
        prediction_reused=reused,
    )


def install_prediction_stub(monkeypatch, values):
    queue = list(values)

    def predict(*_args, **_kwargs):
        if len(queue) > 1:
            return queue.pop(0)
        return queue[0]

    monkeypatch.setattr("app.services.alert_service.prediction_service.predict_case", predict)


@pytest.mark.parametrize("threshold", [0, -0.1, 1.01])
def test_alert_risk_threshold_must_be_greater_than_zero_and_at_most_one(
    threshold: float,
) -> None:
    with pytest.raises(ValidationError):
        Settings(alert_risk_threshold=threshold)


def test_high_prediction_creates_one_idempotent_alert_and_exposes_reads(
    client, db_session: Session, monkeypatch
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    prediction = make_prediction(db_session, commercial_case, model, timestamp, score=0.85)
    install_prediction_stub(monkeypatch, [prediction_read(prediction), prediction_read(prediction, reused=True)])

    path = f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate"
    first = client.post(path)
    second = client.post(path)
    assert first.status_code == second.status_code == 200
    assert first.json()["outcome"] == "CREATED"
    assert second.json()["outcome"] == "NO_CHANGE"
    assert first.json()["alert"]["alert_code"] == "ALR-000001"
    alert_id = first.json()["alert"]["id"]

    assert client.get("/api/v1/alerts").json()["total"] == 1
    detail = client.get(f"/api/v1/alerts/{alert_id}")
    assert detail.status_code == 200
    assert detail.json()["model_version"] == "alert-test-v1"
    assert len(detail.json()["current_factors"]) == 1
    assert len(client.get(f"/api/v1/cases/{commercial_case['id']}/alerts").json()) == 1
    actions = client.get(f"/api/v1/alerts/{alert_id}/actions").json()
    assert [item["action_type"] for item in actions] == ["CREATED"]
    summary = client.get("/api/v1/alerts/summary").json()
    assert summary["active"] == summary["open_alerts"] == 1


@pytest.mark.parametrize(
    ("score", "label"),
    [(0.50, False), (0.69, True), (0.75, False)],
)
def test_low_score_or_negative_label_does_not_create_alert(
    client, db_session: Session, monkeypatch, score: float, label: bool
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    prediction = make_prediction(
        db_session, commercial_case, model, timestamp, score=score, label=label
    )
    install_prediction_stub(monkeypatch, [prediction_read(prediction)])
    response = client.post(f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate")
    assert response.status_code == 200
    assert response.json()["outcome"] == "BELOW_THRESHOLD"
    assert client.get("/api/v1/alerts/summary").json()["total_alerts"] == 0


def test_not_applicable_prediction_is_skipped(client, db_session: Session, monkeypatch) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    not_applicable = PredictionRead(
        id=None,
        case_id=commercial_case["id"],
        case_code=commercial_case["case_code"],
        snapshot_timestamp=timestamp,
        model_version=model.model_version,
        algorithm=model.algorithm,
        risk_score=None,
        risk_level=None,
        predicted_label=None,
        decision_threshold=model.decision_threshold,
        prediction_applicable=False,
        reason="DETERMINISTIC_THRESHOLD_ALREADY_EXCEEDED",
    )
    install_prediction_stub(monkeypatch, [not_applicable])
    response = client.post(f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate")
    assert response.json()["outcome"] == "NOT_APPLICABLE"
    assert client.get("/api/v1/alerts/summary").json()["total_alerts"] == 0


def test_open_alert_is_reevaluated_up_and_down_without_automatic_resolution(
    client, db_session: Session, monkeypatch
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    original = make_prediction(db_session, commercial_case, model, timestamp, score=0.80)
    higher = make_prediction(db_session, commercial_case, model, timestamp + timedelta(hours=1), score=0.90)
    lower = make_prediction(
        db_session, commercial_case, model, timestamp + timedelta(hours=2), score=0.45, label=False
    )
    install_prediction_stub(
        monkeypatch,
        [prediction_read(original), prediction_read(higher), prediction_read(lower)],
    )
    path = f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate"
    created = client.post(path).json()
    assert client.post(path).json()["outcome"] == "UPDATED"
    lowered = client.post(path).json()
    assert lowered["outcome"] == "UPDATED"
    assert lowered["alert"]["status"] == "ACTIVE"
    assert lowered["alert"]["risk_score"] == 0.45
    actions = client.get(f"/api/v1/alerts/{created['alert']['id']}/actions").json()
    assert [item["action_type"] for item in actions] == [
        "CREATED", "RISK_REEVALUATED", "RISK_REEVALUATED"
    ]
    assert actions[-1]["details"]["previous_risk_score"] == 0.9
    assert actions[-1]["details"]["new_risk_score"] == 0.45


def test_state_transitions_notes_and_conflicts_are_audited(
    client, db_session: Session, monkeypatch
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    prediction = make_prediction(db_session, commercial_case, model, timestamp, score=0.88)
    install_prediction_stub(monkeypatch, [prediction_read(prediction)])
    alert = client.post(
        f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate"
    ).json()["alert"]
    alert_id = alert["id"]

    assert client.post(f"/api/v1/alerts/{alert_id}/resolve", json={}).status_code == 409
    assert client.post(f"/api/v1/alerts/{alert_id}/actions", json={"notes": "   "}).status_code == 422
    note = client.post(
        f"/api/v1/alerts/{alert_id}/actions",
        json={"actor": "Jefe Comercial", "notes": "Seguimiento iniciado"},
    )
    assert note.status_code == 201
    attended = client.post(
        f"/api/v1/alerts/{alert_id}/attend",
        json={"actor": "Jefe Comercial", "notes": "Cliente contactado"},
    )
    assert attended.json()["status"] == "ATTENDED"
    resolved = client.post(
        f"/api/v1/alerts/{alert_id}/resolve",
        json={"actor": "Jefe Comercial", "notes": "Seguimiento concluido"},
    )
    assert resolved.json()["status"] == "RESOLVED"
    assert client.post(f"/api/v1/alerts/{alert_id}/attend", json={}).status_code == 409
    assert client.post(
        f"/api/v1/alerts/{alert_id}/actions", json={"notes": "Tardía"}
    ).status_code == 409
    actions = client.get(f"/api/v1/alerts/{alert_id}/actions").json()
    assert [item["action_type"] for item in actions] == [
        "CREATED", "NOTE", "ATTENDED", "RESOLVED"
    ]


def test_dismiss_requires_reason_and_allows_both_open_states(
    client, db_session: Session, monkeypatch
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    prediction = make_prediction(db_session, commercial_case, model, timestamp, score=0.91)
    install_prediction_stub(monkeypatch, [prediction_read(prediction)])
    alert_id = client.post(
        f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate"
    ).json()["alert"]["id"]
    assert client.post(f"/api/v1/alerts/{alert_id}/dismiss", json={}).status_code == 422
    dismissed = client.post(
        f"/api/v1/alerts/{alert_id}/dismiss",
        json={"actor": "Supervisor", "notes": "Riesgo aceptado y documentado"},
    )
    assert dismissed.status_code == 200
    assert dismissed.json()["status"] == "DISMISSED"
    assert client.get("/api/v1/alerts/summary").json()["dismissed"] == 1


def test_closed_alert_stays_closed_and_later_snapshot_starts_new_cycle(
    client, db_session: Session, monkeypatch
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    original = make_prediction(db_session, commercial_case, model, timestamp, score=0.82)
    install_prediction_stub(monkeypatch, [prediction_read(original)])
    path = f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate"
    first = client.post(path).json()["alert"]
    client.post(f"/api/v1/alerts/{first['id']}/attend", json={})
    client.post(f"/api/v1/alerts/{first['id']}/resolve", json={})

    future_timestamp = datetime.now(UTC) + timedelta(days=1)
    later = make_prediction(db_session, commercial_case, model, future_timestamp, score=0.93)
    install_prediction_stub(monkeypatch, [prediction_read(later)])
    second = client.post(path, json={"as_of": future_timestamp.isoformat()})
    assert second.status_code == 200
    assert second.json()["outcome"] == "CREATED"
    assert second.json()["alert"]["id"] != first["id"]
    assert second.json()["alert"]["evaluation_mode"] == "HISTORICAL_REPLAY"
    assert len(client.get(f"/api/v1/cases/{commercial_case['id']}/alerts").json()) == 2


def test_latest_observation_rejects_closed_case_but_historical_replay_allows_it(
    client, db_session: Session, monkeypatch
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    case_model = db_session.get(CommercialCase, UUID(commercial_case["id"]))
    case_model.status = CaseStatus.CLOSED
    case_model.closed_at = timestamp + timedelta(days=1)
    prediction = make_prediction(db_session, commercial_case, model, timestamp, score=0.84)
    install_prediction_stub(monkeypatch, [prediction_read(prediction)])
    path = f"/api/v1/cases/{commercial_case['id']}/alerts/evaluate"
    assert client.post(path).json()["outcome"] == "INELIGIBLE"
    replay = client.post(path, json={"as_of": timestamp.isoformat()})
    assert replay.json()["outcome"] == "CREATED"
    assert replay.json()["alert"]["evaluation_mode"] == "HISTORICAL_REPLAY"


def test_batch_counters_and_limit_validation(client, db_session: Session, monkeypatch) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    high = make_prediction(db_session, commercial_case, model, timestamp, score=0.89)
    install_prediction_stub(monkeypatch, [prediction_read(high)])
    response = client.post(
        "/api/v1/alerts/evaluate",
        json={"case_ids": [commercial_case["id"]], "limit": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cases_evaluated"] == body["predictions_created"] == body["alerts_created"] == 1
    assert body["predictions_reused"] == body["alerts_updated"] == 0
    assert client.post("/api/v1/alerts/evaluate", json={"limit": 101}).status_code == 422


def test_batch_counts_high_low_not_applicable_and_no_observable_state(
    client, db_session: Session, monkeypatch
) -> None:
    high_case, model, timestamp = setup_case(client, db_session, case_code="CASE-BATCH-HIGH")
    stored_case = db_session.get(CommercialCase, UUID(high_case["id"]))
    stage_id = str(stored_case.current_stage_id)
    low_case = create_case(client, stage_id, case_code="CASE-BATCH-LOW")
    not_applicable_case = create_case(client, stage_id, case_code="CASE-BATCH-NA")
    no_state_case = create_case(client, stage_id, case_code="CASE-BATCH-NO-STATE")
    for commercial_case in (low_case, not_applicable_case):
        response = client.post(
            f"/api/v1/cases/{commercial_case['id']}/events",
            json={
                "stage_id": stage_id,
                "activity": "Lead",
                "event_type": "STAGE_CHANGE",
                "resource": "Asesor",
                "timestamp": timestamp.isoformat(),
                "metadata": {},
            },
        )
        assert response.status_code == 201
    high_prediction = make_prediction(db_session, high_case, model, timestamp, score=0.87)
    low_prediction = make_prediction(
        db_session, low_case, model, timestamp, score=0.25, label=False
    )
    responses = {
        UUID(high_case["id"]): prediction_read(high_prediction),
        UUID(low_case["id"]): prediction_read(low_prediction),
        UUID(not_applicable_case["id"]): PredictionRead(
            id=None,
            case_id=not_applicable_case["id"],
            case_code=not_applicable_case["case_code"],
            snapshot_timestamp=timestamp,
            model_version=model.model_version,
            algorithm=model.algorithm,
            risk_score=None,
            risk_level=None,
            predicted_label=None,
            decision_threshold=model.decision_threshold,
            prediction_applicable=False,
            reason="DETERMINISTIC_THRESHOLD_ALREADY_EXCEEDED",
        ),
    }
    monkeypatch.setattr(
        "app.services.alert_service.prediction_service.predict_case",
        lambda _db, case_id, _as_of: responses[case_id],
    )
    response = client.post(
        "/api/v1/alerts/evaluate",
        json={
            "case_ids": [
                high_case["id"], low_case["id"],
                not_applicable_case["id"], no_state_case["id"],
            ],
            "limit": 4,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cases_evaluated"] == 4
    assert body["predictions_created"] == 2
    assert body["alerts_created"] == 1
    assert body["below_threshold"] == 1
    assert body["skipped_not_applicable"] == 1
    assert body["skipped_no_observable_state"] == 1
    assert body["cases_without_alert"] == 3


def test_partial_unique_constraint_prevents_two_open_alerts_per_case(
    db_session: Session, client
) -> None:
    commercial_case, model, timestamp = setup_case(client, db_session)
    first_prediction = make_prediction(db_session, commercial_case, model, timestamp, score=0.8)
    second_prediction = make_prediction(
        db_session, commercial_case, model, timestamp + timedelta(hours=1), score=0.9
    )

    def alert(prediction, code):
        return Alert(
            alert_code=code,
            case_id=UUID(commercial_case["id"]),
            origin_prediction_id=prediction.id,
            latest_prediction_id=prediction.id,
            status=AlertStatus.ACTIVE,
            risk_score=prediction.risk_score,
            risk_level=prediction.risk_level,
            title="Riesgo alto de desviación",
            description="Riesgo estimado.",
            evaluation_mode=AlertEvaluationMode.LATEST_OBSERVATION,
            fingerprint=uuid4().hex + uuid4().hex,
            last_evaluated_at=datetime.now(UTC),
        )

    db_session.add(alert(first_prediction, "ALR-000001"))
    db_session.commit()
    db_session.add(alert(second_prediction, "ALR-000002"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
