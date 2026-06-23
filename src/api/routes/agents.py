import asyncio
import threading
from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.repository import AgentRepository, DownloadHistoryRepository
from src.api.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentVersionResponse,
    AgentVersionsResponse,
)
from src.core.database import get_db, AsyncSessionLocal
from src.storage.downloader import DownloadManager

router = APIRouter()
download_manager = DownloadManager()

download_counts: dict[str, int] = defaultdict(int)
_counts_lock = threading.Lock()
_flush_started = False

FLUSH_INTERVAL = 5.0

async def _flush_loop():
    while True:
        await asyncio.sleep(FLUSH_INTERVAL)

        with _counts_lock:
            if not download_counts:
                continue
            counts = dict(download_counts)
            download_counts.clear()

        async with AsyncSessionLocal() as session:
            agent_repo = AgentRepository(session)
            for agent_id, count in counts.items():
                for _ in range(count):
                    await agent_repo.increment_download(agent_id)
            await session.commit()


def _start_flush():
    global _flush_started
    if not _flush_started:
        asyncio.create_task(_flush_loop())
        _flush_started = True


def agent_to_response(agent) -> AgentResponse:
    return AgentResponse(
        id=str(agent.id),
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        version=agent.version,
        commit_id=agent.commit_id,
        author=agent.author,
        source=agent.source,
        source_url=agent.source_url,
        category=agent.category,
        tags=agent.tags,
        supported_platforms=agent.supported_platforms,
        logo_url=agent.logo_url,
        homepage_url=agent.homepage_url,
        license=agent.license,
        readme_content=agent.readme_content,
        agent_yaml_content=agent.agent_yaml_content,
        parsed_config=agent.parsed_config,
        verified=agent.verified,
        star_count=agent.star_count,
        contributor_count=agent.contributor_count,
        security_score=agent.security_score,
        download_count=agent.download_count,
        rating=agent.rating,
        latest_commit_id=agent.latest_commit_id,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    tags: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    tag_list = tags.split(",") if tags else None
    repo = AgentRepository(db)
    agents, total = await repo.list(skip=skip, limit=limit, category=category, tags=tag_list)

    return AgentListResponse(
        agents=[agent_to_response(a) for a in agents],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
):
    repo = AgentRepository(db)

    existing = await repo.get_by_agent_id(agent_data.agent_id)
    if existing:
        raise HTTPException(status_code=409, detail="Agent already exists")

    agent = await repo.create(agent_data.model_dump())
    return agent_to_response(agent)


@router.get("/{agent_id:path}/versions", response_model=AgentVersionsResponse)
async def get_agent_versions(agent_id: str, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    versions = await repo.get_versions(agent.id)

    return AgentVersionsResponse(
        agent_id=agent_id,
        versions=[
            AgentVersionResponse(
                version=v.version,
                commit_id=v.commit_id,
                author=v.author,
                message=v.message,
                released_at=v.released_at,
                download_count=v.download_count,
            )
            for v in versions
        ],
    )


@router.get("/{agent_id:path}/download")
async def download_agent(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _start_flush()

    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    download_url = await download_manager.get_download_url(
        agent.source, agent.source_url, None, agent.version, agent.latest_commit_id
    )

    with _counts_lock:
        download_counts[agent.id] += 1

    return {"download_url": download_url}


@router.get("/{agent_id:path}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    agent = await repo.get_by_agent_id(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent_to_response(agent)


@router.delete("/{agent_id:path}")
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    repo = AgentRepository(db)
    deleted = await repo.delete(agent_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"message": "Agent deleted", "agent_id": agent_id}
