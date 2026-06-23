"""
Comprehensive tests for Skills API endpoints
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.models import Skill


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_skill():
    """Create a mock skill object"""
    skill = MagicMock(spec=Skill)
    skill.id = uuid.uuid4()
    skill.skill_id = "test/skill:v1.0.0"
    skill.name = "Test Skill"
    skill.description = "A test skill description"
    skill.version = "v1.0.0"
    skill.commit_id = "abc123"
    skill.author = "test_author"
    skill.source = "github"
    skill.source_url = "https://github.com/test/skill"
    skill.category = "DevTools"
    skill.tags = ["test", "mock"]
    skill.platform = "claude"
    skill.extra_metadata = {}
    skill.content = "Skill content here"
    skill.security_score = 95
    skill.download_count = 100
    skill.rating = "4.5"
    skill.created_at = datetime.now(timezone.utc)
    skill.updated_at = datetime.now(timezone.utc)
    skill.last_indexed_at = None
    skill.embedding = None
    return skill


@pytest.fixture
def mock_skill_dict():
    """Create a mock skill dictionary for creation"""
    return {
        "skill_id": "test/skill:v1.0.0",
        "name": "Test Skill",
        "description": "A test skill description",
        "version": "v1.0.0",
        "commit_id": "abc123",
        "author": "test_author",
        "source": "github",
        "source_url": "https://github.com/test/skill",
        "category": "DevTools",
        "tags": ["test", "mock"],
        "platform": "claude",
        "content": "Skill content here",
    }


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "skillhub"


class TestListSkillsEndpoint:
    """Tests for GET /api/v1/skills/"""

    def test_list_skills_empty(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/")
            assert response.status_code == 200
            data = response.json()
            assert "skills" in data
            assert "total" in data
            assert "skip" in data
            assert "limit" in data
            assert data["total"] == 0

    def test_list_skills_with_pagination(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/?skip=10&limit=50")
            assert response.status_code == 200
            data = response.json()
            assert data["skip"] == 10
            assert data["limit"] == 50

    def test_list_skills_with_category_filter(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/?category=DevTools")
            assert response.status_code == 200
            mock_repo.list.assert_called_once()
            call_kwargs = mock_repo.list.call_args[1]
            assert call_kwargs["category"] == "DevTools"

    def test_list_skills_with_platform_filter(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/?platform=claude")
            assert response.status_code == 200
            call_kwargs = mock_repo.list.call_args[1]
            assert call_kwargs["platform"] == "claude"

    def test_list_skills_with_tags_filter(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/?tags=test,debug")
            assert response.status_code == 200
            call_kwargs = mock_repo.list.call_args[1]
            assert call_kwargs["tags"] == ["test", "debug"]

    def test_list_skills_limit_validation(self, client):
        response = client.get("/api/v1/skills/?limit=200")
        assert response.status_code == 422

    def test_list_skills_negative_skip_validation(self, client):
        response = client.get("/api/v1/skills/?skip=-1")
        assert response.status_code == 422


class TestGetSkillEndpoint:
    """Tests for GET /api/v1/skills/{skill_id}"""

    def test_get_skill_found(self, client, mock_skill):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = mock_skill
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/test/skill:v1.0.0")
            assert response.status_code == 200
            data = response.json()
            assert data["skill_id"] == "test/skill:v1.0.0"
            assert data["name"] == "Test Skill"

    def test_get_skill_not_found(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/nonexistent")
            assert response.status_code == 404

    def test_get_skill_nested_path(self, client, mock_skill):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = mock_skill
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/owner/repo/skill-name")
            assert response.status_code == 200


class TestCreateSkillEndpoint:
    """Tests for POST /api/v1/skills/"""

    def test_create_skill_success(self, client, mock_skill_dict):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            with patch("src.api.routes.skills.SecurityService") as mock_security_class:
                mock_repo = AsyncMock()
                mock_repo.get_by_skill_id.return_value = None

                mock_skill = MagicMock()
                mock_skill.id = uuid.uuid4()
                mock_skill.skill_id = mock_skill_dict["skill_id"]
                mock_skill.name = mock_skill_dict["name"]
                mock_skill.description = mock_skill_dict["description"]
                mock_skill.version = mock_skill_dict["version"]
                mock_skill.commit_id = mock_skill_dict["commit_id"]
                mock_skill.author = mock_skill_dict["author"]
                mock_skill.source = mock_skill_dict["source"]
                mock_skill.source_url = mock_skill_dict["source_url"]
                mock_skill.category = mock_skill_dict["category"]
                mock_skill.tags = mock_skill_dict["tags"]
                mock_skill.platform = mock_skill_dict["platform"]
                mock_skill.extra_metadata = {}
                mock_skill.content = mock_skill_dict["content"]
                mock_skill.security_score = None
                mock_skill.download_count = 0
                mock_skill.rating = None
                mock_skill.created_at = datetime.now(timezone.utc)
                mock_skill.updated_at = datetime.now(timezone.utc)
                mock_skill.last_indexed_at = None

                mock_repo.create.return_value = mock_skill
                mock_repo_class.return_value = mock_repo

                mock_security = MagicMock()
                mock_security.detector.enable_audit = False
                mock_security_class.return_value = mock_security

                response = client.post("/api/v1/skills/", json=mock_skill_dict)
                assert response.status_code == 201
                data = response.json()
                assert data["skill_id"] == mock_skill_dict["skill_id"]

    def test_create_skill_already_exists(self, client, mock_skill_dict):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = MagicMock()
            mock_repo_class.return_value = mock_repo

            response = client.post("/api/v1/skills/", json=mock_skill_dict)
            assert response.status_code == 409

    def test_create_skill_missing_required_field(self, client):
        incomplete_data = {
            "name": "Test Skill",
            "source": "github",
        }
        response = client.post("/api/v1/skills/", json=incomplete_data)
        assert response.status_code == 422

    def test_create_skill_invalid_source(self, client):
        invalid_data = {
            "skill_id": "test/skill",
            "name": "Test",
            "source": "invalid_source",
            "source_url": "https://example.com",
        }
        response = client.post("/api/v1/skills/", json=invalid_data)
        assert response.status_code == 422


class TestDeleteSkillEndpoint:
    """Tests for DELETE /api/v1/skills/{skill_id}"""

    def test_delete_skill_success(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.delete.return_value = True
            mock_repo_class.return_value = mock_repo

            response = client.delete("/api/v1/skills/test/skill")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Skill deleted"
            assert data["skill_id"] == "test/skill"

    def test_delete_skill_not_found(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.delete.return_value = False
            mock_repo_class.return_value = mock_repo

            response = client.delete("/api/v1/skills/nonexistent")
            assert response.status_code == 404


class TestDownloadSkillEndpoint:
    """Tests for GET /api/v1/skills/{skill_id}/download"""

    def test_download_skill_success(self, client, mock_skill):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            with patch("src.api.routes.skills.DownloadManager") as mock_dm_class:
                with patch("src.api.routes.skills.DownloadHistoryRepository") as mock_dl_repo_class:
                    mock_repo = AsyncMock()
                    mock_repo.get_by_skill_id.return_value = mock_skill
                    mock_repo.increment_download = AsyncMock()
                    mock_repo_class.return_value = mock_repo

                    mock_dm = MagicMock()
                    mock_dm.get_download_url = AsyncMock(
                        return_value="https://github.com/test/skill/archive/refs/heads/main.zip"
                    )
                    mock_dm_class.return_value = mock_dm

                    mock_dl_repo = AsyncMock()
                    mock_dl_repo.create = AsyncMock()
                    mock_dl_repo_class.return_value = mock_dl_repo

                    response = client.get("/api/v1/skills/test/skill:v1.0.0/download")
                    assert response.status_code == 200
                    data = response.json()
                    assert "download_url" in data

    def test_download_skill_not_found(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/nonexistent/download")
            assert response.status_code == 404


class TestSkillAuditEndpoint:
    """Tests for GET /api/v1/skills/{skill_id}/audit"""

    def test_audit_skill_found(self, client, mock_skill):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            with patch("src.api.routes.skills.SecurityService") as mock_security_class:
                mock_repo = AsyncMock()
                mock_repo.get_by_skill_id.return_value = mock_skill
                mock_repo_class.return_value = mock_repo

                mock_audit = MagicMock()
                mock_audit.id = uuid.uuid4()
                mock_audit.resource_type = "skill"
                mock_audit.resource_id = mock_skill.id
                mock_audit.audit_type = "socket.dev"
                mock_audit.risk_level = "low"
                mock_audit.risk_signals = []
                mock_audit.details = {}
                mock_audit.audited_at = datetime.now(timezone.utc)

                mock_audit_repo = MagicMock()
                mock_audit_repo.get_latest_by_resource = AsyncMock(return_value=mock_audit)

                mock_security = MagicMock()
                mock_security.audit_repo = mock_audit_repo
                mock_security_class.return_value = mock_security

                response = client.get(f"/api/v1/skills/{mock_skill.skill_id}/audit")
                assert response.status_code == 200
                data = response.json()
                assert data["resource_type"] == "skill"

    def test_audit_skill_not_found(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_skill_id.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/nonexistent/audit")
            assert response.status_code == 404

    def test_audit_skill_no_audit_record(self, client, mock_skill):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            with patch("src.api.routes.skills.SecurityService") as mock_security_class:
                mock_repo = AsyncMock()
                mock_repo.get_by_skill_id.return_value = mock_skill
                mock_repo_class.return_value = mock_repo

                mock_audit_repo = MagicMock()
                mock_audit_repo.get_latest_by_resource = AsyncMock(return_value=None)

                mock_security = MagicMock()
                mock_security.audit_repo = mock_audit_repo
                mock_security_class.return_value = mock_security

                response = client.get(f"/api/v1/skills/{mock_skill.skill_id}/audit")
                assert response.status_code == 200
                data = response.json()
                assert "error" in data


class TestSkillVersionsEndpoint:
    """Tests for GET /api/v1/skills/{repo}/{skill_name}/versions"""

    def test_get_versions_found(self, client, mock_skill):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_repo_and_name.return_value = [mock_skill]
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/versions/test/skill-name")
            assert response.status_code == 200
            data = response.json()
            assert "versions" in data
            assert "source_url" in data
            assert "skill_name" in data

    def test_get_versions_not_found(self, client):
        with patch("src.api.routes.skills.SkillRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_repo_and_name.return_value = []
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/skills/versions/nonexistent/skill")
            assert response.status_code == 404
