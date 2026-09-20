from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import get_db
from app.main import app


class WorkingSession:
    def execute(self, _: object) -> None:
        return None


class FailingSession:
    def execute(self, _: object) -> None:
        raise SQLAlchemyError("postgresql://user:secret@database/example")


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> Generator[None, None, None]:
    yield
    app.dependency_overrides.clear()


def test_health_returns_expected_payload() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "backend"}


def test_database_health_returns_connected() -> None:
    app.dependency_overrides[get_db] = lambda: WorkingSession()

    with TestClient(app) as client:
        response = client.get("/api/v1/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_database_health_hides_connection_details() -> None:
    app.dependency_overrides[get_db] = lambda: FailingSession()

    with TestClient(app) as client:
        response = client.get("/api/v1/health/database")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database connection unavailable"}
    assert "secret" not in response.text
