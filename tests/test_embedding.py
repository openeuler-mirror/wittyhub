"""
Comprehensive tests for embedding service
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.embedding import (
    AIConfig,
    Settings,
    EmbeddingProvider,
    LocalEmbeddingService,
    MockEmbeddingService,
    get_embedding_service,
    generate_embeddings,
    prepare_skill_text,
    generate_skill_embedding,
)


class TestAIConfig:
    """Tests for AIConfig"""

    def test_default_config(self):
        config = AIConfig()
        assert config.embedding_model == "bge-base-zh-v1.5"
        assert config.embedding_host == "http://localhost:8081"
        assert config.embedding_dimension == 768
        assert config.enable_semantic_search is True

    def test_custom_config(self):
        config = AIConfig(
            embedding_model="bge-large",
            embedding_host="http://custom:8080",
            embedding_dimension=1024,
            enable_semantic_search=False,
        )
        assert config.embedding_model == "bge-large"
        assert config.embedding_dimension == 1024
        assert config.enable_semantic_search is False


class TestSettings:
    """Tests for Settings"""

    def test_settings_with_ai_config(self):
        settings = Settings(
            ai=AIConfig(embedding_model="custom-model")
        )
        assert settings.ai.embedding_model == "custom-model"


class TestMockEmbeddingService:
    """Tests for MockEmbeddingService"""

    @pytest.mark.asyncio
    async def test_mock_encode(self):
        service = MockEmbeddingService(dimension=3)
        result = await service.encode(["test text"])
        assert len(result) == 1
        assert len(result[0]) == 3

    @pytest.mark.asyncio
    async def test_mock_encode_multiple(self):
        service = MockEmbeddingService(dimension=4)
        result = await service.encode(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 4
        assert len(result[1]) == 4

    def test_mock_dimension(self):
        service = MockEmbeddingService(dimension=256)
        assert service.dimension() == 256


class TestLocalEmbeddingService:
    """Tests for LocalEmbeddingService"""

    @pytest.mark.asyncio
    async def test_local_encode_success(self):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": [0.1, 0.2, 0.3]}
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            service = LocalEmbeddingService(
                host="http://localhost:8081",
                model="bge-base-zh-v1.5",
                dimension=3,
            )
            result = await service.encode(["test text"])
            assert len(result) == 1
            assert result[0] == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_local_encode_multiple(self):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            service = LocalEmbeddingService(
                host="http://localhost:8081",
                model="bge-base-zh-v1.5",
                dimension=2,
            )
            result = await service.encode(["text1", "text2"])
            assert len(result) == 2

    def test_local_dimension(self):
        service = LocalEmbeddingService(
            host="http://localhost:8081",
            model="bge-base-zh-v1.5",
            dimension=768,
        )
        assert service.dimension() == 768


class TestPrepareSkillText:
    """Tests for prepare_skill_text function"""

    def test_prepare_skill_text_with_object(self):
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.description = "Test description"
        mock_skill.content = "Test content"

        result = prepare_skill_text(mock_skill)
        assert result == "Test Skill Test description Test content"

    def test_prepare_skill_text_without_content(self):
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.description = "Test description"
        mock_skill.content = None

        result = prepare_skill_text(mock_skill)
        assert result == "Test Skill Test description"

    def test_prepare_skill_text_with_dict(self):
        skill_dict = {
            "name": "Test Skill",
            "description": "Test description",
            "content": "Test content",
        }

        result = prepare_skill_text(skill_dict)
        assert result == "Test Skill Test description Test content"

    def test_prepare_skill_text_empty_fields(self):
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.description = None
        mock_skill.content = None

        result = prepare_skill_text(mock_skill)
        assert result == "Test Skill"


class TestGenerateSkillEmbedding:
    """Tests for generate_skill_embedding function"""

    @pytest.mark.asyncio
    async def test_generate_skill_embedding_success(self):
        mock_skill = MagicMock()
        mock_skill.name = "Test Skill"
        mock_skill.description = "Test description"
        mock_skill.content = None

        with patch("src.ai.embedding.generate_embeddings") as mock_gen_emb:
            mock_gen_emb.return_value = [[0.1, 0.2, 0.3]]

            result = await generate_skill_embedding(mock_skill)
            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_generate_skill_embedding_empty_text(self):
        mock_skill = MagicMock()
        mock_skill.name = ""
        mock_skill.description = None
        mock_skill.content = None

        result = await generate_skill_embedding(mock_skill)
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_skill_embedding_error(self):
        mock_skill = MagicMock()
        mock_skill.name = "Test"
        mock_skill.description = None
        mock_skill.content = None

        with patch("src.ai.embedding.generate_embeddings") as mock_gen_emb:
            mock_gen_emb.side_effect = Exception("API error")

            result = await generate_skill_embedding(mock_skill)
            assert result is None


class TestGetEmbeddingService:
    """Tests for get_embedding_service function"""

    def test_get_embedding_service_cached(self):
        import src.ai.embedding as embedding_module

        embedding_module._embedding_service = None

        with patch("src.ai.embedding.load_settings") as mock_load:
            mock_load.return_value = Settings(
                ai=AIConfig(enable_semantic_search=False)
            )

            service1 = get_embedding_service()
            service2 = get_embedding_service()

            assert service1 is service2
            assert isinstance(service1, MockEmbeddingService)


class TestGenerateEmbeddings:
    """Tests for generate_embeddings function"""

    @pytest.mark.asyncio
    async def test_generate_embeddings(self):
        with patch("src.ai.embedding.get_embedding_service") as mock_get_service:
            mock_service = MockEmbeddingService(dimension=3)
            mock_get_service.return_value = mock_service

            result = await generate_embeddings(["test"])
            assert len(result) == 1
            assert len(result[0]) == 3
