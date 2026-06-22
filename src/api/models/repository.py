import uuid
from datetime import datetime
from typing import Any, List

from sqlalchemy import func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.models import Skill, Agent, SecurityAudit, DownloadHistory


class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, skill_data: dict[str, Any]) -> Skill:
        skill = Skill(**skill_data)
        self.session.add(skill)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    async def get_by_skill_id(self, skill_id: str) -> Skill | None:
        result = await self.session.execute(
            select(Skill).where(Skill.skill_id == skill_id)
        )
        return result.scalar_one_or_none()

    async def get_versions_by_base_skill(self, source_url: str | None, skill_name: str) -> list[Skill]:
        query = select(Skill)
        pattern = f"{skill_name}:%"
        query = query.where(Skill.skill_id.like(pattern))
        if source_url:
            query = query.where(Skill.source_url == source_url)
        query = query.order_by(Skill.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_repo_and_name(self, repo: str, skill_name: str) -> list[Skill]:
        pattern_with_version = f"{repo}:{skill_name}:%"
        pattern_without_version = f"{repo}:{skill_name}"
        result = await self.session.execute(
            select(Skill)
            .where(
                (Skill.skill_id.like(pattern_with_version)) |
                (Skill.skill_id == pattern_without_version)
            )
            .order_by(Skill.created_at.desc())
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
        query = select(Skill)

        if category:
            query = query.where(Skill.category == category)
        if platform:
            query = query.where(Skill.platform == platform)
        if tags:
            query = query.where(Skill.tags.contains(tags))
        if source:
            query = query.where(Skill.source == source)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.offset(skip).limit(limit).order_by(Skill.created_at.desc())
        result = await self.session.execute(query)
        skills = list(result.scalars().all())

        return skills, total or 0

    async def update(self, skill_id: str, update_data: dict[str, Any]) -> Skill | None:
        update_data["updated_at"] = datetime.utcnow()
        await self.session.execute(
            update(Skill).where(Skill.skill_id == skill_id).values(**update_data)
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
        await self.session.execute(
            update(Skill)
            .where(Skill.skill_id == skill_id)
            .values(download_count=Skill.download_count + 1)
        )
        await self.session.flush()

    async def update_last_indexed(self, skill_id: str) -> None:
        await self.session.execute(
            update(Skill)
            .where(Skill.skill_id == skill_id)
            .values(last_indexed_at=datetime.utcnow())
        )
        await self.session.flush()

    async def update_embedding(self, skill_id: str, embedding: List[float]) -> None:
        await self.session.execute(
            update(Skill)
            .where(Skill.skill_id == skill_id)
            .values(embedding=embedding, last_indexed_at=datetime.utcnow())
        )
        await self.session.flush()
        await self.session.commit()

    async def get_stats(self) -> dict[str, Any]:
        total_result = await self.session.execute(
            select(func.count()).select_from(Skill)
        )
        total_skills = total_result.scalar() or 0

        category_result = await self.session.execute(
            select(Skill.category, func.count())
            .group_by(Skill.category)
            .order_by(func.count().desc())
        )
        categories = [{"name": row[0] or "Other", "count": row[1]} for row in category_result.fetchall()]
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