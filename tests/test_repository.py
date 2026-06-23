"""
Comprehensive tests for repository layer
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.models.repository import (
    SkillRepository,
    AgentRepository,
    SecurityAuditRepository,
    DownloadHistoryRepository,
)


class TestSkillRepository:
    """Tests for SkillRepository"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.scalar = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return SkillRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        skill_data = {
            "skill_id": "test/skill:v1.0.0",
            "name": "Test Skill",
            "source": "github",
        }
        mock_session.refresh = AsyncMock()

        result = await repository.create(skill_data)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_skill_id_found(self, repository, mock_session):
        mock_skill = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_skill_id("test/skill:v1.0.0")

        assert result == mock_skill
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_skill_id_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_skill_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_versions_by_base_skill(self, repository, mock_session):
        mock_skills = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_versions_by_base_skill(
            source_url="https://github.com/test",
            skill_name="skill"
        )

        assert len(result) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_repo_and_name(self, repository, mock_session):
        mock_skills = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_repo_and_name("test", "skill")

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_session):
        test_id = uuid.uuid4()
        mock_skill = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(test_id)

        assert result == mock_skill

    @pytest.mark.asyncio
    async def test_list_no_filters(self, repository, mock_session):
        mock_skills = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 2

        result = await repository.list()

        skills, total = result
        assert len(skills) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_with_category(self, repository, mock_session):
        mock_skills = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        result = await repository.list(category="DevTools")

        skills, total = result
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_list_with_platform(self, repository, mock_session):
        mock_skills = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        result = await repository.list(platform="claude")

        skills, total = result
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_list_with_tags(self, repository, mock_session):
        mock_skills = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        result = await repository.list(tags=["test"])

        skills, total = result
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, repository, mock_session):
        mock_skills = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_skills
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        result = await repository.list(skip=10, limit=5)

        skills, total = result
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_update(self, repository, mock_session):
        mock_skill = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute.return_value = mock_result

        result = await repository.update("test/skill:v1.0.0", {"name": "Updated"})

        assert result == mock_skill
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_delete_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete("test/skill:v1.0.0")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_increment_download(self, repository, mock_session):
        await repository.increment_download("test/skill:v1.0.0")

        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_update_last_indexed(self, repository, mock_session):
        await repository.update_last_indexed("test/skill:v1.0.0")

        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_update_embedding(self, repository, mock_session):
        embedding = [0.1, 0.2, 0.3]
        await repository.update_embedding("test/skill:v1.0.0", embedding)

        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_get_stats(self, repository, mock_session):
        results = [
            MagicMock(scalar=MagicMock(return_value=10)),
            MagicMock(fetchall=MagicMock(return_value=[
                ("DevTools", 5),
                ("AI", 3),
                (None, 2),
            ])),
        ]
        mock_session.execute = AsyncMock(side_effect=results)

        result = await repository.get_stats()

        assert result["total_skills"] == 10
        assert result["total_categories"] == 3
        assert len(result["categories"]) == 3


class TestAgentRepository:
    """Tests for AgentRepository"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.scalar = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return AgentRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        agent_data = {
            "agent_id": "test/agent:v1.0.0",
            "name": "Test Agent",
            "source": "github",
        }
        mock_session.refresh = AsyncMock()

        result = await repository.create(agent_data)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_agent_id_found(self, repository, mock_session):
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_agent_id("test/agent:v1.0.0")

        assert result == mock_agent

    @pytest.mark.asyncio
    async def test_get_by_agent_id_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_agent_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, mock_session):
        test_id = uuid.uuid4()
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(test_id)

        assert result == mock_agent

    @pytest.mark.asyncio
    async def test_list_no_filters(self, repository, mock_session):
        mock_agents = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_agents
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 2

        result = await repository.list()

        agents, total = result
        assert len(agents) == 2
        assert total == 2

    @pytest.mark.asyncio
    async def test_list_with_category(self, repository, mock_session):
        mock_agents = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_agents
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        result = await repository.list(category="AI")

        agents, total = result
        assert len(agents) == 1

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, repository, mock_session):
        mock_agents = [MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_agents
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        result = await repository.list(skip=5, limit=10)

        agents, total = result
        assert len(agents) == 1

    @pytest.mark.asyncio
    async def test_delete_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete("test/agent:v1.0.0")

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete("nonexistent")

        assert result is False


class TestSecurityAuditRepository:
    """Tests for SecurityAuditRepository"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return SecurityAuditRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        audit_data = {
            "resource_type": "skill",
            "resource_id": uuid.uuid4(),
            "audit_type": "socket.dev",
            "risk_level": "low",
        }
        mock_session.refresh = AsyncMock()

        result = await repository.create(audit_data)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_by_resource_found(self, repository, mock_session):
        mock_audit = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_audit
        mock_session.execute.return_value = mock_result

        resource_id = uuid.uuid4()
        result = await repository.get_latest_by_resource("skill", resource_id)

        assert result == mock_audit

    @pytest.mark.asyncio
    async def test_get_latest_by_resource_not_found(self, repository, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        resource_id = uuid.uuid4()
        result = await repository.get_latest_by_resource("skill", resource_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_list_by_resource(self, repository, mock_session):
        mock_audits = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_audits
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        resource_id = uuid.uuid4()
        result = await repository.list_by_resource("skill", resource_id)

        assert len(result) == 2


class TestDownloadHistoryRepository:
    """Tests for DownloadHistoryRepository"""

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        return DownloadHistoryRepository(mock_session)

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        download_data = {
            "resource_type": "skill",
            "resource_id": uuid.uuid4(),
            "ip_address": "127.0.0.1",
        }
        mock_session.refresh = AsyncMock()

        result = await repository.create(download_data)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()
