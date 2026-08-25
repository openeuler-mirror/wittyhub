import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from skillcrawler.core.skill_parser import (
    build_public_skill_id_from_relative_path,
    extract_owner_repo,
)

from src.models.repository import SkillRepository


def _slugify_telemetry_value(value: str) -> str:
    lowered = value.strip().lower()
    if not lowered:
        return ""
    normalized = re.sub(r"[^a-z0-9._-]+", "-", lowered)
    normalized = re.sub(r"-{2,}", "-", normalized)
    return normalized.strip("-")


def build_skill_id_from_telemetry(
    source_type: str | None,
    source: str | None,
    skill_name: str,
    skill_files: dict[str, str] | None = None,
) -> str | None:
    if source_type not in {"github", "gitcode", "gitlab", "gitee"}:
        return None
    if not source:
        return None

    try:
        owner_repo = extract_owner_repo(source)
    except ValueError:
        return None

    # Prefer the repo-relative SKILL.md path. It uses the exact same
    # derivation as the crawler (skill_parser.build_public_skill_id) that
    # wrote the skill records, so install telemetry/audit lookups hit the
    # same skill_id that exists in the database.
    if skill_files:
        relative_path = skill_files.get(skill_name)
        if relative_path:
            normalized_path = relative_path.strip().replace("\\", "/").rstrip("/")
            try:
                return build_public_skill_id_from_relative_path(
                    source_type, owner_repo, normalized_path
                )
            except ValueError:
                pass

    # No path info available — fall back to the skill name slug.
    skill_path = _slugify_telemetry_value(skill_name)
    if not skill_path:
        return None
    return f"{source_type}:{owner_repo}/{skill_path}"


class TelemetryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.skill_repo = SkillRepository(session)

    async def process(self, params: dict[str, str]) -> list[str]:
        if params.get("event") != "install":
            return []

        return await self._process_install(params)

    async def _process_install(self, params: dict[str, str]) -> list[str]:
        source = params.get("source")
        source_type = params.get("sourceType")
        skills = [skill.strip() for skill in params.get("skills", "").split(",") if skill.strip()]

        skill_files: dict[str, str] | None = None
        raw_skill_files = params.get("skillFiles")
        if raw_skill_files:
            try:
                parsed_skill_files = json.loads(raw_skill_files)
            except json.JSONDecodeError:
                parsed_skill_files = None
            if isinstance(parsed_skill_files, dict):
                skill_files = {
                    str(key): str(value)
                    for key, value in parsed_skill_files.items()
                    if isinstance(key, str) and isinstance(value, str)
                }

        matched_skill_ids: list[str] = []
        for skill_name in skills:
            skill_id = build_skill_id_from_telemetry(source_type, source, skill_name, skill_files)
            if not skill_id:
                continue
            updated = await self.skill_repo.increment_download(skill_id)
            if updated:
                matched_skill_ids.append(skill_id)

        if matched_skill_ids:
            await self.session.commit()

        return matched_skill_ids
