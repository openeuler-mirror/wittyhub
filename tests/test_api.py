import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "skillhub"}


def test_list_skills_empty(client):
    response = client.get("/api/v1/skills/")
    assert response.status_code == 200
    data = response.json()
    assert "skills" in data
    assert "total" in data


def test_get_skill_not_found(client):
    response = client.get("/api/v1/skills/nonexistent")
    assert response.status_code == 404


def test_search_endpoint(client):
    response = client.get("/api/v1/index/search", params={"q": "test"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
