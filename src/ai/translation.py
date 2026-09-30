"""Optional query translation for cross-language skill retrieval."""

import re
from collections import OrderedDict
import time

import httpx

from src.core.config import get_settings

TRANSLATION_CACHE_TTL_SECONDS = 600.0
TRANSLATION_CACHE_MAX_ENTRIES = 256
_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
_client: httpx.AsyncClient | None = None


def contains_chinese(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text))


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def translate_query_to_english(query: str) -> str | None:
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
    payload = {
        "model": settings.model.name,
        "temperature": 0,
        "max_tokens": 128,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Translate the user's Chinese search query into concise English. "
                    "Return only the translation, with no explanation."
                ),
            },
            {"role": "user", "content": normalized},
        ],
    }
    try:
        response = await _get_client().post(
            f"{settings.model.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.model.api_key}"},
            json=payload,
            timeout=settings.model.timeout,
        )
        response.raise_for_status()
        translated = response.json()["choices"][0]["message"]["content"].strip()
        if not translated or len(translated) > 500:
            return None
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return None

    _cache[normalized] = (now, translated)
    _cache.move_to_end(normalized)
    while len(_cache) > TRANSLATION_CACHE_MAX_ENTRIES:
        _cache.popitem(last=False)
    return translated


async def close_translation_service() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
