import os
from abc import ABC, abstractmethod
from typing import Any

import httpx
import yaml
from pydantic import BaseModel, Field


class AIConfig(BaseModel):
    embedding_model: str = "bge-base-zh-v1.5"
    embedding_host: str = "http://localhost:8081"
    embedding_dimension: int = 768
    enable_semantic_search: bool = True


class Settings(BaseModel):
    ai: AIConfig = Field(default_factory=AIConfig)


def load_settings() -> Settings:
    config_path = os.environ.get("SKILLHUB_CONFIG", "config.yaml")
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return Settings(ai=AIConfig(**data.get("ai", {})))
    except Exception:
        return Settings()


class EmbeddingProvider(ABC):
    @abstractmethod
    async def encode(self, texts: list[str]) -> list[list[float]]:
        pass

    @abstractmethod
    def dimension(self) -> int:
        pass


class LocalEmbeddingService(EmbeddingProvider):
    def __init__(self, host: str, model: str, dimension: int):
        self.host = host
        self.model = model
        self._dimension = dimension

    async def encode(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.host}/v1/embeddings",
                json={"input": texts, "model": self.model},
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    def dimension(self) -> int:
        return self._dimension


class MockEmbeddingService(EmbeddingProvider):
    """Mock embedding service for testing without actual model."""

    def __init__(self, dimension: int = 768):
        self._dimension = dimension

    async def encode(self, texts: list[str]) -> list[list[float]]:
        import random

        return [
            [random.random() for _ in range(self._dimension)]
            for _ in texts
        ]

    def dimension(self) -> int:
        return self._dimension


_embedding_service: EmbeddingProvider | None = None


def get_embedding_service() -> EmbeddingProvider:
    global _embedding_service
    if _embedding_service is None:
        settings = load_settings()
        if settings.ai.enable_semantic_search:
            _embedding_service = LocalEmbeddingService(
                host=settings.ai.embedding_host,
                model=settings.ai.embedding_model,
                dimension=settings.ai.embedding_dimension,
            )
        else:
            _embedding_service = MockEmbeddingService()
    return _embedding_service


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    service = get_embedding_service()
    return await service.encode(texts)


def prepare_skill_text(skill: dict[str, Any] | Any) -> str:
    """
    组合 skill 的 name、description、content 生成用于 embedding 的文本
    """
    parts = []
    if hasattr(skill, "name"):
        parts.append(skill.name)
        if skill.description:
            parts.append(skill.description)
        if skill.content:
            parts.append(skill.content)
    else:
        if skill.get("name"):
            parts.append(skill["name"])
        if skill.get("description"):
            parts.append(skill["description"])
        if skill.get("content"):
            parts.append(skill["content"])
    return " ".join(parts)


async def generate_skill_embedding(skill: dict[str, Any] | Any) -> list[float] | None:
    """
    为单个 skill 生成 embedding
    """
    try:
        text = prepare_skill_text(skill)
        if not text.strip():
            return None
        embeddings = await generate_embeddings([text])
        return embeddings[0] if embeddings else None
    except Exception:
        return None
