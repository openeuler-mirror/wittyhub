"""
Comprehensive tests for Agents API endpoints
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.models import Agent


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_agent():
    """Create a mock agent object"""
    agent = MagicMock(spec=Agent)
    agent.id = uuid.uuid4()
    agent.agent_id = "test/agent:v1.0.0"
    agent.name = "Test Agent"
    agent.description = "A test agent description"
    agent.version = "v1.0.0"
    agent.commit_id = "def456"
    agent.author = "test_author"
    agent.source = "github"
    agent.source_url = "https://github.com/test/agent"
    agent.category = "AI"
    agent.tags = ["test", "ai"]
    agent.extra_metadata = {}
    agent.security_score = 90
    agent.download_count = 50
    agent.rating = "4.3"
    agent.created_at = datetime.now(timezone.utc)
    agent.updated_at = datetime.now(timezone.utc)
    agent.last_indexed_at = None
    agent.logo_url = None
    agent.homepage_url = None
    agent.license = "MIT"
    agent.readme_content = "# Test Agent README"
    agent.agent_yaml_content = "name: test-agent\nversion: 1.0.0"
    agent.parsed_config = {
        "prompt": {"system": "You are a helpful assistant", "identity": {"role": "Assistant"}},
        "tools": {"allowed": ["read", "bash"]},
        "skills": [],
        "subagents": []
    }
    agent.supported_platforms = ["claude-code", "opencode"]
    agent.verified = False
    agent.star_count = 10
    agent.contributor_count = 2
    agent.latest_commit_id = "abc123"
    return agent


class TestListAgentsEndpoint:
    """Tests for GET /api/v1/agents/"""

    def test_list_agents_empty(self, client):
        with patch("src.api.routes.agents.AgentRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/agents/")
            assert response.status_code == 200
            data = response.json()
            assert "agents" in data
            assert "total" in data
            assert data["total"] == 0

    def test_list_agents_with_pagination(self, client):
        with patch("src.api.routes.agents.AgentRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/agents/?skip=10&limit=50")
            assert response.status_code == 200
            data = response.json()
            assert data["skip"] == 10
            assert data["limit"] == 50

    def test_list_agents_with_category_filter(self, client):
        with patch("src.api.routes.agents.AgentRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.list.return_value = ([], 0)
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/agents/?category=AI")
            assert response.status_code == 200
            call_kwargs = mock_repo.list.call_args[1]
            assert call_kwargs["category"] == "AI"

    def test_list_agents_limit_validation(self, client):
        response = client.get("/api/v1/agents/?limit=200")
        assert response.status_code == 422


class TestGetAgentEndpoint:
    """Tests for GET /api/v1/agents/{agent_id}"""

    def test_get_agent_found(self, client, mock_agent):
        with patch("src.api.routes.agents.AgentRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_agent_id.return_value = mock_agent
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/agents/test/agent:v1.0.0")
            assert response.status_code == 200
            data = response.json()
            assert data["agent_id"] == "test/agent:v1.0.0"
            assert data["name"] == "Test Agent"

    def test_get_agent_not_found(self, client):
        with patch("src.api.routes.agents.AgentRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get_by_agent_id.return_value = None
            mock_repo_class.return_value = mock_repo

            response = client.get("/api/v1/agents/nonexistent")
            assert response.status_code == 404
