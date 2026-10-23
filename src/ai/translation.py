"""Optional query translation for cross-language skill retrieval."""

import logging
import re
from collections import OrderedDict
import time

import httpx

from src.ai.llm import chat_completion, close_llm_service
from src.core.config import get_settings

_logger = logging.getLogger(__name__)

TRANSLATION_CACHE_TTL_SECONDS = 600.0
TRANSLATION_CACHE_MAX_ENTRIES = 256
_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


async def translate_query_to_english(
    query: str, timeout: float | None = None,
) -> str | None:
    normalized = query.strip()
    if not normalized or not contains_chinese(normalized):
        return None
    now = time.monotonic()
    cached = _cache.get(normalized)
    if cached and now - cached[0] < TRANSLATION_CACHE_TTL_SECONDS:
        _cache.move_to_end(normalized)
        return cached[1]
    if cached:
        _cache.pop(normalized, None)

    settings = get_settings()
    if not settings.model.base_url or not settings.model.api_key:
        return None

    messages = [
        {
            "role": "system",
            "content": (
                "Translate the user's Chinese search query into concise English. "
                "Return only the translation, with no explanation."
            ),
        },
        {"role": "user", "content": normalized},
    ]
    try:
        # 统一走 src.ai.llm：enable_thinking=False 等口径与 skill 分类一致
        translated = await chat_completion(messages, timeout=timeout)
        if not translated or len(translated) > 500:
            return None
    except httpx.TimeoutException:
        _logger.warning(
            "LLM 翻译超时 (timeout=%ss, provider=%s, model=%s, query=%r)",
            timeout or settings.model.timeout,
            settings.model.provider or "-",
            settings.model.name,
            normalized[:50],
        )
        return None
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        _logger.warning(
            "LLM 翻译失败 (provider=%s, model=%s, query=%r): %s",
            settings.model.provider or "-",
            settings.model.name,
            normalized[:50],
            exc,
        )
        return None

    _cache[normalized] = (now, translated)
    _cache.move_to_end(normalized)
    while len(_cache) > TRANSLATION_CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)
    return translated


async def close_translation_service() -> None:
    """关闭共享 LLM HTTP 客户端（与 skill 分类共用）。"""
    await close_llm_service()
