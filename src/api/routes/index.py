from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.repository import SkillRepository
from src.api.schemas.skill import SkillResponse
from src.core.database import get_db
from src.indexer.search import get_search_client, SearchClient

router = APIRouter()


def skill_to_dict(skill) -> dict[str, Any]:
    return {
        "id": str(skill.id),
        "skill_id": skill.skill_id,
        "name": skill.name,
        "description": skill.description,
        "version": skill.version,
        "author": skill.author,
        "source": skill.source,
        "source_url": skill.source_url,
        "category": skill.category,
        "tags": skill.tags or [],
        "platform": skill.platform,
        "metadata": skill.extra_metadata,
        "security_score": skill.security_score,
        "download_count": skill.download_count,
        "rating": skill.rating,
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
    }


@router.get("/search")
async def search(
    q: Annotated[str, Query(min_length=1)] = "",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    platform: str | None = None,
    tags: str | None = None,
    search_client: SearchClient = Depends(get_search_client),
) -> dict[str, Any]:
    filters = {}
    if category:
        filters["category"] = category
    if platform:
        filters["platform"] = platform
    if tags:
        filters["tags"] = tags.split(",")

    results = search_client.search_skills(
        query=q,
        limit=limit,
        offset=skip,
        filters=filters if filters else None,
    )

    return {
        "results": results.get("hits", []),
        "total": results.get("estimatedTotalHits", 0),
        "query": q,
        "skip": skip,
        "limit": limit,
        "processing_time_ms": results.get("processingTimeMs", 0),
    }


@router.post("/reindex")
async def reindex(
    db: AsyncSession = Depends(get_db),
    search_client: SearchClient = Depends(get_search_client),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    skills, total = await repo.list(skip=0, limit=1000)

    skills_data = [skill_to_dict(s) for s in skills]

    if skills_data:
        search_client.index_skills(skills_data)

    return {
        "status": "completed",
        "indexed_count": len(skills_data),
        "total_skills": total,
    }


@router.post("/reindex/{skill_id:path}")
async def reindex_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
    search_client: SearchClient = Depends(get_search_client),
) -> dict[str, Any]:
    repo = SkillRepository(db)
    skill = await repo.get_by_skill_id(skill_id)

    if not skill:
        return {"status": "error", "message": "Skill not found"}

    skill_dict = skill_to_dict(skill)
    search_client.index_skill(skill_dict)
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