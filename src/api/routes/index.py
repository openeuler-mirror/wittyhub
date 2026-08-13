from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.ai.embedding import generate_embeddings, prepare_skill_text
from src.core.database import get_db
from src.core.config import  get_settings
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
            embeddings = await generate_embeddings([q])
            embedding = embeddings[0] if embeddings else None
        except Exception:
            embedding = None
            mode = "text"

    if embedding is None:
        mode = "text"

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
    )

    return results


@router.post("/reindex")
async def reindex(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    skills, total = await repo.list(skip=0, limit=1000)

    indexed_count = 0
    for skill in skills:
        try:
            text = prepare_skill_text(skill)
            if text.strip():
                embeddings = await generate_embeddings([text])
                if embeddings and embeddings[0]:
                    await repo.update_embedding(skill.skill_id, embeddings[0])
                    indexed_count += 1
        except Exception:
            continue

    return {
        "status": "completed",
        "indexed_count": indexed_count,
        "total_skills": total,
    }


@router.post("/reindex/{skill_id:path}")
async def reindex_skill(
    skill_id: Annotated[str, Path(min_length=1, max_length=255)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    skill = await repo.get_by_skill_id(skill_id)

    if not skill:
        return {"status": "error", "message": "Skill not found"}

    try:
        text = prepare_skill_text(skill)
        if text.strip():
            embeddings = await generate_embeddings([text])
            if embeddings and embeddings[0]:
                await repo.update_embedding(skill_id, embeddings[0])
                return {"status": "completed", "skill_id": skill_id, "embedding_generated": True}
    except Exception as e:
        return {"status": "completed", "skill_id": skill_id, "embedding_generated": False, "error": str(e)}

    await repo.update_last_indexed(skill_id)
    return {"status": "completed", "skill_id": skill_id}


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    stats = await repo.get_stats()
    return {
        "total_skills": stats["total_skills"],
        "total_categories": stats["total_categories"],
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
