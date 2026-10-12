from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.ai import translation


def test_contains_chinese():
    assert translation.contains_chinese("日志分析")
    assert not translation.contains_chinese("log analysis")


@pytest.mark.asyncio
async def test_translate_query_uses_openai_compatible_response():
    translation._cache.clear()
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "choices": [{"message": {"content": "log analysis"}}]
    }
    settings = MagicMock()
    settings.model.base_url = "http://model"
    settings.model.api_key = "token"
    settings.model.name = "translator"
    settings.model.timeout = 5
    with (
        patch.object(translation, "get_settings", return_value=settings),
        patch.object(translation, "_get_client") as get_client,
    ):
        get_client.return_value.post = AsyncMock(return_value=response)
        assert await translation.translate_query_to_english(" 日志分析 ") == "log analysis"
        assert await translation.translate_query_to_english("日志分析") == "log analysis"
        assert get_client.return_value.post.await_count == 1


@pytest.mark.asyncio
async def test_translate_query_failure_degrades_to_none():
    settings = MagicMock()
    settings.model.base_url = "http://model"
    settings.model.api_key = "token"
    settings.model.timeout = 5
    with (
        patch.object(translation, "get_settings", return_value=settings),
        patch.object(translation, "_get_client") as get_client,
    ):
        get_client.return_value.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        assert await translation.translate_query_to_english("分析日志") is None
