import re
import uuid
from datetime import datetime, timezone
from typing import Any, List

from sqlalchemy import case, delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.orm import (
    Agent,
    AgentVersion,
    SecurityAudit,
    DownloadHistory,
    SecurityAudit,
    Skill,
    SkillRepoModel,
    SkillVersion,
)


class SkillRepoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _coerce_repository_id(self, repository_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(repository_id, uuid.UUID):
            return repository_id
        return uuid.UUID(str(repository_id))

    async def list_skill_repositories(self) -> list[SkillRepoModel]:
        result = await self.session.execute(
            select(SkillRepoModel).order_by(SkillRepoModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_skill_repository(
        self,
        *,
        repo_name: str,
        source: str,
        branch: str | None,
        url: str | None,
        local_path: str | None,
        skill_discover_status: str,
    ) -> SkillRepoModel:
        repository = SkillRepoModel(
            repo_name=repo_name,
            source=source,
            branch=branch,
            url=url,
            local_path=local_path,
            skill_discover_status=skill_discover_status,
            skill_num=0,
        )
        self.session.add(repository)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(repository)
        return repository

    async def update_skill_repository(
        self,
        repository_id: str | uuid.UUID,
        *,
        source: str | None = None,
        branch: str | None = None,
        url: str | None = None,
        local_path: str | None = None,
        skill_discover_status: str | None = None,
        skill_num: int | None = None,
    ) -> SkillRepoModel:
        values: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if source is not None:
            values["source"] = source
        if branch is not None:
            values["branch"] = branch
        if url is not None:
            values["url"] = url
        if local_path is not None:
            values["local_path"] = local_path
        if skill_discover_status is not None:
            values["skill_discover_status"] = skill_discover_status
        if skill_num is not None:
            values["skill_num"] = skill_num

        await self.session.execute(
            update(SkillRepoModel)
            .where(SkillRepoModel.id == self._coerce_repository_id(repository_id))
            .values(**values)
        )
        await self.session.flush()
        await self.session.commit()

        repository = await self.get_skill_repository_by_id(repository_id)
        if repository is None:
            raise ValueError(f"Skill repo not found: {repository_id}")
        return repository

    async def delete_skill_repository(self, repository_id: str | uuid.UUID) -> None:
        await self.session.execute(
            delete(SkillRepoModel).where(
                SkillRepoModel.id == self._coerce_repository_id(repository_id)
            )
        )
        await self.session.flush()
        await self.session.commit()

    async def get_skill_repository_by_id(
        self,
        repository_id: str | uuid.UUID,
    ) -> SkillRepoModel | None:
        result = await self.session.execute(
            select(SkillRepoModel).where(
                SkillRepoModel.id == self._coerce_repository_id(repository_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_skill_repository_by_repo_name(
        self,
        repo_name: str,
    ) -> SkillRepoModel | None:
        result = await self.session.execute(
            select(SkillRepoModel).where(
                SkillRepoModel.repo_name == repo_name
            )
        )
        return result.scalar_one_or_none()


class SkillRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _version_sort_key(
        self, skill: Skill | SkillVersion
    ) -> tuple[int, tuple[int, ...], int, str, datetime, datetime]:
        version = (skill.version or "").strip()
        if version.lower() == "latest":
            return (2, tuple(), 0, "", skill.updated_at, skill.created_at)
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

    def _dedupe_skills(self, skills: list[Skill | SkillVersion]) -> list[Skill | SkillVersion]:
        grouped: dict[str, Skill | SkillVersion] = {}

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
        skill_model,
        *,
        category: str | None = None,
        platform: str | None = None,
        tags: list[str] | None = None,
        source: str | None = None,
    ):
        if category:
            query = query.where(skill_model.category == category)
        if platform:
            query = query.where(skill_model.platform == platform)
        if tags:
            query = query.where(skill_model.tags.contains(tags))
        if source:
            query = query.where(skill_model.source == source)
        return query

    def _latest_unique_skills_subquery(self):
        return (
            select(Skill)
            .order_by(desc(Skill.updated_at), desc(Skill.created_at))
            .subquery()
        )

    def _build_summary_skill(
        self,
        representative: SkillVersion,
        *,
        download_count: int = 0,
    ) -> Skill:
        return Skill(
            skill_repo_id=representative.skill_repo_id,
            skill_id=representative.skill_id,
            name=representative.name,
            description=representative.description,
            version=representative.version,
            commit_id=representative.commit_id,
            author=representative.author,
            source=representative.source,
            source_url=representative.source_url,
            category=representative.category,
            tags=representative.tags,
            platform=representative.platform,
            extra_metadata=representative.extra_metadata,
            content=representative.content,
            security_score=representative.security_score,
            download_count=download_count,
            rating=representative.rating,
            created_at=representative.created_at,
            updated_at=representative.updated_at,
            last_indexed_at=representative.last_indexed_at,
            embedding=representative.embedding,
        )

    async def create(self, skill_data: dict[str, Any]) -> Skill:
        skill = Skill(**skill_data)
        self.session.add(skill)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(skill)
        return skill

    def _select_skill_by_version(
        self, skills: list[SkillVersion], version: str | None = None
    ) -> SkillVersion | None:
        if not skills:
            return None
        if len(skills) == 1:
            return skills[0]

        target_version = (version or "latest").strip()
        if target_version:
            for skill in skills:
                if (skill.version or "").strip() == target_version:
                    return skill

        return skills[0]

    async def get_by_skill_id(self, skill_id: str) -> Skill | None:
        result = await self.session.execute(
            select(Skill).where(Skill.skill_id == skill_id)
        )
        return result.scalar_one_or_none()

    async def get_with_repository_by_skill_id(self, skill_id: str) -> Skill | None:
        result = await self.session.execute(
            select(Skill)
            .options(selectinload(Skill.skill_repo))
            .where(Skill.skill_id == skill_id)
        )
        return result.scalar_one_or_none()

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

    async def get_commit_ids_for_skill_repo(self, skill_repo_id: uuid.UUID) -> set[str]:
        result = await self.session.execute(
            select(Skill.commit_id)
            .where(
                Skill.skill_repo_id == skill_repo_id,
                Skill.commit_id.is_not(None),
                Skill.commit_id != "",
            )
        )
        return {commit_id for commit_id in result.scalars().all() if commit_id}

    async def replace_for_skill_repo(
        self,
        skill_repo_id: uuid.UUID,
        latest_skills: list[SkillVersion],
        tagged_skills: list[SkillVersion],
    ) -> tuple[list[SkillVersion], list[SkillVersion]]:
        existing_result = await self.session.execute(
            select(Skill.skill_id, Skill.download_count)
            .where(Skill.skill_repo_id == skill_repo_id)
        )
        existing_download_counts = {
            skill_id: download_count
            for skill_id, download_count in existing_result.all()
        }

        summary_skills: list[Skill] = []
        for skill in latest_skills:
            skill.skill_repo_id = skill_repo_id
            summary_skills.append(
                self._build_summary_skill(
                    skill,
                    download_count=existing_download_counts.get(skill.skill_id, 0),
                )
            )
        for skill in tagged_skills:
            skill.skill_repo_id = skill_repo_id

        await self.session.execute(
            delete(SkillVersion).where(SkillVersion.skill_repo_id == skill_repo_id)
        )
        await self.session.execute(
            delete(Skill).where(Skill.skill_repo_id == skill_repo_id)
        )
        self.session.add_all(summary_skills)
        self.session.add_all(tagged_skills)
        await self.session.flush()
        await self.session.commit()
        return latest_skills, tagged_skills

    async def get_versions_by_base_skill(self, source_url: str | None, skill_id: str) -> list[SkillVersion]:
        query = select(SkillVersion)
        query = query.where(SkillVersion.skill_id == skill_id)
        if source_url:
            query = query.where(SkillVersion.source_url == source_url)
        query = query.order_by(desc(SkillVersion.updated_at), desc(SkillVersion.created_at))
        result = await self.session.execute(query)
        skills = list(result.scalars().all())
        return sorted(skills, key=self._version_sort_key, reverse=True)

    async def get_by_repo_and_name(self, repo: str, skill_name: str) -> list[SkillVersion]:
        public_skill_id = f"{repo}/{skill_name}"
        result = await self.session.execute(
            select(SkillVersion)
            .where(SkillVersion.skill_id == public_skill_id)
            .order_by(desc(SkillVersion.updated_at), desc(SkillVersion.created_at))
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
        sort_by: str = "updated_at",
    ) -> tuple[list[Skill], int]:
        filtered_query = self._apply_skill_filters(
            select(Skill),
            Skill,
            category=category,
            platform=platform,
            tags=tags,
            source=source,
        )

        count_query = self._apply_skill_filters(
            select(func.count()),
            Skill,
            category=category,
            platform=platform,
            tags=tags,
            source=source,
        )
        total = await self.session.scalar(count_query)

        if sort_by == "download_count":
            order_by = [desc(Skill.download_count), desc(Skill.updated_at), desc(Skill.created_at)]
        else:
            order_by = [desc(Skill.updated_at), desc(Skill.created_at)]

        query = (
            filtered_query
            .order_by(*order_by)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        skills = list(result.scalars().all())

        return skills, total or 0

    async def update(self, skill_id: str, update_data: dict[str, Any]) -> Skill | None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return None
        update_data["updated_at"] = datetime.now(timezone.utc)
        await self.session.execute(
            update(Skill).where(Skill.id == existing.id).values(**update_data)
        )
        await self.session.flush()
        return await self.get_by_skill_id(skill_id)

    async def delete(self, skill_id: str) -> bool:
        version_result = await self.session.execute(
            delete(SkillVersion).where(SkillVersion.skill_id == skill_id)
        )
        summary_result = await self.session.execute(
            delete(Skill).where(Skill.skill_id == skill_id)
        )
        await self.session.flush()
        return (version_result.rowcount or 0) > 0 or (summary_result.rowcount or 0) > 0

    async def increment_download(self, skill_id: str) -> bool:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return False
        await self.session.execute(
            update(Skill)
            .where(Skill.id == existing.id)
            .values(download_count=Skill.download_count + 1)
        )
        await self.session.flush()
        return True

    async def update_last_indexed(self, skill_id: str) -> None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return
        await self.session.execute(
            update(Skill)
            .where(Skill.id == existing.id)
            .values(last_indexed_at=datetime.now(timezone.utc))
        )
        await self.session.flush()

    async def update_embedding(self, skill_id: str, embedding: List[float]) -> None:
        existing = await self.get_by_skill_id(skill_id)
        if existing is None:
            return
        await self.session.execute(
            update(Skill)
            .where(Skill.id == existing.id)
            .values(embedding=embedding, last_indexed_at=datetime.now(timezone.utc))
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
        tags: list[str] | None = None,
    ) -> tuple[list[Agent], int]:
        query = select(Agent)

        if category:
            query = query.where(Agent.category == category)
        if tags:
            query = query.where(Agent.tags.contains(tags))

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.offset(skip).limit(limit).order_by(Agent.created_at.desc())
        result = await self.session.execute(query)
        agents = list(result.scalars().all())

        return agents, total or 0

    async def get_versions(self, agent_id: uuid.UUID) -> List[AgentVersion]:
        result = await self.session.execute(
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.released_at.desc())
        )
        return list(result.scalars().all())

    async def create_version(self, version_data: dict[str, Any]) -> AgentVersion:
        version = AgentVersion(**version_data)
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(version)
        return version

    async def increment_download(self, agent_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Agent)
            .where(Agent.id == agent_id)
            .values(download_count=Agent.download_count + 1)
        )
        await self.session.flush()

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
