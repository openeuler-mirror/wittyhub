from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.repository import SkillRepository
from src.core.database import get_db
from src.indexer.search import SearchService
from src.ai.embedding import generate_embeddings, prepare_skill_text, load_settings


router = APIRouter()


@router.get("/search")
async def search(
    q: Annotated[str, Query(min_length=1)] = "",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    platform: str | None = None,
    tags: str | None = None,
    mode: str = Query("hybrid", regex="^(text|semantic|hybrid)$"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tag_list = tags.split(",") if tags else None
    embedding = None

    settings = load_settings()
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
        category=category,
        platform=platform,
        tags=tag_list,
        embedding=embedding,
        mode=mode,
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
    skill_id: str,
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
