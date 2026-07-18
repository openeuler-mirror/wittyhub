"""SkillManager: orchestrates skill repo CRUD and discovery."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from skillcrawler.core.category_classifier import DeepSeekCategoryClassifier
from skillcrawler.core.git_operations import GitOperations
from skillcrawler.core.skill_parser import (
    as_optional_str,
    as_optional_str_list,
    derive_skill_source,
    find_scannable_skill_files,
    normalize_clone_url_for_git,
    normalize_git_clone_url,
)
from skillcrawler.core.skill_scanner import SkillScanner
from src.core.config import get_settings
from src.models.orm import SkillVersion
from src.models.repository import SkillRepoRepository, SkillRepository

if TYPE_CHECKING:
    from src.models.orm import SkillRepoModel

_logger = logging.getLogger(__name__)
settings = get_settings()


class SkillRepositoryRequest(BaseModel):
    branch: str | None = None
    url: str | None = None


class SkillDiscoverStatus:
    INIT = 'init'
    DISCOVERING = 'discovering'
    DONE = 'done'
    FAILED = 'failed'


@dataclass(slots=True)
class SkillManager:
    skill_repository: SkillRepository
    skill_repo_repository: SkillRepoRepository
    workspace_base: Path | None = None
    _git_ops: GitOperations = field(init=False, repr=False)
    _scanner: SkillScanner = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.workspace_base is None:
            self.workspace_base = Path(settings.storage.local_path).expanduser().resolve()

        category_classifier: DeepSeekCategoryClassifier | None = None
        try:
            category_classifier = DeepSeekCategoryClassifier()
        except Exception as exc:
            _logger.warning('Failed to initialize category classifier: %s', exc)

        self._git_ops = GitOperations()
        self._scanner = SkillScanner(
            git_ops=self._git_ops,
            skill_repository=self.skill_repository,
            category_classifier=category_classifier,
        )

    # ── Public API ─────────────────────────────────────────────────

    async def list_skill_repositories(self) -> list[SkillRepoModel]:
        return await self.skill_repo_repository.list_skill_repositories()

    async def create_skill_repository(
        self, request: SkillRepositoryRequest
    ) -> SkillRepoModel | None:
        normalized = self._normalize_create_request(request)
        repo_name = self._derive_git_repository_name(normalized)
        existing = await self.skill_repo_repository.get_skill_repository_by_repo_name(repo_name)
        if existing is not None:
            _logger.warning(
                f'Skill repo "{repo_name}" already exists with id "{existing.id}"'
            )
            return None
        source, _ = derive_skill_source(normalized.url)
        return await self.skill_repo_repository.create_skill_repository(
            repo_name=repo_name,
            source=source,
            branch=normalized.branch,
            url=normalized.url,
            local_path=None,
            skill_discover_status=SkillDiscoverStatus.INIT,
        )

    async def delete_skill_repository(self, repository_id: str) -> None:
        stored = await self.get_repository_by_id(repository_id)
        if stored.local_path:
            local_path = Path(stored.local_path)
            if local_path.is_dir():
                try:
                    shutil.rmtree(local_path)
                except Exception as exc:
                    _logger.warning(f'Failed to clean up directory {local_path}: {exc}')
        await self.skill_repo_repository.delete_skill_repository(stored.id)

    async def discover_one_skill_repository(
        self,
        repository_id: str,
        *,
        force: bool = False,
    ) -> SkillRepoModel:
        repository = await self.get_repository_by_id(repository_id)
        if not force and repository.skill_discover_status == SkillDiscoverStatus.DISCOVERING:
            raise ValueError('Skill repo discovery is already in progress')

        await self._set_discovery_status(repository, SkillDiscoverStatus.DISCOVERING)
        try:
            latest_skills, tagged_skills = await self._discover_git_skill_repository_skills(repository)
            unique_skill_count = self._count_unique_skills(latest_skills)
            await self.skill_repository.replace_for_skill_repo(
                repository.id, latest_skills, tagged_skills,
            )
            return await self.skill_repo_repository.update_skill_repository(
                repository.id,
                skill_discover_status=SkillDiscoverStatus.DONE,
                skill_num=unique_skill_count,
            )
        except Exception as exc:
            error_summary = self._git_ops.summarize_exception(exc)
            _logger.warning(
                'Failed to discover skills from skill repo %s (%s): %s',
                repository.id, repository.repo_name, error_summary,
            )
            await self.skill_repo_repository.update_skill_repository(
                repository.id,
                skill_discover_status=SkillDiscoverStatus.FAILED,
                skill_num=repository.skill_num,
            )
            raise ValueError(
                f'Failed to discover skills from skill repo {repository.id}: {error_summary}'
            ) from exc

    async def get_repository_by_id(self, repository_id: str) -> SkillRepoModel:
        repository = await self.skill_repo_repository.get_skill_repository_by_id(repository_id)
        if repository is None:
            raise KeyError(f'Skill repo {repository_id} not found')
        return repository

    # ── Scan: probe repo for SKILL.md, only persist if found ──────

    @staticmethod
    def _has_skill_md(clone_dir: Path) -> bool:
        """Check whether a cloned repo contains at least one scannable skill."""
        return bool(find_scannable_skill_files(clone_dir))

    async def scan_one_skill_repository(
        self,
        request: SkillRepositoryRequest,
    ) -> SkillRepoModel | None:
        """Clone a repo and persist it only when a scannable skill is present.

        Returns ``None`` when no scannable ``SKILL.md`` exists and the repository
        has no persisted record. Existing records are deleted when their clone no
        longer contains a scannable skill.

        Clone and discovery errors propagate to the caller. The clone directory is
        retained for troubleshooting and reuse by a later scan.
        """
        normalized = self._normalize_create_request(request)
        repo_name = self._derive_git_repository_name(normalized)
        clone_dir = self.workspace_base / 'skill-repositories' / repo_name

        # Clone directly to the standard directory
        clone_url = normalize_clone_url_for_git(normalized.url)

        if clone_dir.is_dir() and (clone_dir / '.git').exists():
            _logger.info('Crawl: existing clone found, pulling updates: %s', clone_dir)
            self._git_ops.update_existing_repository(
                clone_dir, clone_url,
                branch=normalized.branch, repo_url=normalized.url,
            )
        else:
            if clone_dir.exists():
                _logger.info('Crawl: removing non-git directory before clone: %s', clone_dir)
                shutil.rmtree(clone_dir)
            _logger.info('Crawl: cloning skill repo: %s', clone_dir)
            clone_dir.mkdir(parents=True, exist_ok=True)
            self._git_ops.clone_repository(
                clone_dir, clone_url,
                branch=normalized.branch, repo_url=normalized.url,
            )

        # Check for SKILL.md
        if not self._has_skill_md(clone_dir):
            _logger.info(
                'Crawl: no scannable SKILL.md found in %s; retaining clone at %s',
                repo_name,
                clone_dir,
            )
            repository = await self.skill_repo_repository.get_skill_repository_by_repo_name(repo_name)
            if repository is not None:
                setattr(repository, "_removed_existing", True)
                await self.skill_repo_repository.delete_skill_repository(repository.id)
                return repository
            return None

        # Has skill — create in DB if needed, then always discover so skills tables stay in sync.
        created_new = False
        repository = await self.create_skill_repository(normalized)
        if repository is None:
            _logger.info('Crawl: skill repo already exists in DB: %s', repo_name)
            repository = await self.skill_repo_repository.get_skill_repository_by_repo_name(repo_name)
            if repository is None:
                raise ValueError(f'Skill repo {repo_name} was expected in DB but not found')
            current_commit_id = self._git_ops.get_repository_head_commit_id(clone_dir)
            existing_commit_ids = await self.skill_repository.get_commit_ids_for_skill_repo(repository.id)
            if current_commit_id and existing_commit_ids == {current_commit_id}:
                setattr(repository, "_unchanged", True)
                return repository
        else:
            created_new = True

        # Discover skills (reuse the clone we already have)
        await self.discover_one_skill_repository(str(repository.id))
        refreshed = await self.get_repository_by_id(repository.id)
        setattr(refreshed, "_created_new", created_new)
        return refreshed

    # ── Internal: discovery orchestration ──────────────────────────

    async def _discover_git_skill_repository_skills(
        self,
        repo: SkillRepoModel,
    ) -> tuple[list[SkillVersion], list[SkillVersion]]:
        clone_url = normalize_clone_url_for_git(repo.url)
        repo_name = self._derive_git_repository_name(
            SkillRepositoryRequest(url=repo.url, branch=repo.branch)
        )

        clone_dir = self.workspace_base / 'skill-repositories' / f'{repo_name}'
        if clone_dir.is_dir() and (clone_dir / '.git').exists():
            _logger.info('Using existing skill repo, fetching updates: %s', clone_dir)
            self._git_ops.update_existing_repository(clone_dir, clone_url, branch=repo.branch, repo_url=repo.url)
        else:
            if clone_dir.exists():
                _logger.info('Removing non-git skill repo directory before clone: %s', clone_dir)
                shutil.rmtree(clone_dir)
            _logger.info('Repository not found locally, cloning: %s', clone_dir)
            clone_dir.mkdir(parents=True, exist_ok=True)
            self._git_ops.clone_repository(clone_dir, clone_url, branch=repo.branch, repo_url=repo.url)

        repository_git_metadata = self._git_ops.collect_repository_git_metadata(
            clone_dir, clone_url, repo.url,
        )
        version_snapshots = GitOperations.build_repository_version_snapshots(
            repository_git_metadata, as_optional_str, as_optional_str_list,
        )
        tag_snapshots = [
            snapshot
            for snapshot in version_snapshots
            if as_optional_str(snapshot.get('version_source')) == 'tag'
        ]

        if repo.branch is None:
            detected_branch = self._git_ops.get_cloned_repo_branch(clone_dir)
            if detected_branch:
                repo = await self.skill_repo_repository.update_skill_repository(
                    repo.id, branch=detected_branch,
                )
        repo = await self.skill_repo_repository.update_skill_repository(
            repo.id, local_path=str(clone_dir),
        )
        return await self._scanner.scan_skill_repository_root(
            repo=repo,
            repo_root=clone_dir,
            repository_git_metadata=repository_git_metadata,
            version_snapshots=tag_snapshots or None,
        )

    # ── Internal: helpers ──────────────────────────────────────────

    @staticmethod
    def _count_unique_skills(skills: list[SkillVersion]) -> int:
        return len(
            {
                str(skill.skill_id).strip()
                for skill in skills
                if getattr(skill, 'skill_id', None)
            }
        )

    async def _set_discovery_status(
        self,
        repo: SkillRepoModel,
        status: str,
    ) -> None:
        await self.skill_repo_repository.update_skill_repository(
            repo.id, skill_discover_status=status, skill_num=repo.skill_num,
        )

    @staticmethod
    def _normalize_create_request(
        request: SkillRepositoryRequest,
    ) -> SkillRepositoryRequest:
        branch = request.branch.strip() if request.branch is not None else None
        url = (
            normalize_git_clone_url(request.url.strip())
            if request.url is not None
            else None
        )
        if not url:
            raise ValueError('git skill repos require url')
        return SkillRepositoryRequest(branch=branch, url=url)

    @staticmethod
    def _derive_git_repository_name(request: SkillRepositoryRequest) -> str:
        name = request.url
        for prefix in ('https://', 'http://'):
            if name.startswith(prefix):
                name = name[len(prefix):]
        name = name.removesuffix('.git')
        name = name.replace('/', '_')
        return name
