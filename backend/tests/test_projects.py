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


@pytest.fixture
def auth_headers(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "proj@example.com", "password": "pass12345", "full_name": "Proj User"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "proj@example.com", "password": "pass12345"},
    )
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_project(client, auth_headers):
    resp = client.post(
        "/api/v1/projects",
        json={"name": "My Project", "description": "Test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["name"] == "My Project"
    assert "id" in resp.json()["data"]


def test_list_projects(client, auth_headers):
    client.post("/api/v1/projects", json={"name": "P1"}, headers=auth_headers)
    client.post("/api/v1/projects", json={"name": "P2"}, headers=auth_headers)
    resp = client.get("/api/v1/projects", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) >= 2


def test_get_project(client, auth_headers):
    create = client.post("/api/v1/projects", json={"name": "GetMe"}, headers=auth_headers)
    pid = create.json()["data"]["id"]
    resp = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == pid


def test_get_project_other_user_forbidden(client, db_session):
    # Register two users
    client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "pass12345", "full_name": "Owner"},
    )
    login1 = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "pass12345"},
    )
    headers1 = {"Authorization": f"Bearer {login1.json()['data']['access_token']}"}

    client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "pass12345", "full_name": "Other"},
    )
    login2 = client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "pass12345"},
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}

    # Owner creates project
    create = client.post("/api/v1/projects", json={"name": "Private"}, headers=headers1)
    pid = create.json()["data"]["id"]

    # Other user tries to access it → 403
    resp = client.get(f"/api/v1/projects/{pid}", headers=headers2)
    assert resp.status_code == 403


def test_delete_project(client, auth_headers):
    create = client.post("/api/v1/projects", json={"name": "Delete Me"}, headers=auth_headers)
    pid = create.json()["data"]["id"]
    resp = client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert resp.status_code == 204
    get_resp = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_update_project(client, auth_headers):
    create = client.post("/api/v1/projects", json={"name": "Old Name"}, headers=auth_headers)
    pid = create.json()["data"]["id"]
    resp = client.patch(f"/api/v1/projects/{pid}", json={"name": "New Name"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "New Name"


def test_update_project_empty_body_is_noop(client, auth_headers):
    create = client.post("/api/v1/projects", json={"name": "Stable Name"}, headers=auth_headers)
    pid = create.json()["data"]["id"]
    resp = client.patch(f"/api/v1/projects/{pid}", json={}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Stable Name"
