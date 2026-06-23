import uuid
from datetime import datetime
import re
from typing import Any, List

from sqlalchemy import func, select, update, delete, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.orm import (
    Skill,
    Agent,
    SecurityAudit,
    DownloadHistory,
)


class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _version_sort_key(self, skill: Skill) -> tuple[int, tuple[int, ...], int, str, datetime, datetime]:
        version = (skill.version or "").strip()
        match = re.fullmatch(
            r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?",
            version,
            flags=re.IGNORECASE,
        )
        if match:
            major = int(match.group(1) or 0)
            minor = int(match.group(2) or 0)
            patch = int(match.group(3) or 0)
            prerelease = (match.group(4) or "").lower()
            is_stable = 1 if not prerelease else 0
            return (
                1,
                (major, minor, patch),
                is_stable,
                prerelease,
                skill.updated_at,
                skill.created_at,
            )
        return (0, tuple(), 0, "", skill.updated_at, skill.created_at)

    def _dedupe_skills(self, skills: list[Skill]) -> list[Skill]:
        grouped: dict[str, Skill] = {}

        for skill in skills:
            skill_id = (skill.skill_id or "").strip()
            if not skill_id:
                continue

            existing = grouped.get(skill_id)
            if existing is None or self._version_sort_key(skill) > self._version_sort_key(existing):
                grouped[skill_id] = skill

        deduped = list(grouped.values())
        return sorted(
            deduped,
            key=lambda skill: self._version_sort_key(skill),
            reverse=True,
        )

    def _apply_skill_filters(
        self,
        query,
        *,
        category: str | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
    ):
        if category:
            query = query.where(Skill.category == category)
        if platform:
            query = query.where(Skill.platform == platform)
        if tags:
            query = query.where(Skill.tags.contains(tags))
        if source:
            query = query.where(Skill.source == source)
        return query

    def _latest_unique_skills_subquery(self):
        return (
            select(Skill)
            .distinct(Skill.skill_id)
            .order_by(Skill.skill_id, desc(Skill.updated_at), desc(Skill.created_at))
            .subquery()
        )

    async def create(self, skill_data: dict[str, Any]) -> Skill:
        skill = Skill(**skill_data)
        self.session.add(skill)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def get_by_skill_id(self, skill_id: str) -> Skill | None:
        skills = await self.get_versions_by_base_skill(None, skill_id)
        return skills[0] if skills else None

    async def get_category_by_source_url(self, source_url: str) -> str | None:
        result = await self.session.execute(
            select(Skill.category)
            .where(
                Skill.source_url == source_url,
                Skill.category.is_not(None),
                Skill.category != "",
            )
            .order_by(desc(Skill.updated_at), desc(Skill.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_category_by_skill_id(self, skill_id: str) -> str | None:
        result = await self.session.execute(
            select(Skill.category)
            .where(
                Skill.skill_id == skill_id,
                Skill.category.is_not(None),
                Skill.category != "",
            )
            .order_by(desc(Skill.updated_at), desc(Skill.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def replace_for_source_repository(
        self,
        source_repository_id: uuid.UUID,
        skills: list[Skill],
    ) -> list[Skill]:
        await self.session.execute(
            delete(Skill).where(Skill.skill_source_repository_id == source_repository_id)
        )
        for skill in skills:
            skill.skill_source_repository_id = source_repository_id
        self.session.add_all(skills)
        await self.session.flush()
        await self.session.commit()
        return skills

    async def get_versions_by_base_skill(self, source_url: str | None, skill_id: str) -> list[Skill]:
        query = select(Skill)
        query = query.where(Skill.skill_id == skill_id)
        if source_url:
            query = query.where(Skill.source_url == source_url)
        query = query.order_by(desc(Skill.updated_at), desc(Skill.created_at))
        result = await self.session.execute(query)
        skills = list(result.scalars().all())
        return sorted(skills, key=self._version_sort_key, reverse=True)

    async def get_by_repo_and_name(self, repo: str, skill_name: str) -> list[Skill]:
        public_skill_id = f"{repo}/{skill_name}"
        result = await self.session.execute(
            select(Skill)
            .where(Skill.skill_id == public_skill_id)
            .order_by(desc(Skill.updated_at), desc(Skill.created_at))
        )
        return list(result.scalars().all())

    async def get_by_id(self, id: uuid.UUID) -> Skill | None:
        result = await self.session.execute(
            select(Skill).where(Skill.id == id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
    ) -> tuple[list[Skill], int]:
        filtered_query = self._apply_skill_filters(
            select(Skill),
            category=category,
            platform=platform,
            tags=tags,
            source=source,
        )

        count_query = self._apply_skill_filters(
            select(func.count(func.distinct(Skill.skill_id))),
            category=category,
            platform=platform,
            tags=tags,
            source=source,
        )
        total = await self.session.scalar(count_query)

        distinct_query = (
            filtered_query
            .distinct(Skill.skill_id)
            .order_by(Skill.skill_id, desc(Skill.updated_at), desc(Skill.created_at))
        )
        subquery = distinct_query.subquery()
        deduped_query = (
            select(Skill)
            .join(subquery, Skill.id == subquery.c.id)
            .order_by(desc(Skill.updated_at), desc(Skill.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(deduped_query)
        skills = list(result.scalars().all())

        return skills, total or 0

    async def update(self, skill_id: str, update_data: dict[str, Any]) -> Skill | None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return None
        update_data["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(Skill).where(Skill.id == existing.id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_skill_id(skill_id)

    async def delete(self, skill_id: str) -> bool:
        result = await self.session.execute(
            delete(Skill).where(Skill.skill_id == skill_id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def increment_download(self, skill_id: str) -> None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return
        await self.session.execute(
            update(Skill)
            .where(Skill.id == existing.id)
            .values(download_count=Skill.download_count + 1)
        )
        await self.session.flush()

    async def update_last_indexed(self, skill_id: str) -> None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return
        await self.session.execute(
            update(Skill)
            .where(Skill.id == existing.id)
            .values(last_indexed_at=datetime.utcnow())
        )
        await self.session.flush()

    async def update_embedding(self, skill_id: str, embedding: List[float]) -> None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return
        await self.session.execute(
            update(Skill)
            .where(Skill.id == existing.id)
            .values(embedding=embedding, last_indexed_at=datetime.utcnow())
        )
        await self.session.flush()
        await self.session.commit()

    async def get_stats(self) -> dict[str, Any]:
        latest_skills = self._latest_unique_skills_subquery()

        total_result = await self.session.execute(
            select(func.count()).select_from(latest_skills)
        )
        total_skills = total_result.scalar() or 0

        raw_category_key = func.lower(
            func.nullif(func.trim(latest_skills.c.category), "")
        )
        normalized_category = case(
            (raw_category_key.is_(None), "others"),
            (raw_category_key.in_(["other", "others"]), "others"),
            else_=raw_category_key,
        )
        category_result = await self.session.execute(
            select(
                normalized_category.label("category_key"),
                func.min(latest_skills.c.category).label("display_name"),
                func.count().label("count"),
            )
            .select_from(latest_skills)
            .group_by(normalized_category)
            .order_by(func.count().desc())
        )
        categories = []
        for row in category_result.fetchall():
            category_key = row.category_key
            if category_key in {None, "other", "others"}:
                display_name = "Others"
            else:
                display_name = row.display_name or "Others"
            categories.append({"name": display_name, "count": row.count})
        categories.sort(
            key=lambda item: (
                1 if str(item["name"]).lower() == "others" else 0,
                -int(item["count"]),
                str(item["name"]).lower(),
            )
        )
        total_categories = len(categories)

        return {
            "total_skills": total_skills,
            "total_categories": total_categories,
            "categories": categories,
        }


class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, agent_data: dict[str, Any]) -> Agent:
        agent = Agent(**agent_data)
        self.session.add(agent)
        await self.session.flush()
        await self.session.refresh(agent)
        return agent

    async def get_by_agent_id(self, agent_id: str) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.agent_id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: uuid.UUID) -> Agent | None:
        result = await self.session.execute(
            select(Agent).where(Agent.id == id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 20,
        category: str | None = None,
    ) -> tuple[list[Agent], int]:
        query = select(Agent)

        if category:
            query = query.where(Agent.category == category)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.offset(skip).limit(limit).order_by(Agent.created_at.desc())
        result = await self.session.execute(query)
        agents = list(result.scalars().all())

        return agents, total or 0

    async def delete(self, agent_id: str) -> bool:
        result = await self.session.execute(
            delete(Agent).where(Agent.agent_id == agent_id)
        )
        await self.session.flush()
        return result.rowcount > 0


class SecurityAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, audit_data: dict[str, Any]) -> SecurityAudit:
        audit = SecurityAudit(**audit_data)
        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(audit)
        return audit

    async def get_latest_by_resource(
        self, resource_type: str, resource_id: uuid.UUID
    ) -> SecurityAudit | None:
        result = await self.session.execute(
            select(SecurityAudit)
            .where(
                SecurityAudit.resource_type == resource_type,
                SecurityAudit.resource_id == resource_id,
            )
            .order_by(SecurityAudit.audited_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_resource(
        self, resource_type: str, resource_id: uuid.UUID
    ) -> list[SecurityAudit]:
        result = await self.session.execute(
            select(SecurityAudit)
            .where(
                SecurityAudit.resource_type == resource_type,
                SecurityAudit.resource_id == resource_id,
            )
            .order_by(SecurityAudit.audited_at.desc())
        )
        return list(result.scalars().all())


class DownloadHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, download_data: dict[str, Any]) -> DownloadHistory:
        record = DownloadHistory(**download_data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record
