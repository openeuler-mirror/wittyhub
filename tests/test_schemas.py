"""
Comprehensive tests for schemas and models
"""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.api.schemas.skill import (
    SkillBase,
    SkillCreate,
    SkillUpdate,
    SkillResponse,
    SkillListResponse,
    SkillVersionsResponse,
    SecurityAuditResponse,
    DownloadResponse,
    ErrorResponse,
    RiskSignalSchema,
)


class TestSkillBase:
    """Tests for SkillBase schema"""

    def test_valid_skill_base(self):
        data = {
            "skill_id": "test/skill:v1.0.0",
            "name": "Test Skill",
            "description": "A test skill",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "test_author",
            "source": "github",
            "source_url": "https://github.com/test/skill",
            "category": "DevTools",
            "tags": ["test", "mock"],
            "platform": "claude",
            "content": "Skill content",
            "metadata": {"key": "value"},
        }
        skill = SkillBase(**data)
        assert skill.skill_id == "test/skill:v1.0.0"
        assert skill.name == "Test Skill"
        assert skill.tags == ["test", "mock"]

    def test_skill_base_optional_fields(self):
        data = {
            "skill_id": "test/skill",
            "name": "Test",
            "source": "github",
            "source_url": "https://github.com/test",
        }
        skill = SkillBase(**data)
        assert skill.description is None
        assert skill.tags is None
        assert skill.content is None

    def test_invalid_source(self):
        data = {
            "skill_id": "test/skill",
            "name": "Test",
            "source": "invalid_source",
            "source_url": "https://example.com",
        }
        with pytest.raises(ValidationError) as exc_info:
            SkillBase(**data)
        assert "source must be one of" in str(exc_info.value)

    def test_source_github_valid(self):
        for source in ["github", "gitcode", "gitlab", "local", "clawhub"]:
            data = {
                "skill_id": "test/skill",
                "name": "Test",
                "source": source,
                "source_url": "https://example.com",
            }
            skill = SkillBase(**data)
            assert skill.source == source

    def test_empty_skill_id_invalid(self):
        data = {
            "skill_id": "",
            "name": "Test",
            "source": "github",
            "source_url": "https://example.com",
        }
        with pytest.raises(ValidationError):
            SkillBase(**data)

    def test_empty_name_invalid(self):
        data = {
            "skill_id": "test/skill",
            "name": "",
            "source": "github",
            "source_url": "https://example.com",
        }
        with pytest.raises(ValidationError):
            SkillBase(**data)


class TestSkillCreate:
    """Tests for SkillCreate schema"""

    def test_skill_create_valid(self):
        data = {
            "skill_id": "test/skill:v1.0.0",
            "name": "Test Skill",
            "source": "github",
            "source_url": "https://github.com/test/skill",
        }
        skill = SkillCreate(**data)
        assert skill.skill_id == "test/skill:v1.0.0"
        assert skill.name == "Test Skill"

    def test_skill_create_all_fields(self):
        data = {
            "skill_id": "test/skill:v1.0.0",
            "name": "Test Skill",
            "description": "Description",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "author",
            "source": "github",
            "source_url": "https://github.com/test/skill",
            "category": "DevTools",
            "tags": ["test"],
            "platform": "claude",
            "content": "Content",
            "metadata": {"key": "value"},
        }
        skill = SkillCreate(**data)
        assert skill.metadata == {"key": "value"}
        assert skill.tags == ["test"]


class TestSkillUpdate:
    """Tests for SkillUpdate schema"""

    def test_skill_update_partial(self):
        data = {"name": "Updated Name"}
        update = SkillUpdate(**data)
        assert update.name == "Updated Name"
        assert update.description is None

    def test_skill_update_all_optional(self):
        update = SkillUpdate()
        assert update.name is None
        assert update.description is None


class TestSkillResponse:
    """Tests for SkillResponse schema"""

    def test_skill_response_valid(self):
        data = {
            "id": str(uuid.uuid4()),
            "skill_id": "test/skill:v1.0.0",
            "name": "Test Skill",
            "source": "github",
            "source_url": "https://github.com/test",
            "security_score": 95,
            "download_count": 100,
            "rating": "4.5",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        response = SkillResponse(**data)
        assert response.security_score == 95
        assert response.download_count == 100


class TestSkillListResponse:
    """Tests for SkillListResponse schema"""

    def test_skill_list_response(self):
        data = {
            "skills": [],
            "total": 0,
            "skip": 0,
            "limit": 20,
        }
        response = SkillListResponse(**data)
        assert response.total == 0


class TestSkillVersionsResponse:
    """Tests for SkillVersionsResponse schema"""

    def test_skill_versions_response(self):
        skill_data = {
            "id": str(uuid.uuid4()),
            "skill_id": "test/skill:v1.0.0",
            "name": "Test Skill",
            "source": "github",
            "source_url": "https://github.com/test",
            "security_score": 95,
            "download_count": 100,
            "rating": "4.5",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        data = {
            "source_url": "https://github.com/test/skill",
            "skill_name": "skill",
            "versions": [SkillResponse(**skill_data)],
        }
        response = SkillVersionsResponse(**data)
        assert len(response.versions) == 1


class TestSecurityAuditResponse:
    """Tests for SecurityAuditResponse schema"""

    def test_security_audit_response_valid(self):
        data = {
            "id": str(uuid.uuid4()),
            "resource_type": "skill",
            "resource_id": str(uuid.uuid4()),
            "audit_type": "socket.dev",
            "risk_level": "low",
            "risk_signals": [],
            "details": {},
            "audited_at": datetime.now(timezone.utc),
        }
        response = SecurityAuditResponse(**data)
        assert response.risk_level == "low"
        assert response.audit_type == "socket.dev"


class TestDownloadResponse:
    """Tests for DownloadResponse schema"""

    def test_download_response_valid(self):
        data = {
            "download_url": "https://github.com/test/skill/archive.zip",
            "file_path": None,
            "security_audit": None,
        }
        response = DownloadResponse(**data)
        assert response.download_url == "https://github.com/test/skill/archive.zip"


class TestErrorResponse:
    """Tests for ErrorResponse schema"""

    def test_error_response(self):
        data = {"error": "Not found", "detail": "Skill does not exist"}
        response = ErrorResponse(**data)
        assert response.error == "Not found"
        assert response.detail == "Skill does not exist"


class TestRiskSignalSchema:
    """Tests for RiskSignalSchema"""

    def test_risk_signal_valid(self):
        data = {
            "id": "signal_1",
            "name": "API Key Detection",
            "description": "Found potential API key",
            "severity": "high",
            "data": {"key": "value"},
        }
        signal = RiskSignalSchema(**data)
        assert signal.severity == "high"
        assert signal.data == {"key": "value"}
