import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_register_success(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "password123", "full_name": "Test User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["success"] is True
    assert "user_id" in data["data"]


def test_register_duplicate_email(client):
    payload = {"email": "dupe@example.com", "password": "pass123", "full_name": "Dupe"}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_success(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "pass123", "full_name": "Login User"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "pass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data["data"]


def test_login_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "correct", "full_name": "User"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "incorrect"},
    )
    assert resp.status_code == 401


def test_me_authenticated(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "password": "pass123", "full_name": "Me User"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "pass123"},
    )
    token = login.json()["data"]["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "me@example.com"


def test_me_no_auth_header(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 403


def test_me_invalid_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
