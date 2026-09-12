"""Shared fixtures for business-data API tests.

In-memory SQLite via a ``get_db`` override; hashing/JWT/cookies run as in
production. The database persists across tests in a session, so tests use
unique values (see ``unique`` fixture) instead of assuming empty tables.

NOTE: test_auth.py defines its own local ``app``/``client`` fixtures, which
take precedence there. This file serves the business-data test modules.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def _override_get_db():  # type: ignore[no-untyped-def]
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def app() -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def unique() -> str:
    """Short unique suffix so tests never collide on emails/skus/names."""
    return uuid.uuid4().hex[:8]


@pytest.fixture()
def auth_client(app: FastAPI, unique: str) -> TestClient:
    """TestClient holding a registered user's session cookie."""
    test_client = TestClient(app)
    response = test_client.post(
        "/api/v1/auth/register",
        json={"email": f"owner-{unique}@example.com", "password": "s3cure-pass"},
    )
    assert response.status_code == 201
    return test_client


@pytest.fixture(scope="module")
def ml_db() -> Session:
    """Isolated ML database: own in-memory SQLite, seeded once per module.

    Never touches the shared TestingSession store, so seeding here cannot
    disturb other test modules. Lazy — only built when an ML test requests it.
    """
    from app.seed.generator import SeedConfig
    from app.seed.seeder import seed_dataset

    ml_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(ml_engine)
    factory = sessionmaker(bind=ml_engine, autoflush=False, autocommit=False)
    db: Session = factory()
    seed_dataset(db, SeedConfig(seed=11, customers=300), reset=True)
    yield db
    db.close()
