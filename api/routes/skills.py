import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.repository import SkillRepository, DownloadHistoryRepository
from api.schemas.skill import (
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    DownloadResponse,
    SecurityAuditResponse,
    ErrorResponse,
)
from api.services.security import SecurityService
from core.database import get_db
from storage.downloader import DownloadManager

router = APIRouter()


def skill_to_response(skill) -> SkillResponse:
    return SkillResponse(
        id=str(skill.id),
        skill_id=skill.skill_id,
        name=skill.name,
        description=skill.description,
        version=skill.version,
        author=skill.author,
        source=skill.source,
        source_url=skill.source_url,
        category=skill.category,
        tags=skill.tags,
        platform=skill.platform,
        metadata=skill.extra_metadata,
        security_score=skill.security_score,
        download_count=skill.download_count,
        rating=skill.rating,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
        last_indexed_at=skill.last_indexed_at,
    )


@router.get("/", response_model=SkillListResponse)
async def list_skills(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    platform: str | None = None,
    tags: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    tag_list = tags.split(",") if tags else None
    repo = SkillRepository(db)
    skills, total = await repo.list(
        skip=skip, limit=limit, category=category, platform=platform, tags=tag_list
    )

    return SkillListResponse(
        skills=[skill_to_response(s) for s in skills],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{skill_id:path}/audit", response_model=SecurityAuditResponse | ErrorResponse)
async def audit_skill(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.get_by_skill_id(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    security_service = SecurityService(db)
    audit_repo = security_service.audit_repo
    latest_audit = await audit_repo.get_latest_by_resource("skill", skill.id)

    if latest_audit:
        return SecurityAuditResponse(
            id=str(latest_audit.id),
            resource_type=latest_audit.resource_type,
            resource_id=str(latest_audit.resource_id),
            audit_type=latest_audit.audit_type,
            risk_level=latest_audit.risk_level,
            risk_signals=latest_audit.risk_signals,
            details=latest_audit.details,
            audited_at=latest_audit.audited_at,
        )

    return {"error": "No audit found"}


@router.get("/{skill_id:path}/download", response_model=DownloadResponse)
async def download_skill(
    skill_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)
    skill = await repo.get_by_skill_id(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    download_manager = DownloadManager()
    download_url = await download_manager.get_download_url(skill.source, skill.source_url)

    dl_history = DownloadHistoryRepository(db)
    await dl_history.create({
        "resource_type": "skill",
        "resource_id": skill.id,
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    })
    await repo.increment_download(skill_id)

    return DownloadResponse(
        download_url=download_url,
        file_path=None,
        security_audit=None,
    )


@router.get("/{skill_id:path}", response_model=SkillResponse | ErrorResponse)
async def get_skill(skill_id: str, db: AsyncSession = Depends(get_db)):
    repo = SkillRepository(db)
    skill = await repo.get_by_skill_id(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return skill_to_response(skill)


@router.post("/", response_model=SkillResponse, status_code=201)
async def create_skill(
    skill_data: SkillCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    repo = SkillRepository(db)

    existing = await repo.get_by_skill_id(skill_data.skill_id)
    if existing:
        raise HTTPException(status_code=409, detail="Skill already exists")

    security_service = SecurityService(db)

    skill_dict = skill_data.model_dump()
    if security_service.detector.enable_audit:
        audit_result = await security_service.audit_skill(
            skill_data.skill_id,
            skill_data.source,
            skill_data.source_url,
            skill_dict,
        )
        skill_dict["security_score"] = audit_result.get("security_score")

    skill = await repo.create(skill_dict)
    return skill_to_response(skill)


@router.delete("/{skill_id:path}")
async def delete_skill(skill_id: str, db: AsyncSession = Depends(get_db)):
    repo = SkillRepository(db)
    deleted = await repo.delete(skill_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {"message": "Skill deleted", "skill_id": skill_id}
