from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.embedding import generate_query_embedding
from src.ai.translation import translate_query_to_english
from src.core.config import get_settings
from src.core.database import get_db
from src.indexer.search import SearchService
from src.models.repository import SkillRepository

router = APIRouter()


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

    settings = get_settings()
    semantic_enabled = settings.ai.enable_semantic_search

    if mode in ("semantic", "hybrid") and semantic_enabled:
        try:
            embedding = await generate_query_embedding(q)
        except Exception:
            embedding = None
            mode = "text"

    if embedding is None:
        mode = "text"

    translated_query = None
    translated_embedding = None
    if mode == "hybrid":
        translated_query = await translate_query_to_english(q)
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
