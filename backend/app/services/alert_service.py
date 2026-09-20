import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, DomainValidationError, PersistenceError, ResourceNotFoundError
from app.models.alert import Alert, AlertAction
from app.models.commercial_case import CommercialCase
from app.models.enums import (
    AlertActionType,
    AlertEvaluationMode,
    AlertStatus,
    CaseStatus,
    RiskLevel,
)
from app.models.prediction import Prediction
from app.repositories import alert_repository
from app.schemas.alert import (
    AlertActionRead,
    AlertBatchRead,
    AlertDetail,
    AlertEvaluationRead,
    AlertList,
    AlertPredictionRead,
    AlertRead,
    AlertSummary,
)
from app.schemas.prediction import RiskFactor
from app.services import prediction_service

ALERT_RULE_VERSION = "alert-rule-v1"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _alert_fingerprint(prediction: Prediction) -> str:
    canonical = json.dumps(
        {
            "case_id": str(prediction.case_id),
            "origin_prediction_id": str(prediction.id),
            "model_version": prediction.model_run.model_version,
            "snapshot_timestamp": _utc(prediction.snapshot_timestamp).isoformat(),
            "rule_version": ALERT_RULE_VERSION,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _read(alert: Alert) -> AlertRead:
    return AlertRead(
        id=alert.id,
        alert_code=alert.alert_code,
        case_id=alert.case_id,
        case_code=alert.commercial_case.case_code,
        status=alert.status,
        risk_score=alert.risk_score,
        risk_level=alert.risk_level,
        title=alert.title,
        description=alert.description,
        evaluation_mode=alert.evaluation_mode,
        triggered_at=alert.triggered_at,
        last_evaluated_at=alert.last_evaluated_at,
        attended_at=alert.attended_at,
        resolved_at=alert.resolved_at,
        dismissed_at=alert.dismissed_at,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
    )


def _prediction_read(prediction: Prediction) -> AlertPredictionRead:
    return AlertPredictionRead(
        id=prediction.id,
        model_version=prediction.model_run.model_version,
        snapshot_timestamp=prediction.snapshot_timestamp,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        predicted_label=prediction.predicted_label,
    )


def _detail(alert: Alert) -> AlertDetail:
    latest = alert.latest_prediction
    return AlertDetail(
        **_read(alert).model_dump(),
        origin_prediction=_prediction_read(alert.origin_prediction),
        latest_prediction=_prediction_read(latest),
        model_version=latest.model_run.model_version,
        snapshot_timestamp=latest.snapshot_timestamp,
        current_factors=[RiskFactor.model_validate(item) for item in latest.explanation],
    )


def _action_read(action: AlertAction) -> AlertActionRead:
    return AlertActionRead(
        id=action.id,
        alert_id=action.alert_id,
        action_type=action.action_type,
        actor=action.actor,
        notes=action.notes,
        previous_status=action.previous_status,
        new_status=action.new_status,
        prediction_id=action.prediction_id,
        details=action.details,
        created_at=action.created_at,
    )


def _result(
    *,
    case_id: UUID,
    case_code: str,
    mode: AlertEvaluationMode,
    outcome,
    message: str,
    prediction=None,
    alert: Alert | None = None,
) -> AlertEvaluationRead:
    return AlertEvaluationRead(
        case_id=case_id,
        case_code=case_code,
        evaluation_mode=mode,
        outcome=outcome,
        prediction=prediction,
        alert=_read(alert) if alert is not None else None,
        alert_risk_threshold=get_settings().alert_risk_threshold,
        message=message,
    )


def evaluate_case(db: Session, case_id: UUID, as_of: datetime | None = None) -> AlertEvaluationRead:
    commercial_case = db.get(CommercialCase, case_id)
    if commercial_case is None:
        raise ResourceNotFoundError("Caso comercial no encontrado")
    mode = (
        AlertEvaluationMode.HISTORICAL_REPLAY
        if as_of is not None
        else AlertEvaluationMode.LATEST_OBSERVATION
    )
    if as_of is None and commercial_case.status != CaseStatus.ACTIVE:
        return _result(
            case_id=case_id,
            case_code=commercial_case.case_code,
            mode=mode,
            outcome="INELIGIBLE",
            message="El caso no está ACTIVE para evaluación de última observación",
        )
    if not alert_repository.has_observable_event(db, case_id, as_of):
        return _result(
            case_id=case_id,
            case_code=commercial_case.case_code,
            mode=mode,
            outcome="NO_OBSERVABLE_STATE",
            message="No existe estado observable para el momento solicitado",
        )

    prediction_read = prediction_service.predict_case(db, case_id, as_of)
    if not prediction_read.prediction_applicable:
        return _result(
            case_id=case_id,
            case_code=commercial_case.case_code,
            mode=mode,
            outcome="NOT_APPLICABLE",
            message="La predicción temprana no aplica porque ya se superó un umbral determinístico",
            prediction=prediction_read,
        )
    if prediction_read.id is None:
        raise PersistenceError("La predicción aplicable no fue persistida")
    prediction = alert_repository.get_prediction(db, prediction_read.id)
    if prediction is None:
        raise PersistenceError("No fue posible recuperar la predicción persistida")

    now = datetime.now(UTC)
    open_alert = alert_repository.get_open_for_case(db, case_id, lock=True)
    if open_alert is not None:
        if open_alert.latest_prediction_id == prediction.id:
            return _result(
                case_id=case_id,
                case_code=commercial_case.case_code,
                mode=mode,
                outcome="NO_CHANGE",
                message="La misma predicción ya fue evaluada; no se duplicó la auditoría",
                prediction=prediction_read,
                alert=open_alert,
            )
        previous_score = open_alert.risk_score
        previous_level = open_alert.risk_level
        previous_prediction_id = open_alert.latest_prediction_id
        open_alert.latest_prediction_id = prediction.id
        open_alert.latest_prediction = prediction
        open_alert.risk_score = prediction.risk_score
        open_alert.risk_level = prediction.risk_level
        open_alert.evaluation_mode = mode
        open_alert.last_evaluated_at = now
        db.add(
            AlertAction(
                alert=open_alert,
                action_type=AlertActionType.RISK_REEVALUATED,
                previous_status=open_alert.status,
                new_status=open_alert.status,
                prediction_id=prediction.id,
                details={
                    "previous_risk_score": previous_score,
                    "new_risk_score": prediction.risk_score,
                    "previous_risk_level": previous_level.value,
                    "new_risk_level": prediction.risk_level.value,
                    "previous_prediction_id": str(previous_prediction_id),
                    "new_prediction_id": str(prediction.id),
                },
                created_at=now,
            )
        )
        try:
            db.commit()
            db.refresh(open_alert)
        except Exception as exc:
            db.rollback()
            raise PersistenceError("No fue posible registrar la reevaluación de riesgo") from exc
        return _result(
            case_id=case_id,
            case_code=commercial_case.case_code,
            mode=mode,
            outcome="UPDATED",
            message="La alerta abierta fue reevaluada sin cerrarse automáticamente",
            prediction=prediction_read,
            alert=open_alert,
        )

    threshold = get_settings().alert_risk_threshold
    if not prediction.predicted_label or prediction.risk_score < threshold:
        return _result(
            case_id=case_id,
            case_code=commercial_case.case_code,
            mode=mode,
            outcome="BELOW_THRESHOLD",
            message="La predicción existe, pero no cumple ambas reglas de generación de alerta",
            prediction=prediction_read,
        )

    fingerprint = _alert_fingerprint(prediction)
    existing = alert_repository.get_by_fingerprint(db, fingerprint)
    if existing is not None:
        return _result(
            case_id=case_id,
            case_code=commercial_case.case_code,
            mode=mode,
            outcome="NO_CHANGE",
            message="Esta predicción ya originó un ciclo de alerta",
            prediction=prediction_read,
            alert=existing,
        )

    latest_closed = alert_repository.latest_closed_for_case(db, case_id)
    if latest_closed is not None:
        closed_at = latest_closed.resolved_at or latest_closed.dismissed_at
        if closed_at is not None and _utc(prediction.snapshot_timestamp) <= _utc(closed_at):
            return _result(
                case_id=case_id,
                case_code=commercial_case.case_code,
                mode=mode,
                outcome="CLOSED_CYCLE_NOT_NEW",
                message="La predicción no es posterior al cierre del ciclo anterior",
                prediction=prediction_read,
            )

    alert = Alert(
        alert_code=alert_repository.next_alert_code(db),
        case_id=case_id,
        commercial_case=commercial_case,
        origin_prediction_id=prediction.id,
        origin_prediction=prediction,
        latest_prediction_id=prediction.id,
        latest_prediction=prediction,
        status=AlertStatus.ACTIVE,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        title="Riesgo alto de desviación",
        description=(
            f"El caso {commercial_case.case_code} presenta un riesgo estimado elevado de "
            "desviación antes de su próxima transición."
        ),
        evaluation_mode=mode,
        fingerprint=fingerprint,
        last_evaluated_at=now,
    )
    created_action = AlertAction(
        alert=alert,
        action_type=AlertActionType.CREATED,
        previous_status=None,
        new_status=AlertStatus.ACTIVE,
        prediction_id=prediction.id,
        details={
            "alert_rule_version": ALERT_RULE_VERSION,
            "alert_risk_threshold": threshold,
            "decision_threshold": prediction.model_run.decision_threshold,
            "evaluation_mode": mode.value,
        },
        created_at=now,
    )
    try:
        db.add_all((alert, created_action))
        db.commit()
        db.refresh(alert)
    except IntegrityError as exc:
        db.rollback()
        concurrent = alert_repository.get_open_for_case(db, case_id) or alert_repository.get_by_fingerprint(db, fingerprint)
        if concurrent is not None:
            return _result(
                case_id=case_id,
                case_code=commercial_case.case_code,
                mode=mode,
                outcome="NO_CHANGE",
                message="Otra evaluación concurrente ya creó la alerta equivalente",
                prediction=prediction_read,
                alert=concurrent,
            )
        raise PersistenceError("No fue posible crear la alerta predictiva") from exc
    except Exception as exc:
        db.rollback()
        raise PersistenceError("No fue posible crear la alerta predictiva") from exc
    return _result(
        case_id=case_id,
        case_code=commercial_case.case_code,
        mode=mode,
        outcome="CREATED",
        message="Se creó una alerta operativa a partir de la predicción de alto riesgo",
        prediction=prediction_read,
        alert=alert,
    )


def evaluate_batch(
    db: Session,
    *,
    as_of: datetime | None,
    case_id: UUID | None,
    case_ids: list[UUID] | None,
    limit: int,
) -> AlertBatchRead:
    settings = get_settings()
    if limit > settings.alert_batch_limit:
        raise DomainValidationError(
            f"limit no puede superar ALERT_BATCH_LIMIT={settings.alert_batch_limit}"
        )
    requested = list(dict.fromkeys(([case_id] if case_id else []) + (case_ids or []))) or None
    ids = alert_repository.candidate_case_ids(
        db, as_of=as_of, requested_ids=requested, limit=limit
    )
    results: list[AlertEvaluationRead] = []
    for candidate_id in ids:
        results.append(evaluate_case(db, candidate_id, as_of))
    outcomes = [item.outcome for item in results]
    predictions_created = sum(
        item.prediction is not None
        and item.prediction.prediction_applicable
        and item.prediction.id is not None
        and not item.prediction.prediction_reused
        for item in results
    )
    predictions_reused = sum(
        item.prediction is not None
        and item.prediction.prediction_applicable
        and item.prediction.id is not None
        and item.prediction.prediction_reused
        for item in results
    )
    no_alert_outcomes = {
        "BELOW_THRESHOLD", "NOT_APPLICABLE", "INELIGIBLE", "NO_OBSERVABLE_STATE",
        "CLOSED_CYCLE_NOT_NEW",
    }
    return AlertBatchRead(
        evaluation_mode=(
            AlertEvaluationMode.HISTORICAL_REPLAY
            if as_of is not None
            else AlertEvaluationMode.LATEST_OBSERVATION
        ),
        alert_risk_threshold=settings.alert_risk_threshold,
        cases_evaluated=len(results),
        predictions_created=predictions_created,
        predictions_reused=predictions_reused,
        alerts_created=outcomes.count("CREATED"),
        alerts_updated=outcomes.count("UPDATED"),
        below_threshold=outcomes.count("BELOW_THRESHOLD"),
        skipped_not_applicable=outcomes.count("NOT_APPLICABLE"),
        skipped_no_observable_state=outcomes.count("NO_OBSERVABLE_STATE"),
        skipped_ineligible=outcomes.count("INELIGIBLE"),
        unchanged=outcomes.count("NO_CHANGE") + outcomes.count("CLOSED_CYCLE_NOT_NEW"),
        cases_without_alert=sum(outcome in no_alert_outcomes for outcome in outcomes),
        results=results,
    )


def list_alerts(
    db: Session,
    *,
    status: AlertStatus | None,
    risk_level: RiskLevel | None,
    case_code: str | None,
    min_risk_score: float | None,
    page: int,
    page_size: int,
) -> AlertList:
    items, total = alert_repository.list_alerts(
        db,
        status=status,
        risk_level=risk_level,
        case_code=case_code,
        min_risk_score=min_risk_score,
        offset=(page - 1) * page_size,
        limit=page_size,
    )
    return AlertList(items=[_read(item) for item in items], page=page, page_size=page_size, total=total)


def get_alert(db: Session, alert_id: UUID) -> AlertDetail:
    alert = alert_repository.get_alert(db, alert_id)
    if alert is None:
        raise ResourceNotFoundError("Alerta no encontrada")
    return _detail(alert)


def alerts_for_case(db: Session, case_id: UUID) -> list[AlertRead]:
    if db.get(CommercialCase, case_id) is None:
        raise ResourceNotFoundError("Caso comercial no encontrado")
    return [_read(item) for item in alert_repository.list_for_case(db, case_id)]


def actions_for_alert(db: Session, alert_id: UUID) -> list[AlertActionRead]:
    if alert_repository.get_alert(db, alert_id) is None:
        raise ResourceNotFoundError("Alerta no encontrada")
    return [_action_read(item) for item in alert_repository.list_actions(db, alert_id)]


def add_note(db: Session, alert_id: UUID, *, actor: str | None, notes: str) -> AlertActionRead:
    alert = alert_repository.get_alert(db, alert_id, lock=True)
    if alert is None:
        raise ResourceNotFoundError("Alerta no encontrada")
    if alert.status not in (AlertStatus.ACTIVE, AlertStatus.ATTENDED):
        raise ConflictError("No se pueden agregar notas a una alerta cerrada")
    action = AlertAction(
        alert_id=alert.id,
        action_type=AlertActionType.NOTE,
        actor=actor,
        notes=notes,
        previous_status=alert.status,
        new_status=alert.status,
        prediction_id=alert.latest_prediction_id,
        created_at=datetime.now(UTC),
    )
    try:
        db.add(action)
        db.commit()
        db.refresh(action)
    except Exception as exc:
        db.rollback()
        raise PersistenceError("No fue posible registrar la nota") from exc
    return _action_read(action)


def _transition(
    db: Session,
    alert_id: UUID,
    *,
    target: AlertStatus,
    actor: str | None,
    notes: str | None,
) -> AlertDetail:
    allowed = {
        AlertStatus.ATTENDED: (AlertStatus.ACTIVE,),
        AlertStatus.RESOLVED: (AlertStatus.ATTENDED,),
        AlertStatus.DISMISSED: (AlertStatus.ACTIVE, AlertStatus.ATTENDED),
    }
    alert = alert_repository.get_alert(db, alert_id, lock=True)
    if alert is None:
        raise ResourceNotFoundError("Alerta no encontrada")
    if alert.status not in allowed[target]:
        raise ConflictError(f"Transición inválida: {alert.status.value} → {target.value}")
    previous = alert.status
    now = datetime.now(UTC)
    alert.status = target
    if target == AlertStatus.ATTENDED:
        alert.attended_at = now
    elif target == AlertStatus.RESOLVED:
        alert.resolved_at = now
    else:
        alert.dismissed_at = now
    db.add(
        AlertAction(
            alert_id=alert.id,
            action_type=AlertActionType(target.value),
            actor=actor,
            notes=notes,
            previous_status=previous,
            new_status=target,
            prediction_id=alert.latest_prediction_id,
            created_at=now,
        )
    )
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise PersistenceError("No fue posible cambiar el estado de la alerta") from exc
    refreshed = alert_repository.get_alert(db, alert.id)
    if refreshed is None:
        raise PersistenceError("No fue posible recuperar la alerta actualizada")
    return _detail(refreshed)


def attend(db: Session, alert_id: UUID, *, actor: str | None, notes: str | None) -> AlertDetail:
    return _transition(db, alert_id, target=AlertStatus.ATTENDED, actor=actor, notes=notes)


def resolve(db: Session, alert_id: UUID, *, actor: str | None, notes: str | None) -> AlertDetail:
    return _transition(db, alert_id, target=AlertStatus.RESOLVED, actor=actor, notes=notes)


def dismiss(db: Session, alert_id: UUID, *, actor: str | None, notes: str) -> AlertDetail:
    return _transition(db, alert_id, target=AlertStatus.DISMISSED, actor=actor, notes=notes)


def get_summary(db: Session) -> AlertSummary:
    return AlertSummary(**alert_repository.summary(db))
