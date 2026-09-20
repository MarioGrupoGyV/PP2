from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event as sqlalchemy_event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import PersistenceError
from app.models.commercial_case import CommercialCase
from app.models.event import Event
from app.schemas.event import EventCreate
from app.services import event_service
from tests.helpers import create_case, create_stage


def test_event_timeline_is_ordered_and_stage_change_updates_case(
    client: TestClient,
) -> None:
    lead = create_stage(client)
    contacted = create_stage(
        client,
        code="CONTACTED",
        name="Contactado",
        sequence=2,
        sla_hours=48,
    )
    qualified = create_stage(
        client,
        code="QUALIFIED",
        name="Calificado",
        sequence=3,
        sla_hours=72,
    )
    commercial_case = create_case(client, str(lead["id"]))
    case_id = commercial_case["id"]

    events = [
        {
            "stage_id": contacted["id"],
            "activity": "Contactado",
            "event_type": "STAGE_CHANGE",
            "resource": "Asesor 01",
            "timestamp": "2026-09-19T10:00:00Z",
            "metadata": {"channel": "whatsapp", "result": "answered"},
        },
        {
            "stage_id": lead["id"],
            "activity": "Lead",
            "event_type": "STAGE_CHANGE",
            "timestamp": "2026-09-19T09:00:00Z",
            "metadata": {},
        },
        {
            "stage_id": qualified["id"],
            "activity": "Calificado",
            "event_type": "STAGE_CHANGE",
            "timestamp": "2026-09-19T11:00:00Z",
            "metadata": {"score": 85},
        },
    ]
    responses = [
        client.post(f"/api/v1/cases/{case_id}/events", json=payload)
        for payload in events
    ]

    timeline = client.get(f"/api/v1/cases/{case_id}/events")
    updated_case = client.get(f"/api/v1/cases/{case_id}")
    all_events = client.get("/api/v1/events")

    assert all(response.status_code == 201 for response in responses)
    assert responses[0].json()["metadata"] == {
        "channel": "whatsapp",
        "result": "answered",
    }
    assert timeline.status_code == 200
    assert [event["activity"] for event in timeline.json()] == [
        "Lead",
        "Contactado",
        "Calificado",
    ]
    assert updated_case.json()["current_stage_id"] == qualified["id"]
    assert all_events.json()["total"] == 3


def test_rejects_event_for_unknown_case(client: TestClient) -> None:
    stage = create_stage(client)

    response = client.post(
        f"/api/v1/cases/{uuid4()}/events",
        json={
            "stage_id": stage["id"],
            "activity": "Lead",
            "event_type": "STAGE_CHANGE",
            "timestamp": "2026-09-19T09:00:00Z",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Commercial case not found"}


def test_rejects_event_for_unknown_stage(client: TestClient) -> None:
    stage = create_stage(client)
    commercial_case = create_case(client, str(stage["id"]))

    response = client.post(
        f"/api/v1/cases/{commercial_case['id']}/events",
        json={
            "stage_id": str(uuid4()),
            "activity": "Etapa inexistente",
            "event_type": "STAGE_CHANGE",
            "timestamp": "2026-09-19T09:00:00Z",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Process stage not found"}


def test_event_failure_rolls_back_case_stage(
    client: TestClient,
    db_session: Session,
) -> None:
    lead = create_stage(client)
    contacted = create_stage(
        client,
        code="CONTACTED",
        name="Contactado",
        sequence=2,
        sla_hours=48,
    )
    commercial_case = create_case(client, str(lead["id"]))
    case_id = UUID(str(commercial_case["id"]))

    @sqlalchemy_event.listens_for(db_session, "before_flush", once=True)
    def force_event_failure(*_: object) -> None:
        raise SQLAlchemyError("forced event failure")

    payload = EventCreate(
        stage_id=UUID(str(contacted["id"])),
        activity="Contactado",
        event_type="STAGE_CHANGE",
        timestamp=datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc),
        metadata={"channel": "whatsapp"},
    )

    with pytest.raises(PersistenceError):
        event_service.create_event(db_session, case_id, payload)

    db_session.expire_all()
    stored_case = db_session.get(CommercialCase, case_id)
    event_count = db_session.scalar(select(func.count()).select_from(Event))

    assert stored_case is not None
    assert str(stored_case.current_stage_id) == lead["id"]
    assert event_count == 0
