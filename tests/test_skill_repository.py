import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


class TestSkillRepositoryUnit:
    async def test_create_skill_data_validation(self):
        from src.api.schemas.skill import SkillCreate

        skill_data = {
            "skill_id": "test/skill:v1.0.0",
            "name": "test-skill",
            "description": "Test skill",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "test",
            "source": "clawhub",
            "source_url": "https://example.com/test",
            "category": "Testing",
            "tags": ["test"],
            "platform": "openclaw",
        }
        skill = SkillCreate(**skill_data)
        assert skill.skill_id == "test/skill:v1.0.0"
        assert skill.name == "test-skill"

    async def test_skill_create_missing_required_fields(self):
        from src.api.schemas.skill import SkillCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SkillCreate(
                name="test",
                source="clawhub",
                source_url="https://example.com",
            )

    async def test_skill_response_model(self):
        from src.api.schemas.skill import SkillResponse

        skill_dict = {
            "id": str(uuid.uuid4()),
            "skill_id": "test/skill:v1.0.0",
            "name": "test-skill",
            "description": "Test skill",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "test",
            "source": "clawhub",
            "source_url": "https://example.com/test",
            "category": "Testing",
            "tags": ["test"],
            "platform": "openclaw",
            "metadata": {},
            "security_score": 85,
            "download_count": 10,
            "rating": "4.5",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = SkillResponse(**skill_dict)
        assert response.skill_id == "test/skill:v1.0.0"
        assert response.name == "test-skill"


class TestSearchClient:
    async def test_search_client_initialization(self):
        from src.indexer.search import SearchClient

        with patch("src.indexer.search.meilisearch.Client") as mock_client:
            mock_client.return_value.index.return_value.search.return_value = {
                "hits": [],
                "estimatedTotalHits": 0,
            }
            client = SearchClient()
            assert client is not None

    async def test_search_skills_returns_results(self):
        from src.indexer.search import SearchClient

        with patch("src.indexer.search.meilisearch.Client") as mock_client:
            mock_index = MagicMock()
            mock_index.search.return_value = {
                "hits": [
                    {"name": "test-skill", "skill_id": "test/skill:v1.0.0"}
                ],
                "estimatedTotalHits": 1,
            }
            mock_client.return_value.index.return_value = mock_index

            client = SearchClient()
            results = client.search_skills(query="test", limit=10)
            assert len(results["hits"]) == 1
            assert results["hits"][0]["name"] == "test-skill"

    async def test_index_skills_adds_documents(self):
        from src.indexer.search import SearchClient

        with patch("src.indexer.search.meilisearch.Client") as mock_client:
            mock_index = MagicMock()
            mock_index.add_documents.return_value = {"taskUid": 1}
            mock_client.return_value.index.return_value = mock_index

            client = SearchClient()
            skills_data = [
                {"id": "1", "name": "skill1", "skill_id": "test/skill1:v1.0.0"}
            ]
            result = client.index_skills(skills_data)
            assert result is not None
            mock_index.add_documents.assert_called_once()


class TestConfig:
    async def test_get_settings(self):
        from src.core.config import get_settings

        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/skillhub",
                "MEILISEARCH_HOST": "http://localhost:7700",
                "MEILISEARCH_API_KEY": "test_key",
            },
        ):
            settings = get_settings()
            assert settings is not None
            assert "postgresql" in settings.database.url


class TestAPIRoutes:
    async def test_health_endpoint(self):
        from src.api.routes.health import router

        assert router is not None
        routes = [route.path for route in router.routes]
        assert "/health" in routes


class TestSkillSchema:
    async def test_skill_id_format(self):
        from src.api.schemas.skill import SkillResponse

        skill_data = {
            "id": str(uuid.uuid4()),
            "skill_id": "author/skill-name:v1.0.0",
            "name": "skill-name",
            "description": "Test",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "author",
            "source": "clawhub",
            "source_url": "https://example.com",
            "category": "Testing",
            "tags": ["test"],
            "platform": "openclaw",
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = SkillResponse(**skill_data)
        assert ":" in response.skill_id
        assert response.skill_id.startswith("author/")

    async def test_source_validation(self):
        from src.api.schemas.skill import SkillResponse

        valid_sources = ["local", "github", "clawhub", "gitcode", "gitlab"]
        for source in valid_sources:
            skill_data = {
                "id": str(uuid.uuid4()),
                "skill_id": f"test/skill:v1.0.0",
                "name": "skill",
                "description": "Test",
                "version": "v1.0.0",
                "commit_id": "abc123",
                "author": "test",
                "source": source,
                "source_url": "https://example.com",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            response = SkillResponse(**skill_data)
            assert response.source == source