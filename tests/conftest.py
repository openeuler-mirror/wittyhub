"""
Pytest configuration and shared fixtures
"""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_session():
    """Mock AsyncSession for repository tests"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_skill():
    """Mock Skill object"""
    skill = MagicMock()
    skill.id = uuid.uuid4()
    skill.skill_id = "test/skill:v1.0.0"
    skill.name = "Test Skill"
    skill.description = "Test description"
    skill.version = "v1.0.0"
    skill.commit_id = "abc123"
    skill.author = "test_author"
    skill.source = "github"
    skill.source_url = "https://github.com/test/skill"
    skill.category = "DevTools"
    skill.tags = ["test", "mock"]
    skill.platform = "claude"
    skill.content = "Skill content"
    skill.metadata = {"key": "value"}
    skill.security_score = 95
    skill.download_count = 100
    skill.rating = "4.5"
    skill.created_at = datetime.now(timezone.utc)
    skill.updated_at = datetime.now(timezone.utc)
    skill.last_indexed_at = None
    skill.embedding = None
    return skill


@pytest.fixture
def mock_agent():
    """Mock Agent object"""
    agent = MagicMock()
    agent.id = uuid.uuid4()
    agent.agent_id = "test/agent:v1.0.0"
    agent.name = "Test Agent"
    agent.description = "Test agent description"
    agent.version = "v1.0.0"
    agent.commit_id = "def456"
    agent.author = "test_author"
    agent.source = "github"
    agent.source_url = "https://github.com/test/agent"
    agent.category = "AI"
    agent.tags = ["test", "ai"]
    agent.platform = "claude"
    agent.content = "Agent content"
    agent.metadata = {"key": "value"}
    agent.created_at = datetime.now(timezone.utc)
    agent.updated_at = datetime.now(timezone.utc)
    return agent


@pytest.fixture
def mock_security_audit():
    """Mock SecurityAudit object"""
    audit = MagicMock()
    audit.id = uuid.uuid4()
    audit.resource_type = "skill"
    audit.resource_id = uuid.uuid4()
    audit.audit_type = "socket.dev"
    audit.risk_level = "low"
    audit.risk_signals = []
    audit.details = {}
    audit.audited_at = datetime.now(timezone.utc)
    return audit


@pytest.fixture
def mock_download_history():
    """Mock DownloadHistory object"""
    history = MagicMock()
    history.id = uuid.uuid4()
    history.resource_type = "skill"
    history.resource_id = uuid.uuid4()
    history.source = "github"
    history.downloaded_at = datetime.now(timezone.utc)
    return history


@pytest.fixture
def sample_skill_data():
    """Sample skill creation data"""
    return {
        "skill_id": "test/skill:v1.0.0",
        "name": "Test Skill",
        "description": "Test description",
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


@pytest.fixture
def sample_agent_data():
    """Sample agent creation data"""
    return {
        "agent_id": "test/agent:v1.0.0",
        "name": "Test Agent",
        "description": "Test agent description",
        "version": "v1.0.0",
        "commit_id": "def456",
        "author": "test_author",
        "source": "github",
        "source_url": "https://github.com/test/agent",
        "category": "AI",
        "tags": ["test", "ai"],
        "platform": "claude",
        "content": "Agent content",
        "metadata": {"key": "value"},
    }
