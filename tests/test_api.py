"""
Basic API tests - require database connection
These tests verify the actual API endpoints work with mocking where needed
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint - no DB required"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "skillhub"}


def test_list_skills_with_mock(client):
    """Test list skills endpoint with proper mocking"""
    with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.list.return_value = ([], 0)
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        assert "total" in data


def test_get_skill_with_mock(client):
    """Test get skill endpoint with proper mocking"""
    with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_by_skill_id.return_value = None
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/skills/nonexistent")
        assert response.status_code == 404


def test_search_with_mock(client):
    """Test search endpoint with proper mocking"""
    with patch("src.api.routes.index.SearchService") as mock_search_class:
        mock_search = AsyncMock()
        mock_search.search_skills.return_value = {"results": [], "total": 0}
        mock_search_class.return_value = mock_search

        response = client.get("/api/v1/index/search", params={"q": "test"})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data


def test_categories_with_mock(client):
    """Test categories endpoint with proper mocking"""
    with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {
            "total_skills": 0,
            "total_categories": 0,
            "categories": []
        }
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/index/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data


def test_stats_with_mock(client):
    """Test stats endpoint with proper mocking"""
    with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {
            "total_skills": 10,
            "total_categories": 5,
            "categories": [{"name": "AI", "count": 10}]
        }
        mock_repo_class.return_value = mock_repo

        response = client.get("/api/v1/index/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_skills" in data
        assert "total_categories" in data
        assert "categories" in data
