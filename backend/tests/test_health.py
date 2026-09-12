"""Backend tests for Phase 1A foundation.

``test_health`` hits the liveness endpoint without a database.
``test_db_health_*`` cover the database verification endpoint with an
overridden ``get_db`` dependency so no real PostgreSQL is required.
"""

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import create_app


def make_client() -> TestClient:
    return TestClient(create_app())


def test_health() -> None:
    client = make_client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"]
    assert body["environment"]


def test_root_health() -> None:
    client = make_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class _FakeSession:
    def execute(self, *args: object, **kwargs: object) -> None:
        # Accept any statement; emulate a successful SELECT 1.
        assert str(args[0]) == str(text("SELECT 1"))
        return None


def _override_get_db_success():  # type: ignore[no-untyped-def]
    yield _FakeSession()


def test_db_health_connected() -> None:
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db_success
    client = TestClient(app)
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}
    app.dependency_overrides.clear()


def _override_get_db_failure():  # type: ignore[no-untyped-def]
    raise RuntimeError("boom")
    yield None


def test_db_health_failure_returns_503_without_internals() -> None:
    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db_failure
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/health/db")
    assert response.status_code in (500, 503)
    assert "boom" not in response.text
