from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.routes.skills import batch_audit_skills


@pytest.mark.asyncio
async def test_batch_audit_skills_empty_skills_returns_empty_dict():
    db = AsyncMock()
    with (
        patch("src.api.routes.skills.SkillRepository"),
        patch("src.api.routes.skills.SecurityAuditRepository"),
    ):
        result = await batch_audit_skills(
            source="vercel-labs/agent-skills", skills="", source_type="github", db=db
        )

    assert result == {}


@pytest.mark.asyncio
async def test_batch_audit_skills_returns_unknown_for_missing_skills():
    skill_repository = MagicMock()
    skill_repository.list_by_skill_ids = AsyncMock(return_value=[])
    audit_repository = MagicMock()
    db = AsyncMock()

    with (
        patch("src.api.routes.skills.SkillRepository", return_value=skill_repository),
        patch(
            "src.api.routes.skills.SecurityAuditRepository", return_value=audit_repository
        ),
    ):
        result = await batch_audit_skills(
            source="vercel-labs/agent-skills",
            skills="deploy-to-vercel,missing",
            source_type="github",
            db=db,
        )

    assert result["deploy-to-vercel"]["risk_level"] == "unknown"
    assert result["deploy-to-vercel"]["risk_score"] is None
    assert result["deploy-to-vercel"]["risk_signals"] == []
    assert result["missing"]["risk_level"] == "unknown"


@pytest.mark.asyncio
async def test_batch_audit_skills_returns_audit_data_for_matched_skills():
    skill = SimpleNamespace(
        skill_id="github/vercel-labs/agent-skills/deploy-to-vercel",
        id=1,
        risk_score=85,
    )
    audit = SimpleNamespace(
        risk_level="high",
        risk_signals=[{"id": "s1", "name": "risky", "severity": "high"}],
        audited_at=None,
    )
    skill_repository = MagicMock()
    skill_repository.list_by_skill_ids = AsyncMock(return_value=[skill])
    audit_repository = MagicMock()
    audit_repository.get_latest_by_resources = AsyncMock(return_value={1: audit})
    db = AsyncMock()

    with (
        patch("src.api.routes.skills.SkillRepository", return_value=skill_repository),
        patch(
            "src.api.routes.skills.SecurityAuditRepository", return_value=audit_repository
        ),
    ):
        result = await batch_audit_skills(
            source="vercel-labs/agent-skills",
            skills="deploy-to-vercel",
            source_type="github",
            db=db,
        )

    data = result["deploy-to-vercel"]
    assert data["risk_level"] == "high"
    assert data["risk_score"] == 85
    assert data["risk_signals"] == [{"id": "s1", "name": "risky", "severity": "high"}]
    assert data["audited_at"] is None
    audit_repository.get_latest_by_resources.assert_awaited_once_with("skill", [1])


@pytest.mark.asyncio
async def test_batch_audit_skills_forwards_source_type_and_derives_skill_id():
    skill_repository = MagicMock()
    skill_repository.list_by_skill_ids = AsyncMock(return_value=[])
    audit_repository = MagicMock()
    db = AsyncMock()

    with (
        patch("src.api.routes.skills.SkillRepository", return_value=skill_repository),
        patch(
            "src.api.routes.skills.SecurityAuditRepository", return_value=audit_repository
        ),
    ):
        await batch_audit_skills(
            source="openeuler/skillhub",
            skills="clean-code",
            source_type="gitcode",
            db=db,
        )

    # skill_id must be derived with the given source_type
    skill_repository.list_by_skill_ids.assert_awaited_once_with(
        ["gitcode/openeuler/skillhub/clean-code"]
    )


@pytest.mark.asyncio
async def test_batch_audit_skills_uses_skill_files_to_derive_skill_id():
    skill_repository = MagicMock()
    skill_repository.list_by_skill_ids = AsyncMock(return_value=[])
    audit_repository = MagicMock()
    db = AsyncMock()

    with (
        patch("src.api.routes.skills.SkillRepository", return_value=skill_repository),
        patch(
            "src.api.routes.skills.SecurityAuditRepository", return_value=audit_repository
        ),
    ):
        await batch_audit_skills(
            source="vercel-labs/agent-skills",
            skills="deploy-to-vercel",
            source_type="github",
            skill_files='{"deploy-to-vercel": "skills/deploy-to-vercel/SKILL.md"}',
            db=db,
        )

    # skill_id must be derived from the file path, not the name slug —
    # matching the install telemetry so both hit the same record.
    skill_repository.list_by_skill_ids.assert_awaited_once_with(
        ["github/vercel-labs/agent-skills/skills/deploy-to-vercel"]
    )


@pytest.mark.asyncio
async def test_batch_audit_skills_fetches_audits_in_batch():
    skill = SimpleNamespace(
        skill_id="github/vercel-labs/agent-skills/deploy-to-vercel",
        id=1,
        risk_score=85,
    )
    audit = SimpleNamespace(
        risk_level="high",
        risk_signals=[{"id": "s1", "name": "risky", "severity": "high"}],
        audited_at=None,
    )
    skill_repository = MagicMock()
    skill_repository.list_by_skill_ids = AsyncMock(return_value=[skill])
    audit_repository = MagicMock()
    audit_repository.get_latest_by_resources = AsyncMock(return_value={1: audit})
    db = AsyncMock()

    with (
        patch("src.api.routes.skills.SkillRepository", return_value=skill_repository),
        patch(
            "src.api.routes.skills.SecurityAuditRepository", return_value=audit_repository
        ),
    ):
        result = await batch_audit_skills(
            source="vercel-labs/agent-skills",
            skills="deploy-to-vercel",
            source_type="github",
            db=db,
        )

    audit_repository.get_latest_by_resources.assert_awaited_once_with("skill", [1])
    assert result["deploy-to-vercel"]["risk_level"] == "high"
    assert result["deploy-to-vercel"]["risk_score"] == 85
