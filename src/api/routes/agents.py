from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.repository import AgentRepository
from src.core.database import get_db

router = APIRouter()


def agent_to_dict(agent) -> dict[str, Any]:
    return {
        "id": str(agent.id),
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "commit_id": agent.commit_id,
        "version": agent.version,
        "author": agent.author,
        "source": agent.source,
        "source_url": agent.source_url,
        "category": agent.category,
        "tags": agent.tags,
        "logo_url": agent.logo_url,
        "homepage_url": agent.homepage_url,
        "license": agent.license,
        "readme_content": agent.readme_content,
        "agent_yaml_content": agent.agent_yaml_content,
        "parsed_config": agent.parsed_config,
        "supported_platforms": agent.supported_platforms,
        "verified": agent.verified,
        "star_count": agent.star_count,
        "contributor_count": agent.contributor_count,
        "extra_metadata": agent.extra_metadata,
        "security_score": agent.security_score,
        "download_count": agent.download_count,
        "rating": agent.rating,
        "latest_commit_id": agent.latest_commit_id,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/")
async def list_agents(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    tags: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    tag_list = tags.split(",") if tags else None
    repo = AgentRepository(db)
    agents, total = await repo.list(skip=skip, limit=limit, category=category, tags=tag_list)

    return {
        "agents": [agent_to_dict(a) for a in agents],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{agent_id}")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_to_dict(agent)


@router.get("/{agent_id}/versions")
async def get_agent_versions(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    versions = await repo.get_versions(agent.id)

    return {
        "agent_id": agent_id,
        "versions": [
            {
                "version": v.version,
                "commit_id": v.commit_id,
                "author": v.author,
                "message": v.message,
                "released_at": v.released_at.isoformat() if v.released_at else None,
                "download_count": v.download_count,
            }
            for v in versions
        ],
    }


@router.get("/{agent_id}/download")
async def download_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"download_url": agent.source_url}
