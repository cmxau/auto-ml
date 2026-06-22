import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

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
        json={"email": "ds@example.com", "password": "pass12345", "full_name": "DS User"},
    )
    resp = client.post("/api/v1/auth/login", json={"email": "ds@example.com", "password": "pass12345"})
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}"}


@pytest.fixture
def project_id(client, auth_headers):
    resp = client.post("/api/v1/projects", json={"name": "Test Project"}, headers=auth_headers)
    return resp.json()["data"]["id"]


def make_csv():
    return io.BytesIO(b"name,age,city\nAlice,30,NYC\nBob,25,LA\n")


def test_upload_dataset_csv(client, auth_headers, project_id):
    with patch("app.services.storage_service.StorageService.upload_file") as mock_upload, \
         patch("app.workers.profiling_worker.profile_dataset_task") as mock_task:
        mock_upload.return_value = "datasets/test/test.csv"
        mock_task_instance = MagicMock()
        mock_task_instance.id = "task-123"
        mock_task.delay.return_value = mock_task_instance

        resp = client.post(
            "/api/v1/datasets/upload",
            data={"project_id": project_id},
            files={"file": ("test.csv", make_csv(), "text/csv")},
            headers=auth_headers,
        )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "dataset_id" in data
    assert "job_id" in data


def test_upload_rejects_invalid_format(client, auth_headers, project_id):
    resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": project_id},
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_upload_rejects_wrong_project_owner(client, db_session):
    # Create second user and their project
    client.post(
        "/api/v1/auth/register",
        json={"email": "other2@example.com", "password": "pass12345", "full_name": "Other"},
    )
    login2 = client.post("/api/v1/auth/login", json={"email": "other2@example.com", "password": "pass12345"})
    h2 = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}
    other_proj = client.post("/api/v1/projects", json={"name": "Other Project"}, headers=h2)
    other_pid = other_proj.json()["data"]["id"]

    # First user tries to upload to second user's project
    client.post(
        "/api/v1/auth/register",
        json={"email": "user1@example.com", "password": "pass12345", "full_name": "User1"},
    )
    login1 = client.post("/api/v1/auth/login", json={"email": "user1@example.com", "password": "pass12345"})
    h1 = {"Authorization": f"Bearer {login1.json()['data']['access_token']}"}

    resp = client.post(
        "/api/v1/datasets/upload",
        data={"project_id": other_pid},
        files={"file": ("test.csv", make_csv(), "text/csv")},
        headers=h1,
    )
    assert resp.status_code == 403


def test_list_datasets(client, auth_headers, project_id):
    resp = client.get(f"/api/v1/projects/{project_id}/datasets", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)
