from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.repository import AgentRepository
from core.database import get_db

router = APIRouter()


@router.get("/")
async def list_agents(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    repo = AgentRepository(db)
    agents, total = await repo.list(skip=skip, limit=limit, category=category)

    return {
        "agents": [
            {
                "id": str(a.id),
                "agent_id": a.agent_id,
                "name": a.name,
                "description": a.description,
                "version": a.version,
                "author": a.author,
                "source": a.source,
                "source_url": a.source_url,
                "category": a.category,
                "tags": a.tags,
                "platform": a.platform,
                "metadata": a.extra_metadata,
                "security_score": a.security_score,
                "download_count": a.download_count,
                "rating": a.rating,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "updated_at": a.updated_at.isoformat() if a.updated_at else None,
            }
            for a in agents
        ],
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

    return {
        "id": str(agent.id),
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "version": agent.version,
        "author": agent.author,
        "source": agent.source,
        "source_url": agent.source_url,
        "category": agent.category,
        "tags": agent.tags,
        "platform": agent.platform,
        "metadata": agent.extra_metadata,
        "security_score": agent.security_score,
        "download_count": agent.download_count,
        "rating": agent.rating,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }