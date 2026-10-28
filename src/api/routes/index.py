from typing import Annotated, Any

import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.embedding import generate_query_embedding
from src.ai.translation import translate_query_to_english
from src.core.config import get_settings
from src.core.database import get_db
from src.indexer.search import SearchService
from src.models.repository import SkillRepository

_logger = logging.getLogger(__name__)

router = APIRouter()

# 翻译是补充检索腿，超时即跳过：不为它拖慢主结果（部分 LLM provider 单次可达数十秒）
TRANSLATE_TIMEOUT_SECONDS = 2.0


@router.get("/search")
async def search(
    q: Annotated[str, Query(min_length=1, max_length=500)] = "",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query(max_length=1000)] = None,
    platform: Annotated[str | None, Query(max_length=500)] = None,
    tags: Annotated[str | None, Query(max_length=2000)] = None,
    security_level: Annotated[str | None, Query(max_length=500)] = None,
    mode: str = Query("hybrid", pattern="^(text|semantic|hybrid)$"),
    scope: str = Query("summary", pattern="^(summary|full)$"),
    sort_by: Annotated[str, Query(pattern="^(relevance|updated_at|download_count)$")] = "relevance",
    sort_period: Annotated[str | None, Query(pattern="^(week|month)$")] = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tag_list = tags.split(",") if tags else None
    category_list = category.split(",") if category else None
    security_level_list = security_level.split(",") if security_level else None
    embedding = None
    translated_query = None

    settings = get_settings()
    semantic_enabled = settings.ai.enable_semantic_search

    if mode in ("semantic", "hybrid") and semantic_enabled:
        # 原查询 embedding 与翻译并行发起，两者耗时取 max 而非相加
        embed_task = generate_query_embedding(q)
        translate_task = (
            asyncio.wait_for(translate_query_to_english(q), timeout=TRANSLATE_TIMEOUT_SECONDS)
            if mode == "hybrid"
            else asyncio.sleep(0)
        )
        gather_results = await asyncio.gather(
            embed_task, translate_task, return_exceptions=True,
        )
        embedding = (
            gather_results[0]
            if not isinstance(gather_results[0], BaseException)
            else None
        )
        translate_result = gather_results[1]
        if mode == "hybrid" and isinstance(translate_result, asyncio.TimeoutError):
            _logger.warning(
                "LLM 翻译超时，跳过翻译腿 (timeout=%ss, query=%r)",
                TRANSLATE_TIMEOUT_SECONDS,
                q[:50],
            )
            translated_query = None
        elif isinstance(translate_result, BaseException):
            _logger.warning(
                "LLM 翻译异常，跳过翻译腿 (query=%r): %s",
                q[:50],
                translate_result,
            )
            translated_query = None
        elif mode == "hybrid":
            translated_query = translate_result
        else:
            translated_query = None

    if embedding is None:
        mode = "text"

    translated_embedding = None
    if translated_query:
        try:
            translated_embedding = await generate_query_embedding(translated_query)
        except Exception:
            translated_embedding = None

    search_service = SearchService(db)
    results = await search_service.search_skills(
        query=q,
        limit=limit,
        offset=skip,
        category=category_list,
        platform=platform,
        tags=tag_list,
        security_level=security_level_list,
        embedding=embedding,
        mode=mode,
        scope=scope,
        translated_query=translated_query,
        translated_embedding=translated_embedding,
        sort_by=sort_by,
        sort_period=sort_period,
    )

    return results


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    stats = await repo.get_stats()
    return {
        "total_skills": stats["total_skills"],
        "total_categories": stats["total_categories"],
        "total_downloads": stats["total_downloads"],
        "categories": stats["categories"][:10],
        "platforms": stats.get("platforms", []),
        "security_levels": stats.get("security_levels", []),
    }


@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    stats = await repo.get_stats()
    return {
        "categories": stats["categories"],
    }
