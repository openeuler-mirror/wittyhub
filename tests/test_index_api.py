"""
Comprehensive tests for Index API endpoints (search, stats, categories)
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


class TestSearchEndpoint:
    """Tests for GET /api/v1/index/search"""

    def test_search_basic(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "text",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = [["embedding"]]

                response = client.get("/api/v1/index/search?q=test")
                assert response.status_code == 200
                data = response.json()
                assert "results" in data
                assert "total" in data
                assert data["query"] == "test"

    def test_search_with_pagination(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 100,
                    "query": "test",
                    "skip": 10,
                    "limit": 50,
                    "mode": "text",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = None

                response = client.get("/api/v1/index/search?q=test&skip=10&limit=50")
                assert response.status_code == 200
                data = response.json()
                assert data["skip"] == 10
                assert data["limit"] == 50

    def test_search_with_category_filter(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "text",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = None

                response = client.get("/api/v1/index/search?q=test&category=DevTools")
                assert response.status_code == 200
                call_kwargs = mock_service.search_skills.call_args[1]
                assert call_kwargs["category"] == "DevTools"

    def test_search_with_platform_filter(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "text",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = None

                response = client.get("/api/v1/index/search?q=test&platform=claude")
                assert response.status_code == 200
                call_kwargs = mock_service.search_skills.call_args[1]
                assert call_kwargs["platform"] == "claude"

    def test_search_with_tags_filter(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "text",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = None

                response = client.get("/api/v1/index/search?q=test&tags=test,debug")
                assert response.status_code == 200
                call_kwargs = mock_service.search_skills.call_args[1]
                assert call_kwargs["tags"] == ["test", "debug"]

    def test_search_mode_text(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "text",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = None

                response = client.get("/api/v1/index/search?q=test&mode=text")
                assert response.status_code == 200
                call_kwargs = mock_service.search_skills.call_args[1]
                assert call_kwargs["mode"] == "text"

    def test_search_mode_semantic(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "semantic",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = [[0.1, 0.2, 0.3]]

                response = client.get("/api/v1/index/search?q=test&mode=semantic")
                assert response.status_code == 200

    def test_search_mode_hybrid(self, client):
        with patch("src.api.routes.index.SearchService") as mock_service_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_service = AsyncMock()
                mock_service.search_skills.return_value = {
                    "results": [],
                    "total": 0,
                    "query": "test",
                    "skip": 0,
                    "limit": 20,
                    "mode": "hybrid",
                }
                mock_service_class.return_value = mock_service
                mock_gen_emb.return_value = [[0.1, 0.2, 0.3]]

                response = client.get("/api/v1/index/search?q=test&mode=hybrid")
                assert response.status_code == 200
                call_kwargs = mock_service.search_skills.call_args[1]
                assert call_kwargs["mode"] == "hybrid"

    def test_search_invalid_mode(self, client):
        response = client.get("/api/v1/index/search?q=test&mode=invalid")
        assert response.status_code == 422

    def test_search_empty_query(self, client):
        response = client.get("/api/v1/index/search?q=")
        assert response.status_code == 422

    def test_search_missing_query(self, client):
        response = client.get("/api/v1/index/search")
        assert response.status_code == 422

    def test_search_limit_validation(self, client):
        response = client.get("/api/v1/index/search?q=test&limit=200")
        assert response.status_code == 422

    def test_search_negative_skip_validation(self, client):
        response = client.get("/api/v1/index/search?q=test&skip=-1")
        assert response.status_code == 422


class TestReindexEndpoint:
    """Tests for POST /api/v1/index/reindex"""

    def test_reindex_success(self, client):
        with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_skill = MagicMock()
                mock_skill.skill_id = "test/skill"
                mock_skill.name = "Test"
                mock_skill.description = "Test desc"
                mock_skill.content = None

                mock_repo = AsyncMock()
                mock_repo.list.return_value = ([mock_skill], 1)
                mock_repo.update_embedding = AsyncMock()
                mock_repo_class.return_value = mock_repo

                mock_gen_emb.return_value = [[0.1, 0.2, 0.3]]

                response = client.post("/api/v1/index/reindex")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert "indexed_count" in data


class TestReindexSkillEndpoint:
    """Tests for POST /api/v1/index/reindex/{skill_id}"""

    def test_reindex_single_skill_success(self, client):
        with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
            with patch("src.api.routes.index.generate_embeddings") as mock_gen_emb:
                mock_skill = MagicMock()
                mock_skill.skill_id = "test/skill"
                mock_skill.name = "Test"
                mock_skill.description = "Test desc"
                mock_skill.content = None

                mock_repo = AsyncMock()
                mock_repo.get_by_skill_id.return_value = mock_skill
                mock_repo.update_embedding = AsyncMock()
                mock_repo.update_last_indexed = AsyncMock()
                mock_repo_class.return_value = mock_repo

                mock_gen_emb.return_value = [[0.1, 0.2, 0.3]]

                response = client.post("/api/v1/index/reindex/test/skill")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["skill_id"] == "test/skill"

    def test_reindex_single_skill_not_found(self, client):
        with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.post("/api/v1/index/reindex/nonexistent")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"


class TestStatsEndpoint:
    """Tests for GET /api/v1/index/stats"""

    def test_stats_success(self, client):
        with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_stats.return_value = {
                "total_skills": 100,
                "total_categories": 5,
                "categories": [
                    {"name": "DevTools", "count": 30},
                    {"name": "AI", "count": 25},
                ],
            }
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/index/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["total_skills"] == 100
            assert data["total_categories"] == 5
            assert "categories" in data


class TestCategoriesEndpoint:
    """Tests for GET /api/v1/index/categories"""

    def test_categories_success(self, client):
        with patch("src.api.routes.index.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_stats.return_value = {
                "total_skills": 100,
                "total_categories": 5,
                "categories": [
                    {"name": "DevTools", "count": 30},
                    {"name": "AI", "count": 25},
                ],
            }
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/index/categories")
            assert response.status_code == 200
            data = response.json()
            assert "categories" in data
            assert len(data["categories"]) == 2
