from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.repository import SkillRepository, DownloadHistoryRepository, SkillRepoRepository
from src.api.schemas.skill import (
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    SkillVersionsResponse,
    SecurityAuditResponse,
    ErrorResponse,
    DownloadResponse,
)
from src.api.services.security import SecurityService
from src.api.services.telemetry import TelemetryService
from src.core.database import get_db
from src.storage.downloader import DownloadManager

router = APIRouter()


@router.get("/telemetry")
async def receive_telemetry(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Receive telemetry data from wittyhub CLI and update counters for installs.
    request params: 
    {   
        'v': '1.5.13', 
        'event': 'install', 
        'source': 'vercel-labs/agent-skills', 
        'skills': 'deploy-to-vercel', 
        'agents': 'amp,antigravity,antigravity-cli,cline,codex,cursor,deepagents,gemini-cli,github-copilot,kimi-code-cli,opencode,warp,zed,openclaw', 
        'skillFiles': '{"deploy-to-vercel":"skills/deploy-to-vercel/SKILL.md"}'
    }
    """
    params = dict(request.query_params)
    telemetry_service = TelemetryService(db)
    matched_skill_ids = await telemetry_service.process(params)
    return {"ok": True, "matched_skill_ids": matched_skill_ids}


def skill_to_response(skill) -> SkillResponse:
    return SkillResponse(
        id=str(skill.id),
        skill_id=skill.skill_id,
        name=skill.name,
        description=skill.description,
        version=skill.version,
        commit_id=skill.commit_id,
        author=skill.author,
        source=skill.source,
        source_url=skill.source_url,
        category=skill.category,
        tags=skill.tags,
        platform=skill.platform,
        metadata=skill.extra_metadata,
        content=skill.content,
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
    sort_by: Annotated[str, Query(pattern="^(updated_at|download_count)$")] = "updated_at",
    db: AsyncSession = Depends(get_db),
):
    tag_list = tags.split(",") if tags else None
    repo = SkillRepository(db)
    skills, total = await repo.list(
        skip=skip,
        limit=limit,
        category=category,
        platform=platform,
        tags=tag_list,
        sort_by=sort_by,
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


@router.post("/{skill_id:path}/audit", response_model=SecurityAuditResponse | ErrorResponse)
async def trigger_skill_audit(
    skill_id: str,
    scanners: str | None = Query(None, description="Comma-separated: skillspector"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a fresh security audit for a skill and return the result."""
    repo = SkillRepository(db)
    skill = await repo.get_by_skill_id(skill_id)

    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    scanner_list = None
    if scanners:
        scanner_list = [s.strip() for s in scanners.split(",") if s.strip()]

    security_service = SecurityService(db)
    audit_result = await security_service.audit_skill(
        skill_id=skill.skill_id,
        source=skill.source,
        source_url=skill.source_url,
        metadata={
            "version": skill.version,
            "content": skill.content,
        },
        scanners=scanner_list,
    )

    if "error" in audit_result:
        return {"error": audit_result["error"]}

    # Fetch the newly created audit record
    audit_repo = security_service.audit_repo
    latest_audit = await audit_repo.get_latest_by_resource("skill", skill.id)

    if not latest_audit:
        return {"error": "Audit completed but no record found"}

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


@router.get("/versions/{skill_id:path}", response_model=SkillVersionsResponse)
async def get_skill_versions(
    skill_id: str,
    db: AsyncSession = Depends(get_db),
):
    skill_repo = SkillRepository(db)
    latest_skill = await skill_repo.get_by_skill_id(skill_id)
    tagged_versions = await skill_repo.get_versions_by_base_skill(None, skill_id)

    if not latest_skill and not tagged_versions:
        raise HTTPException(status_code=404, detail="Skill not found")

    versions = [latest_skill]
    if tagged_versions is not None:
        versions.extend(tagged_versions)

    return SkillVersionsResponse(
        source_url=latest_skill.source_url,
        skill_id=skill_id,
        versions=[skill_to_response(s) for s in versions],
    )


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
    download_url = await download_manager.get_download_url(
        skill.source, skill.source_url, skill.skill_id, skill.version, skill.commit_id
    )

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

    skill_dict = skill_data.model_dump()

    # Resolve skill_repo_id: look up or create the source repository
    if not skill_dict.get("skill_repo_id"):
        repo_repo = SkillRepoRepository(db)
        source = skill_data.source
        source_url = skill_data.source_url
        path_parts = source_url.rstrip("/").split("/")
        repo_name = f"{source}-{path_parts[-2]}-{path_parts[-1]}" if len(path_parts) >= 2 else f"{source}-{source_url}"
        existing_repo = await repo_repo.get_skill_repository_by_repo_name(repo_name)
        if existing_repo:
            skill_dict["skill_repo_id"] = existing_repo.id
        else:
            new_repo = await repo_repo.create_skill_repository(
                repo_name=repo_name,
                source=source,
                branch=skill_data.version or "main",
                url=source_url,
                local_path=None,
                skill_discover_status="init",
            )
            skill_dict["skill_repo_id"] = new_repo.id

    skill = await repo.create(skill_dict)

    # Run security audit after skill is persisted, then write back the score
    security_service = SecurityService(db)
    if security_service.detector.enable_audit:
        try:
            audit_result = await security_service.audit_skill(
                skill.skill_id,
                skill.source,
                skill.source_url,
                {"version": skill.version, "content": skill.content or ""},
            )
            # security_score is already persisted by audit_skill internally
        except Exception:
            pass  # audit failure must not block skill creation

    return skill_to_response(skill)


@router.delete("/{skill_id:path}")
async def delete_skill(skill_id: str, db: AsyncSession = Depends(get_db)):
    repo = SkillRepository(db)
    deleted = await repo.delete(skill_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found")

    return {"message": "Skill deleted", "skill_id": skill_id}
