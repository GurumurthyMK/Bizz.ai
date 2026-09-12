"""Authentication tests: register, login, logout, current user, protection.

Uses an in-memory SQLite database via a ``get_db`` override so no live
PostgreSQL is required. Password hashing, JWT validation, and cookie
handling run exactly as in production.
"""

import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.user import User

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


def _db_user(email: str) -> User | None:
    with TestingSession() as db:
        return db.scalar(select(User).where(User.email == email))


def test_register_success_sets_session_cookie(app: FastAPI) -> None:
    with TestClient(app) as fresh:
        response = fresh.post(
            "/api/v1/auth/register",
            json={"email": "ana@example.com", "password": "s3cure-pass"},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "ana@example.com"
    assert body["user"]["id"]
    assert body["user"]["created_at"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "password_hash" not in body["user"]
    assert "s3cure-pass" not in response.text
    cookie = response.headers.get("set-cookie", "")
    assert settings.auth_cookie_name in cookie
    assert "httponly" in cookie.lower()


def test_password_is_hashed_not_stored_plaintext(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "hash@example.com", "password": "s3cure-pass"},
    )
    user = _db_user("hash@example.com")
    assert user is not None
    assert user.password_hash != "s3cure-pass"
    assert user.password_hash.startswith("$2b$")
    assert bcrypt.checkpw(b"s3cure-pass", user.password_hash.encode())


def test_register_duplicate_email_conflicts(client: TestClient) -> None:
    payload = {"email": "dupe@example.com", "password": "s3cure-pass"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_register_rejects_invalid_input(client: TestClient) -> None:
    bad_email = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "s3cure-pass"},
    )
    short_password = client.post(
        "/api/v1/auth/register", json={"email": "ok@example.com", "password": "short"}
    )
    assert bad_email.status_code == 422
    assert short_password.status_code == 422


def test_login_success_and_me_via_cookie(app: FastAPI, client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "li@example.com", "password": "s3cure-pass"},
    )
    with TestClient(app) as fresh:
        response = fresh.post(
            "/api/v1/auth/login",
            json={"email": "li@example.com", "password": "s3cure-pass"},
        )
        assert response.status_code == 200
        assert response.json()["user"]["email"] == "li@example.com"
        me = fresh.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "li@example.com"
    assert "password_hash" not in me.json()


def test_login_rejects_bad_credentials_without_leaking(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "real@example.com", "password": "s3cure-pass"},
    )
    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "real@example.com", "password": "wrong-pass"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "s3cure-pass"},
    )
    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    # Identical generic message: the endpoint must not reveal which accounts exist.
    assert wrong_password.json() == unknown_email.json()


def test_me_rejects_unauthenticated(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_tampered_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer tampered.token.here"}
    )
    assert response.status_code == 401


def test_me_accepts_bearer_fallback(app: FastAPI, client: TestClient) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "bearer@example.com", "password": "s3cure-pass"},
    )
    token = registered.json()["access_token"]
    with TestClient(app) as fresh:
        response = fresh.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "bearer@example.com"


def test_logout_clears_session(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "bye@example.com", "password": "s3cure-pass"},
    )
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
