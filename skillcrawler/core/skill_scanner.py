"""Skill scanning logic: version scan, current state scan, and record building."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skillcrawler.core.category_classifier import DeepSeekCategoryClassifier
from skillcrawler.core.git_operations import GitOperations
from src.security.detector import SecurityDetector, SecurityReport
from skillcrawler.core.skill_parser import (
    as_optional_str,
    as_optional_str_list,
    build_public_skill_id,
    build_skill_md_url,
    derive_repository_skill_name,
    derive_skill_source,
    parse_skill_frontmatter_text,
    should_skip_relative_path,
)
from src.models.orm import Skill, SkillVersion
from src.models.repository import SkillRepository

if TYPE_CHECKING:
    from src.models.orm import SkillRepoModel

_logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SecurityResolution:
    risk_score: int | None
    audit_details: dict[str, Any] | None
    audit_triggered: bool


class SkillScanner:
    """Scans repositories for skills and builds skill records."""

    def __init__(
        self,
        git_ops: GitOperations,
        skill_repository: SkillRepository,
        category_classifier: DeepSeekCategoryClassifier | None = None,
        security_detector: SecurityDetector | None = None,
        security_async_mode: bool = False,
    ) -> None:
        self.git_ops = git_ops
        self.skill_repository = skill_repository
        self.category_classifier = category_classifier
        self.security_detector = security_detector
        self.security_async_mode = security_async_mode

    async def start_scan(
        self,
        repo: SkillRepoModel,
        repo_root: Path,
        repository_git_metadata: dict[str, Any] | None = None,
        version_snapshots: list[dict[str, str]] | None = None,
        author: str | None = None,
        skill_paths: list[str] | None = None,
    ) -> tuple[list[Skill], list[SkillVersion]]:
        if not repo_root.exists():
            raise ValueError(
                f'Repository root does not exist for repository {repo.id}: {repo_root}'
            )

        discovery_started_at = time.perf_counter()
        if skill_paths is None:
            skill_paths = self.git_ops.list_skill_paths_for_ref(
                repo_root, 'HEAD', should_skip_relative_path,
            )
        _logger.debug(
            'Skill file discovery timing: repo=%s files=%d elapsed=%.3fs',
            getattr(repo, 'repo_name', None) or repo.url,
            len(skill_paths),
            time.perf_counter() - discovery_started_at,
        )

        repository_git_metadata = repository_git_metadata or {}
        repository_commit_id = as_optional_str(repository_git_metadata.get('commit_id'))
        repository_latest_tags = as_optional_str_list(repository_git_metadata.get('latest_tags')) or []
        existing_skills, existing_versions = await self.skill_repository.load_scan_records(repo.id)
        category_cache = {
            skill_id: skill.category
            for skill_id, skill in existing_skills.items()
            if getattr(skill, 'category', None)
        }
        latest_skills = await self._scan_latest_skills(
            repo=repo,
            repo_root=repo_root,
            skill_paths=skill_paths,
            repository_commit_id=repository_commit_id,
            repository_latest_tags=repository_latest_tags,
            author=author,
            existing_skills=existing_skills,
            category_cache=category_cache,
        )

        tagged_skills: list[SkillVersion] = []
        if version_snapshots:
            tagged_skills = await self._scan_tagged_skills(
                repo=repo,
                repo_root=repo_root,
                version_snapshots=version_snapshots,
                repository_commit_id=repository_commit_id,
                repository_latest_tags=repository_latest_tags,
                author=author,
                existing_versions=existing_versions,
                category_cache=category_cache,
            )

        return latest_skills, tagged_skills

    async def _scan_latest_skills(
        self,
        repo: SkillRepoModel,
        repo_root: Path,
        skill_paths: list[str],
        repository_commit_id: str | None,
        repository_latest_tags: list[str],
        author: str | None,
        existing_skills: dict[str, Skill],
        category_cache: dict[str, str | None],
    ) -> list[Skill]:
        discovered: list[Skill] = []
        # skill_id is derived from the SKILL.md directory name, so different
        # paths with the same directory name collide.  Keep the first one so
        # every returned record maps to a persisted row (records dropped here
        # would never receive a database id).
        seen_skill_ids: set[str] = set()
        tree_hashes = self.git_ops.get_skill_tree_hashes(
            repo_root, skill_paths, ref='HEAD',
        )
        for relative_path in skill_paths:
            scan_started_at = time.perf_counter()
            virtual_skill_file = repo_root / relative_path
            skill_id = build_public_skill_id(repo, repo_root, virtual_skill_file)
            if skill_id in seen_skill_ids:
                _logger.warning(
                    'Duplicate skill_id from different paths, keeping first '
                    'occurrence: skill_id=%s skipped_path=%s',
                    skill_id, relative_path,
                )
                continue
            seen_skill_ids.add(skill_id)
            metadata_content = self.git_ops.load_skill_frontmatter_from_git_ref(
                repo_root, 'HEAD', relative_path, parse_skill_frontmatter_text,
            )
            if metadata_content is None:
                continue
            input_elapsed = time.perf_counter() - scan_started_at
            tree_hash = tree_hashes.get(relative_path)
            skill = await self._build_skill_record(
                repo=repo,
                skill_file=virtual_skill_file,
                relative_path=relative_path,
                metadata_content=metadata_content,
                ref=None,
                version='latest',
                commit_id=repository_commit_id,
                tree_hash=tree_hash,
                skill_id=skill_id,
                repository_latest_tags=repository_latest_tags,
                category_cache=category_cache,
                version_source='branch_head',
                author=author,
                scan_started_at=scan_started_at,
                input_elapsed=input_elapsed,
                existing_record=existing_skills.get(skill_id),
            )
            _logger.debug(
                'Discovered skill: skill_id=%s version=%s source=%s',
                skill.skill_id, skill.version or '-', relative_path,
            )
            discovered.append(skill)
        return discovered

    async def _scan_tagged_skills(
        self,
        repo: SkillRepoModel,
        repo_root: Path,
        version_snapshots: list[dict[str, str]],
        repository_commit_id: str | None,
        repository_latest_tags: list[str],
        author: str | None,
        existing_versions: dict[tuple[str, str | None], SkillVersion],
        category_cache: dict[str, str | None],
    ) -> list[SkillVersion]:
        discovered: list[SkillVersion] = []
        seen_versions: set[tuple[str, str]] = set()
        seen_commits: set[tuple[str, str]] = set()

        for snapshot in version_snapshots:
            ref = snapshot['ref']
            version = snapshot.get('version')
            commit_id = snapshot.get('commit_id') or repository_commit_id
            version_source_val = as_optional_str(snapshot.get('version_source'))
            path_listing_started_at = time.perf_counter()
            # Discover paths per ref: a tag may contain skills that were later
            # renamed, removed, or that never existed at HEAD, so HEAD's path
            # set cannot be reused as the universe of tag paths.
            current_tag_skill_paths = self.git_ops.list_skill_paths_for_ref(
                repo_root, ref, should_skip_relative_path,
            )
            tree_hashes = self.git_ops.get_skill_tree_hashes(
                repo_root, current_tag_skill_paths, ref=ref,
            )
            _logger.debug(
                'Tag skill path listing timing: repo=%s ref=%s current_paths=%d '
                'elapsed=%.3fs',
                getattr(repo, 'repo_name', None) or repo.url,
                ref,
                len(current_tag_skill_paths),
                time.perf_counter() - path_listing_started_at,
            )
            for relative_path in current_tag_skill_paths:
                scan_started_at = time.perf_counter()
                virtual_skill_file = repo_root / relative_path
                metadata_content = self.git_ops.load_skill_frontmatter_from_git_ref(
                    repo_root, ref, relative_path, parse_skill_frontmatter_text,
                )
                if metadata_content is None:
                    continue
                input_elapsed = time.perf_counter() - scan_started_at
                tree_hash = tree_hashes.get(relative_path)
                skill_id = build_public_skill_id(repo, repo_root, virtual_skill_file)
                skill = await self._build_skill_record(
                    repo=repo,
                    skill_file=virtual_skill_file,
                    relative_path=relative_path,
                    metadata_content=metadata_content,
                    ref=ref,
                    version=version,
                    commit_id=commit_id,
                    tree_hash=tree_hash,
                    skill_id=skill_id,
                    repository_latest_tags=repository_latest_tags,
                    category_cache=category_cache,
                    version_source=version_source_val,
                    author=author,
                    scan_started_at=scan_started_at,
                    input_elapsed=input_elapsed,
                    return_skill_model=False,
                    existing_record=existing_versions.get((skill_id, version)),
                )
                version_key = (skill.skill_id, skill.version) if skill.version else None
                commit_key = (skill.skill_id, skill.commit_id) if skill.commit_id else None
                if version_key is not None and version_key in seen_versions:
                    _logger.debug(
                        'Skipped duplicate skill version: skill_id=%s version=%s commit_id=%s',
                        skill.skill_id,
                        skill.version or '-',
                        skill.commit_id or '-',
                    )
                    continue
                if commit_key is not None and commit_key in seen_commits:
                    _logger.debug(
                        'Skipped duplicate skill commit: skill_id=%s version=%s commit_id=%s',
                        skill.skill_id,
                        skill.version or '-',
                        skill.commit_id or '-',
                    )
                    continue
                if version_key is not None:
                    seen_versions.add(version_key)
                if commit_key is not None:
                    seen_commits.add(commit_key)
                _logger.info(
                    'Discovered skill: skill_id=%s version=%s source=%s',
                    skill.skill_id, skill.version or '-', relative_path,
                )
                discovered.append(skill)

        return discovered

    async def _build_skill_record(
        self,
        repo: SkillRepoModel,
        skill_file: Path,
        relative_path: str,
        metadata_content: tuple[dict[str, object], str],
        ref: str | None,
        version: str | None,
        commit_id: str | None,
        tree_hash: str | None,
        skill_id: str,
        repository_latest_tags: list[str],
        category_cache: dict[str, str | None],
        version_source: str | None,
        author: str | None,
        scan_started_at: float,
        input_elapsed: float,
        *,
        return_skill_model: bool = True,
        existing_record: Skill | SkillVersion | None = None,
    ) -> Skill | SkillVersion:
        prepare_started_at = time.perf_counter()
        metadata, content = metadata_content
        merged_metadata = dict(metadata)
        if repository_latest_tags and 'repository_latest_tags' not in merged_metadata:
            merged_metadata['repository_latest_tags'] = repository_latest_tags
        if version_source and 'version_source' not in merged_metadata:
            merged_metadata['version_source'] = version_source
        source_url = build_skill_md_url(repo, relative_path, ref=ref)
        if source_url is None:
            raise ValueError(
                f'Failed to build source_url for repository {repo.id}: {relative_path}'
            )
        prepare_elapsed = time.perf_counter() - prepare_started_at

        context_started_at = time.perf_counter()
        host, source_author = derive_skill_source(repo.url)
        author = author or source_author
        prepare_elapsed += time.perf_counter() - context_started_at

        category_started_at = time.perf_counter()
        category = await self._classify_skill_category(
            skill_file=skill_file,
            metadata=merged_metadata,
            content=content or '',
            source_url=source_url,
            skill_id=skill_id,
            category_cache=category_cache,
        )
        category_elapsed = time.perf_counter() - category_started_at

        security_started_at = time.perf_counter()
        security = await self._resolve_security_result(
            repo=repo,
            relative_path=relative_path,
            skill_id=skill_id,
            version=version,
            commit_id=commit_id,
            tree_hash=tree_hash,
            existing_record=existing_record,
        )
        if security.audit_details:
            merged_metadata['security_audit'] = security.audit_details
        security_elapsed = time.perf_counter() - security_started_at

        assemble_started_at = time.perf_counter()
        common = {
            'skill_repo_id': repo.id,
            'skill_id': skill_id,
            'name': derive_repository_skill_name(skill_file, metadata),
            'description': as_optional_str(metadata.get('description')),
            'version': version or as_optional_str(metadata.get('version')),
            'commit_id': commit_id,
            'tree_hash': tree_hash,
            'author': author,
            'source': host,
            'source_url': source_url,
            'repo_url': repo.url,
            'category': category,
            'tags': as_optional_str_list(metadata.get('tags')),
            'platform': as_optional_str(getattr(repo, 'platform', None)) or as_optional_str(metadata.get('platform')),
            'extra_metadata': merged_metadata,
            'content': content or None,
            'risk_score': security.risk_score,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        model_class = Skill if return_skill_model else SkillVersion
        record = model_class(**common)
        setattr(record, '_security_audit_triggered', security.audit_triggered)
        assemble_elapsed = time.perf_counter() - assemble_started_at
        total_elapsed = time.perf_counter() - scan_started_at
        accounted_elapsed = (
            input_elapsed
            + prepare_elapsed
            + category_elapsed
            + security_elapsed
            + assemble_elapsed
        )
        _logger.debug(
            'Skill timing: skill_id=%s version=%s input=%.3fs prepare=%.3fs '
            'category=%.3fs security=%.3fs assemble=%.3fs '
            'other=%.3fs total=%.3fs',
            skill_id,
            version or 'latest',
            input_elapsed,
            prepare_elapsed,
            category_elapsed,
            security_elapsed,
            assemble_elapsed,
            max(0.0, total_elapsed - accounted_elapsed),
            total_elapsed,
        )
        return record

    async def _resolve_security_result(
        self,
        *,
        repo: SkillRepoModel,
        relative_path: str,
        skill_id: str,
        version: str | None,
        commit_id: str | None,
        tree_hash: str | None,
        existing_record: Skill | SkillVersion | None,
    ) -> SecurityResolution:
        existing_metadata = (
            dict(existing_record.extra_metadata or {})
            if existing_record is not None
            else {}
        )
        if (
            existing_record is not None
            and tree_hash is not None
            and tree_hash == existing_record.tree_hash
            and existing_record.risk_score is not None
        ):
            audit_details = existing_metadata.get('security_audit')
            _logger.debug(
                'Reused security result: skill_id=%s version=%s tree_hash=%s score=%s',
                skill_id,
                version or '-',
                tree_hash,
                existing_record.risk_score,
            )
            return SecurityResolution(
                risk_score=existing_record.risk_score,
                audit_details=dict(audit_details) if audit_details else None,
                audit_triggered=False,
            )

        report = await self._audit_skill_security(
            repo=repo,
            relative_path=relative_path,
            commit_id=commit_id,
            skill_id=skill_id,
        )
        risk_score, audit_details = self._extract_audit_artifacts(report)
        return SecurityResolution(
            risk_score=risk_score,
            audit_details=audit_details,
            audit_triggered=bool(
                audit_details
                and audit_details.get('skillspector_async')
                and audit_details.get('skillspector_build_number') is not None
            ),
        )

    async def _classify_skill_category(
        self,
        *,
        skill_file: Path,
        metadata: dict[str, object],
        content: str,
        source_url: str,
        skill_id: str,
        category_cache: dict[str, str | None],
    ) -> str | None:
        if skill_id in category_cache:
            return category_cache[skill_id]

        if self.category_classifier is None:
            category = as_optional_str(metadata.get('category'))
            category_cache[skill_id] = category
            return category
        category = self.category_classifier.classify(
            skill_file=skill_file,
            metadata=metadata,
            content=content,
            source_url=source_url,
        )
        category_cache[skill_id] = category
        return category

    async def _audit_skill_security(
        self,
        *,
        repo: SkillRepoModel,
        relative_path: str,
        commit_id: str | None,
        skill_id: str,
    ) -> SecurityReport | None:
        """Trigger a security audit for one skill record.

        The crawler stays DB-agnostic; ``SkillManager`` persists the
        ``SecurityAudit`` row after the skill is stored.
        """
        if self.security_detector is None or not self.security_detector.has_skillspector:
            return None
        skill_path = Path(relative_path).parent.as_posix()
        if skill_path == '.':
            skill_path = ''

        try:
            if self.security_async_mode:
                build_number = await self.security_detector.trigger_skillspector(
                    repo.url, version=commit_id, skill_path=skill_path,
                )
                report = SecurityReport(
                    resource_type='skill',
                    resource_id=skill_id,
                    risk_level='unknown',
                    risk_signals=[],
                    details={
                        'skillspector_async': True,
                        'skillspector_build_number': build_number,
                        'source': 'skillspector',
                    },
                )
            else:
                report = await self.security_detector.detect_skillspector(
                    repo.url, version=commit_id, skill_path=skill_path,
                )
        except Exception:
            _logger.warning(
                'Security audit failed for skill %s', skill_id, exc_info=True,
            )
            report = SecurityReport(
                resource_type='skill',
                resource_id=skill_id,
                risk_level='unknown',
                risk_signals=[],
                details={'error': 'audit_failed', 'source': 'skillspector'},
            )

        return report

    async def audit_existing_skill(
        self,
        *,
        repo: SkillRepoModel,
        relative_path: str,
        commit_id: str | None,
        skill_id: str,
    ) -> SecurityReport | None:
        """Trigger security detection for an already persisted skill record."""
        return await self._audit_skill_security(
            repo=repo,
            relative_path=relative_path,
            commit_id=commit_id,
            skill_id=skill_id,
        )

    @staticmethod
    def _extract_audit_artifacts(
        report: SecurityReport | None,
    ) -> tuple[int | None, dict[str, Any] | None]:
        """Translate a ``SecurityReport`` into ``risk_score`` + storable details."""
        if report is None:
            return None, None

        score = report.details.get('skillspector_score')
        if score is None:
            level = (report.risk_level or 'unknown').lower()
            score_map = {'critical': 90, 'high': 65, 'medium': 35, 'low': 10}
            score = score_map.get(level) if level != 'unknown' else None

        details = dict(report.details) if report.details else None
        if details:
            details.setdefault('risk_level', report.risk_level)
            details.setdefault(
                'risk_signals',
                [s.__dict__ for s in report.risk_signals],
            )
        return score, details
