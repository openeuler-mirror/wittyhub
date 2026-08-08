"""SkillManager: orchestrates skill repo CRUD and discovery."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from skillcrawler.core.category_classifier import DeepSeekCategoryClassifier
from skillcrawler.core.git_operations import GitOperations
from skillcrawler.core.openeuler_sig import build_openeuler_repo_sig_mapping
from skillcrawler.core.skill_parser import (
    as_optional_str,
    as_optional_str_list,
    derive_skill_source,
    extract_owner_repo,
    find_scannable_skill_files,
    normalize_clone_url_for_git,
    normalize_git_clone_url,
)
from skillcrawler.core.skill_scanner import SkillScanner
from src.core.config import get_settings
from src.models.orm import Skill, SkillVersion
from src.models.repository import (
    SecurityAuditRepository,
    SkillRepoRepository,
    SkillRepository,
)
from src.security.detector import SecurityDetector

if TYPE_CHECKING:
    from src.models.orm import SkillRepoModel

_logger = logging.getLogger(__name__)
settings = get_settings()


class SkillRepositoryRequest(BaseModel):
    branch: str | None = None
    url: str | None = None
    platform: str | None = None


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
    _openeuler_sig_by_repo_name: dict[str, str] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.workspace_base is None:
            self.workspace_base = Path(settings.storage.local_path).expanduser().resolve()

        category_classifier: DeepSeekCategoryClassifier | None = None
        security_detector: SecurityDetector | None = None
        try:
            category_classifier = DeepSeekCategoryClassifier()
        except Exception as exc:
            _logger.warning('Failed to initialize category classifier: %s', exc)

        try:
            detector = SecurityDetector()
            if detector.has_skillspector:
                security_detector = detector
            else:
                _logger.info('SecurityDetector: skillspector not configured')
        except Exception as exc:
            _logger.warning('Failed to initialize security detector: %s', exc)

        self._git_ops = GitOperations()
        self._scanner = SkillScanner(
            git_ops=self._git_ops,
            skill_repository=self.skill_repository,
            category_classifier=category_classifier,
            security_detector=security_detector,
            security_async_mode=True,
        )

    # ── Public API ─────────────────────────────────────────────────

    async def list_skill_repositories(self) -> list[SkillRepoModel]:
        return await self.skill_repo_repository.list_skill_repositories()

    async def rollback(self) -> None:
        """Restore the shared database session after a failed repository scan."""
        await self.skill_repository.session.rollback()

    async def create_skill_repository(
        self, request: SkillRepositoryRequest
    ) -> SkillRepoModel | None:
        normalized = self._normalize_repository_request(request)
        repo_name = self._derive_repo_name(normalized)
        existing = await self.skill_repo_repository.get_skill_repository_by_repo_name(repo_name)
        if existing is not None:
            _logger.info(
                f'Skill repo "{repo_name}" already exists with id "{existing.id}", skipping creation'
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
            platform=normalized.platform,
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

    async def discover_skills_from_single_existing_repository(
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
            request = SkillRepositoryRequest(
                url=repository.url,
                branch=repository.branch,
                platform=repository.platform,
            )
            repo_name = self._derive_repo_name(request)
            clone_dir = self._local_repository_path(repo_name)
            self._sync_git_repository(
                clone_dir=clone_dir,
                clone_url=normalize_clone_url_for_git(repository.url),
                branch=repository.branch,
                repo_url=repository.url,
            )
            return await self._discover_and_store_skills(
                repository,
                clone_dir=clone_dir,
                repo_name=repo_name,
            )
        except Exception as exc:
            error_summary = self._git_ops.summarize_exception(exc)
            _logger.warning(
                'Failed to discover skills from skill repo %s (%s): %s',
                repository.id, repository.repo_name, error_summary,
            )
            await self.rollback()
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

    # ── Discover from configured repo list ────────────────────────

    @staticmethod
    def _has_skill_md(clone_dir: Path) -> bool:
        """Check whether a cloned repo contains at least one scannable skill."""
        return bool(find_scannable_skill_files(clone_dir))

    async def discover_configured_skill_repository(
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
        normalized = self._normalize_repository_request(request)
        repo_name = self._derive_repo_name(normalized)
        clone_dir = self._local_repository_path(repo_name)
        self._sync_git_repository(
            clone_dir=clone_dir,
            clone_url=normalize_clone_url_for_git(normalized.url),
            branch=normalized.branch,
            repo_url=normalized.url,
        )

        if not self._has_skill_md(clone_dir):
            _logger.info(
                'Discover: no scannable SKILL.md found in %s; retaining clone at %s',
                repo_name,
                clone_dir,
            )
            repository = await self.skill_repo_repository.get_skill_repository_by_repo_name(repo_name)
            if repository is not None:
                setattr(repository, "_removed_existing", True)
                await self.skill_repo_repository.delete_skill_repository(repository.id)
                return repository
            return None

        repository, created_new = await self._get_or_create_skill_repository(
            normalized,
            repo_name,
        )
        if not created_new and self._is_commit_unchanged(repository, clone_dir):
            candidates, triggered = await self._retry_unscored_security_audits(repository)
            if candidates:
                setattr(repository, "_security_retry_candidates", candidates)
                setattr(repository, "_security_retriggered", triggered)
                return repository
            setattr(repository, "_unchanged", True)
            return repository

        await self._set_discovery_status(repository, SkillDiscoverStatus.DISCOVERING)
        try:
            refreshed = await self._discover_and_store_skills(
                repository,
                clone_dir=clone_dir,
                repo_name=repo_name,
            )
        except Exception as exc:
            error_summary = self._git_ops.summarize_exception(exc)
            _logger.warning(
                'Failed to discover skills from skill repo %s (%s): %s',
                repository.id, repository.repo_name, error_summary,
            )
            await self.rollback()
            await self.skill_repo_repository.update_skill_repository(
                repository.id,
                skill_discover_status=SkillDiscoverStatus.FAILED,
                skill_num=repository.skill_num,
            )
            raise ValueError(
                f'Failed to discover skills from skill repo {repository.id}: {error_summary}'
            ) from exc
        setattr(refreshed, "_created_new", created_new)
        return refreshed

    # ── Internal: discovery orchestration ──────────────────────────

    async def _discover_and_store_skills(
        self,
        repo: SkillRepoModel,
        *,
        clone_dir: Path,
        repo_name: str,
    ) -> SkillRepoModel:
        author = self._resolve_skill_author(repo.platform, repo_name)
        latest_skills, tagged_skills = await self._discover_skills(
            repo,
            clone_dir=clone_dir,
            author=author,
        )
        unique_skill_count = self._count_unique_skills(latest_skills)
        repository_commit_id = self._git_ops.get_repository_head_commit_id(clone_dir)
        await self.skill_repository.store_skills_and_versions(
            repo.id,
            latest_skills,
            tagged_skills,
            commit=False,
        )
        await self._store_to_security_audits(
            latest_skills,
            tagged_skills,
        )
        return await self.skill_repo_repository.update_skill_repository(
            repo.id,
            repository_commit_id=repository_commit_id,
            skill_discover_status=SkillDiscoverStatus.DONE,
            skill_num=unique_skill_count,
        )

    async def _discover_skills(
        self,
        repo: SkillRepoModel,
        *,
        clone_dir: Path,
        author: str | None,
    ) -> tuple[list[Skill], list[SkillVersion]]:
        clone_url = normalize_clone_url_for_git(repo.url)
        self._git_ops.ensure_full_history(clone_dir, clone_url, repo.url)
        repository_git_metadata = self._git_ops.collect_repository_git_metadata(
            clone_dir,
            clone_url,
            repo.url,
        )
        version_snapshots = GitOperations.build_repository_version_snapshots(
            repository_git_metadata, as_optional_str, as_optional_str_list,
        )

        detected_branch: str | None = None
        if repo.branch is None:
            detected_branch = self._git_ops.get_cloned_repo_branch(clone_dir)
        repo = await self.skill_repo_repository.update_skill_repository(
            repo.id,
            branch=detected_branch,
            local_path=str(clone_dir),
            commit=False,
        )
        return await self._scanner.start_scan(
            repo=repo,
            repo_root=clone_dir,
            repository_git_metadata=repository_git_metadata,
            version_snapshots=version_snapshots or None,
            author=author,
        )

    async def _store_to_security_audits(
        self,
        latest_skills: list[Skill],
        tagged_skills: list[SkillVersion],
    ) -> None:
        """Create ``SecurityAudit`` records for async-triggered skills."""
        records: list[Skill | SkillVersion] = [*latest_skills, *tagged_skills]
        pending = [record for record in records if self._has_new_security_audit(record)]

        if not pending:
            return

        audit_repo = SecurityAuditRepository(self.skill_repository.session)
        upserted = 0
        for resource_id, version, commit_id, security_audit in pending:
            await audit_repo.upsert_by_resource(
                resource_type='skill',
                resource_id=resource_id,
                audit_data={
                    'resource_type': 'skill',
                    'resource_id': resource_id,
                    'version': version,
                    'commit_id': commit_id,
                    'audit_type': 'skillspector',
                    'risk_level': 'unknown',
                    'risk_signals': [],
                    'details': dict(security_audit),
                },
            )
            upserted += 1

        _logger.info(
            'Upserted %d/%d SecurityAudit records',
            upserted, len(pending),
        )

    @staticmethod
    def _should_store_security_audit(record: Skill | SkillVersion) -> bool:
        """Return whether this scan triggered a new audit for the record."""
        return bool(getattr(record, '_security_audit_triggered', False))

    async def _retry_unscored_security_audits(
        self,
        repo: SkillRepoModel,
    ) -> tuple[int, int]:
        """Re-trigger audits for unchanged records that still have no score."""
        if not settings.security.enable_audit:
            return 0, 0

        latest_skills, tagged_skills = await self.skill_repository.list_unscored_by_skill_repo(
            repo.id,
        )
        records: list[Skill | SkillVersion] = [*latest_skills, *tagged_skills]
        if not records:
            return 0, 0

        detector = self._scanner.security_detector
        if detector is None or not detector.has_skillspector:
            _logger.warning(
                'Security retry skipped for repo %s: %d unscored records but '
                'Skillspector is unavailable',
                repo.repo_name,
                len(records),
            )
            return len(records), 0

        audit_repo = SecurityAuditRepository(self.skill_repository.session)
        triggered = 0
        for record in records:
            relative_path = self._relative_skill_path(repo, record)
            report = await self._scanner.audit_existing_skill(
                repo=repo,
                relative_path=relative_path,
                commit_id=record.commit_id,
                skill_id=record.skill_id,
            )
            details = dict(report.details) if report is not None else {}
            if details.get('skillspector_build_number') is None:
                _logger.warning(
                    'Security retry failed to trigger: skill_id=%s version=%s',
                    record.skill_id,
                    record.version or '-',
                )
                continue

            metadata = dict(record.extra_metadata or {})
            metadata['security_audit'] = details
            record.extra_metadata = metadata
            await audit_repo.upsert_by_resource(
                resource_type='skill',
                resource_id=record.id,
                audit_data={
                    'resource_type': 'skill',
                    'resource_id': record.id,
                    'version': record.version,
                    'commit_id': record.commit_id,
                    'audit_type': 'skillspector',
                    'risk_level': 'unknown',
                    'risk_signals': [],
                    'details': details,
                    'audited_at': datetime.now(timezone.utc),
                },
            )
            triggered += 1

        await self.skill_repository.session.commit()
        _logger.info(
            'Security retry for unchanged repo %s: triggered=%d candidates=%d',
            repo.repo_name,
            triggered,
            len(records),
        )
        return len(records), triggered

    @staticmethod
    def _relative_skill_path(
        repo: SkillRepoModel,
        record: Skill | SkillVersion,
    ) -> str:
        refs = []
        if record.commit_id:
            refs.append(record.commit_id)
        if isinstance(record, SkillVersion) and record.version:
            refs.append(record.version)
        if repo.branch:
            refs.append(repo.branch)
        refs.extend(['HEAD', 'master', 'main'])

        for ref in dict.fromkeys(refs):
            marker = f'/blob/{ref}/'
            if marker in record.source_url:
                relative_path = record.source_url.split(marker, 1)[1]
                if relative_path.endswith('SKILL.md'):
                    return relative_path

        owner_repo = extract_owner_repo(repo.url)
        prefix = f'{repo.source}/{owner_repo}/'
        skill_path = record.skill_id.removeprefix(prefix)
        repository_name = owner_repo.rsplit('/', 1)[-1]
        if skill_path == repository_name:
            return 'SKILL.md'
        return f'{skill_path.strip("/")}/SKILL.md'

    # ── Internal: helpers ──────────────────────────────────────────

    def _local_repository_path(self, repo_name: str) -> Path:
        return self.workspace_base / 'skill-repositories' / repo_name

    def _sync_git_repository(
        self,
        *,
        clone_dir: Path,
        clone_url: str,
        branch: str | None,
        repo_url: str | None,
    ) -> None:
        if clone_dir.is_dir() and (clone_dir / '.git').exists():
            _logger.info('Discover: existing clone found, pulling updates: %s', clone_dir)
            self._git_ops.update_existing_repository(
                clone_dir, clone_url,
                branch=branch, repo_url=repo_url,
            )
            return

        if clone_dir.exists():
            _logger.info('Discover: removing non-git directory before clone: %s', clone_dir)
            shutil.rmtree(clone_dir)
        _logger.info('Discover: cloning skill repo: %s', clone_dir)
        clone_dir.mkdir(parents=True, exist_ok=True)
        self._git_ops.clone_repository(
            clone_dir, clone_url,
            branch=branch, repo_url=repo_url,
        )

    async def _get_or_create_skill_repository(
        self,
        request: SkillRepositoryRequest,
        repo_name: str,
    ) -> tuple[SkillRepoModel, bool]:
        repository = await self.create_skill_repository(request)
        if repository is not None:
            return repository, True

        _logger.info('Discover: skill repo already exists in DB: %s', repo_name)
        repository = await self.skill_repo_repository.get_skill_repository_by_repo_name(repo_name)
        if repository is None:
            raise ValueError(f'Skill repo {repo_name} was expected in DB but not found')
        return repository, False

    def _is_commit_unchanged(
        self,
        repo: SkillRepoModel,
        clone_dir: Path,
    ) -> bool:
        current_commit_id = self._git_ops.get_repository_head_commit_id(clone_dir)
        stored_commit_id = as_optional_str(getattr(repo, 'repository_commit_id', None))
        return bool(current_commit_id and stored_commit_id == current_commit_id)

    def _resolve_skill_author(self, platform: str | None, repo_name: str) -> str | None:
        if platform == 'openeuler':
            return self._get_openeuler_sig_name(repo_name)
        return None

    @staticmethod
    def _count_unique_skills(skills: list[Skill]) -> int:
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
    def _normalize_repository_request(
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
        platform = request.platform.strip() if request.platform is not None else None
        return SkillRepositoryRequest(branch=branch, url=url, platform=platform)

    @staticmethod
    def _derive_repo_name(request: SkillRepositoryRequest) -> str:
        name = request.url
        for prefix in ('https://', 'http://'):
            if name.startswith(prefix):
                name = name[len(prefix):]
        name = name.removesuffix('.git')
        name = name.replace('/', '_')
        return name

    def _get_openeuler_sig_name(self, repo_name: str) -> str | None:
        if self._openeuler_sig_by_repo_name is None:
            try:
                self._openeuler_sig_by_repo_name = build_openeuler_repo_sig_mapping()
                _logger.info(
                    "Loaded openEuler SIG mapping: repos=%s",
                    len(self._openeuler_sig_by_repo_name),
                )
            except Exception as exc:
                _logger.warning(
                    "Failed to load openEuler SIG mapping; continuing without SIG author: %s",
                    self._git_ops.summarize_exception(exc),
                )
                self._openeuler_sig_by_repo_name = {}
        return self._openeuler_sig_by_repo_name.get(repo_name)
