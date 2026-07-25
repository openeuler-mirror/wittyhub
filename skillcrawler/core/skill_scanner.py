"""Skill scanning logic: version scan, current state scan, and record building."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skillcrawler.core.category_classifier import DeepSeekCategoryClassifier
from skillcrawler.core.git_operations import GitOperations
from skillcrawler.core.skill_parser import (
    as_optional_str,
    as_optional_str_list,
    build_public_skill_id,
    build_skill_md_url,
    derive_repository_skill_name,
    derive_skill_source,
    find_scannable_skill_files,
    load_skill_frontmatter,
    parse_skill_frontmatter_text,
    should_skip_relative_path,
    to_repository_relative_path,
)
from src.models.orm import SkillVersion
from src.models.repository import SkillRepository

if TYPE_CHECKING:
    from src.models.orm import SkillRepoModel

_logger = logging.getLogger(__name__)


class SkillScanner:
    """Scans repositories for skills and builds skill records."""

    def __init__(
        self,
        git_ops: GitOperations,
        skill_repository: SkillRepository,
        category_classifier: DeepSeekCategoryClassifier | None = None,
    ) -> None:
        self.git_ops = git_ops
        self.skill_repository = skill_repository
        self.category_classifier = category_classifier

    async def start_scan(
        self,
        repo: SkillRepoModel,
        repo_root: Path,
        repository_git_metadata: dict[str, Any] | None = None,
        version_snapshots: list[dict[str, str]] | None = None,
        author: str | None = None,
    ) -> tuple[list[SkillVersion], list[SkillVersion]]:
        if not repo_root.exists():
            raise ValueError(
                f'Repository root does not exist for repository {repo.id}: {repo_root}'
            )

        skill_files = find_scannable_skill_files(repo_root)

        repository_git_metadata = repository_git_metadata or {}
        repository_commit_id = as_optional_str(repository_git_metadata.get('commit_id'))
        repository_latest_tags = as_optional_str_list(repository_git_metadata.get('latest_tags')) or []
        latest_skills = await self._scan_latest_skills(
            repo=repo,
            repo_root=repo_root,
            skill_files=skill_files,
            repository_commit_id=repository_commit_id,
            repository_latest_tags=repository_latest_tags,
            author=author,
        )

        tagged_skills: list[SkillVersion] = []
        if version_snapshots:
            tagged_skills = await self._scan_tagged_skills(
                repo=repo,
                repo_root=repo_root,
                skill_files=skill_files,
                version_snapshots=version_snapshots,
                repository_commit_id=repository_commit_id,
                repository_latest_tags=repository_latest_tags,
                author=author,
            )

        return latest_skills, tagged_skills

    async def _scan_latest_skills(
        self,
        repo: SkillRepoModel,
        repo_root: Path,
        skill_files: list[Path],
        repository_commit_id: str | None,
        repository_latest_tags: list[str],
        author: str | None,
    ) -> list[SkillVersion]:
        discovered: list[SkillVersion] = []
        category_cache: dict[str, str | None] = {}
        for skill_file in skill_files:
            relative_path = to_repository_relative_path(repo_root, skill_file)
            skill = await self._build_skill_record(
                repo=repo,
                repo_root=repo_root,
                skill_file=skill_file,
                relative_path=relative_path,
                metadata_content=load_skill_frontmatter(skill_file),
                ref=repo.branch or None,
                version='latest',
                commit_id=repository_commit_id,
                repository_latest_tags=repository_latest_tags,
                category_cache=category_cache,
                version_source='branch_head',
                author=author,
            )
            _logger.info(
                'Discovered skill: skill_id=%s version=%s source=%s',
                skill.skill_id, skill.version or '-', relative_path,
            )
            discovered.append(skill)
        return discovered

    async def _scan_tagged_skills(
        self,
        repo: SkillRepoModel,
        repo_root: Path,
        skill_files: list[Path],
        version_snapshots: list[dict[str, str]],
        repository_commit_id: str | None,
        repository_latest_tags: list[str],
        author: str | None,
    ) -> list[SkillVersion]:
        discovered: list[SkillVersion] = []
        seen_versions: set[tuple[str, str]] = set()
        seen_commits: set[tuple[str, str]] = set()
        category_cache: dict[str, str | None] = {}
        current_skill_paths = {
            to_repository_relative_path(repo_root, skill_file)
            for skill_file in skill_files
        }

        for snapshot in version_snapshots:
            ref = snapshot['ref']
            version = snapshot.get('version')
            commit_id = snapshot.get('commit_id') or repository_commit_id
            version_source_val = as_optional_str(snapshot.get('version_source'))
            for relative_path in self.git_ops.list_skill_paths_for_ref(
                repo_root, ref, should_skip_relative_path,
            ):
                if relative_path not in current_skill_paths:
                    continue
                virtual_skill_file = repo_root / relative_path
                metadata_content = self.git_ops.load_skill_frontmatter_from_git_ref(
                    repo_root, ref, relative_path, parse_skill_frontmatter_text,
                )
                if metadata_content is None:
                    continue
                skill = await self._build_skill_record(
                    repo=repo,
                    repo_root=repo_root,
                    skill_file=virtual_skill_file,
                    relative_path=relative_path,
                    metadata_content=metadata_content,
                    ref=ref,
                    version=version,
                    commit_id=commit_id,
                    repository_latest_tags=repository_latest_tags,
                    category_cache=category_cache,
                    version_source=version_source_val,
                    author=author,
                )
                version_key = (skill.skill_id, skill.version) if skill.version else None
                commit_key = (skill.skill_id, skill.commit_id) if skill.commit_id else None
                if version_key is not None and version_key in seen_versions:
                    continue
                if commit_key is not None and commit_key in seen_commits:
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
        repo_root: Path,
        skill_file: Path,
        relative_path: str,
        metadata_content: tuple[dict[str, object], str],
        ref: str | None,
        version: str | None,
        commit_id: str | None,
        repository_latest_tags: list[str],
        category_cache: dict[str, str | None],
        version_source: str | None,
        author: str | None,
    ) -> SkillVersion:
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
        skill_id = build_public_skill_id(repo, repo_root, skill_file)
        skill_dir_commit_id = self._get_skill_directory_commit_id(
            repo_root=repo_root,
            relative_path=relative_path,
            ref=ref,
        )
        if skill_dir_commit_id:
            merged_metadata['skill_directory_commit_id'] = skill_dir_commit_id
        host, source_author = derive_skill_source(repo.url)
        author = author or source_author
        category = await self._classify_skill_category(
            skill_file=skill_file,
            metadata=merged_metadata,
            content=content or '',
            source_url=source_url,
            skill_id=skill_id,
            category_cache=category_cache,
        )
        return SkillVersion(
            skill_repo_id=repo.id,
            skill_id=skill_id,
            name=derive_repository_skill_name(skill_file, metadata),
            description=as_optional_str(metadata.get('description')),
            version=as_optional_str(metadata.get('version')) or version,
            commit_id=skill_dir_commit_id or commit_id,
            author=author,
            source=host,
            source_url=source_url,
            repo_url=repo.url,
            category=category,
            tags=as_optional_str_list(metadata.get('tags')),
            platform=as_optional_str(getattr(repo, 'platform', None)) or as_optional_str(metadata.get('platform')),
            extra_metadata=merged_metadata,
            content=content or None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def _get_skill_directory_commit_id(
        self,
        *,
        repo_root: Path,
        relative_path: str,
        ref: str | None,
    ) -> str | None:
        skill_dir = Path(relative_path).parent.as_posix()
        if skill_dir == '.':
            skill_dir = ''
        return self.git_ops.get_latest_commit_id_for_path(
            repo_root,
            skill_dir,
            ref=ref or 'HEAD',
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

        existing_category = await self.skill_repository.get_category_by_skill_id(skill_id)
        if existing_category:
            category_cache[skill_id] = existing_category
            return existing_category

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
