from unittest.mock import AsyncMock

import pytest

from src.ai import embedding as embedding_module
from src.ai.embedding import (
    BGE_QUERY_INSTRUCTION,
    MAX_EMBEDDING_TEXT_CHARS,
    prepare_search_query,
    prepare_skill_text,
)


def test_prepare_search_query_adds_bge_instruction():
    assert prepare_search_query("  安全审计  ") == (
        f"{BGE_QUERY_INSTRUCTION}安全审计"
    )


def test_prepare_skill_text_truncates_oversized_content():
    """超长 content 截断到上限：几十万字符长文不再整体发给 embedding 服务。"""
    skill = {
        "name": "torch-npugraph",
        "description": "诊断工具",
        "content": "长文" * 200_000,
    }
    text = prepare_skill_text(skill)
    assert len(text) == MAX_EMBEDDING_TEXT_CHARS
    assert text.startswith("torch-npugraph 诊断工具")


@pytest.mark.asyncio
async def test_query_embedding_cache_avoids_duplicate_model_requests(monkeypatch):
    embedding_module._query_embedding_cache.clear()
    generate = AsyncMock(return_value=[[0.1, 0.2]])
    monkeypatch.setattr(embedding_module, "generate_embeddings", generate)

    first = await embedding_module.generate_query_embedding(" 日志分析 ")
    second = await embedding_module.generate_query_embedding("日志分析")

    assert first == second == [0.1, 0.2]
    generate.assert_awaited_once_with([f"{BGE_QUERY_INSTRUCTION}日志分析"])
