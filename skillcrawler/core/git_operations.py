"""Git clone, fetch, metadata, and authentication operations."""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from skillcrawler.config import load_crawler_config

_logger = logging.getLogger(__name__)

GIT_CLONE_RETRY_TIMES = 3
GIT_CLONE_TIMEOUT_SECONDS = 120
DEFAULT_MAX_TAGS_PER_REPO = 3
GIT_NON_INTERACTIVE_ENV = {
    'GIT_TERMINAL_PROMPT': '0',
    'GCM_INTERACTIVE': 'Never',
}


class GitOperations:
    """Handles git clone, fetch, metadata collection, and GitHub auth."""

    def __init__(
        self,
        github_token: str | None = None,
        github_username: str | None = None,
        max_tags_per_repo: int = DEFAULT_MAX_TAGS_PER_REPO,
    ) -> None:
        self.github_token = github_token or self._load_github_token()
        self.github_username = github_username or self._load_github_username()
        self.max_tags_per_repo = max_tags_per_repo if max_tags_per_repo != DEFAULT_MAX_TAGS_PER_REPO else self._load_max_tags_per_repo()

    # ── Public operations ──────────────────────────────────────────

    def clone_repository(
        self,
        clone_dir: Path,
        clone_url: str,
        *,
        branch: str | None = None,
        repo_url: str | None = None,
    ) -> None:
        command = ['git', 'clone', '--depth', '1']
        if branch:
            command.extend(['--branch', branch])
        command.extend([clone_url, str(clone_dir)])
        self._run_git_command_with_auth_retry(command, clone_url, repo_url, 'clone')

    def update_existing_repository(
        self,
        clone_dir: Path,
        clone_url: str,
        *,
        branch: str | None = None,
        repo_url: str | None = None,
    ) -> None:
        self._run_git_command_with_retries(
            ['git', '-C', str(clone_dir), 'remote', 'set-url', 'origin', clone_url]
        )

        target_branch = branch or self._get_cloned_repo_branch(clone_dir)
        if target_branch:
            fetch_command = [
                'git', '-C', str(clone_dir), 'fetch',
                '--depth', '1', 'origin', target_branch,
            ]
            self._run_git_command_with_auth_retry(
                fetch_command, clone_url, repo_url, 'fetch',
            )
            self._run_git_command_with_retries(
                ['git', '-C', str(clone_dir), 'checkout', '-B', target_branch, 'FETCH_HEAD']
            )
            return

        self._run_git_command_with_auth_retry(
            ['git', '-C', str(clone_dir), 'fetch', '--depth', '1', 'origin'],
            clone_url, repo_url, 'fetch',
        )

    def collect_repository_git_metadata(
        self,
        clone_dir: Path,
        clone_url: str,
        repo_url: str | None,
    ) -> dict[str, Any]:
        commit_id = self.get_repository_head_commit_id(clone_dir)
        latest_tags = self._get_repository_latest_tags(clone_dir, clone_url, repo_url)
        latest_tag_commits = {
            tag: self._get_git_ref_commit_id(clone_dir, tag)
            for tag in latest_tags
        }
        return {
            'commit_id': commit_id,
            'latest_tags': latest_tags,
            'latest_tag_commits': latest_tag_commits,
        }

    def get_repository_head_commit_id(self, clone_dir: Path) -> str | None:
        return self._get_git_ref_commit_id(clone_dir, 'HEAD')

    def get_cloned_repo_branch(self, clone_dir: Path) -> str | None:
        return self._get_cloned_repo_branch(clone_dir)

    def _get_cloned_repo_branch(self, clone_dir: Path) -> str | None:
        # Prefer the checked-out branch when the repo is not detached.
        try:
            branch = self._run_git_command(
                ['git', '-C', str(clone_dir), 'rev-parse', '--abbrev-ref', 'HEAD']
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            branch = ''
        branch = branch.strip()
        if branch and branch != 'HEAD':
            return branch

        # Fall back to the remote's default branch, which still works when
        # the local checkout is detached after fetching a specific ref.
        try:
            origin_head = self._run_git_command(
                ['git', '-C', str(clone_dir), 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD']
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            origin_head = ''
        origin_head = origin_head.strip()
        if origin_head.startswith('origin/'):
            return origin_head.removeprefix('origin/').strip() or None

        try:
            remote_info = self._run_git_command(
                ['git', '-C', str(clone_dir), 'remote', 'show', 'origin']
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

        for line in remote_info.splitlines():
            stripped = line.strip()
            if not stripped.startswith('HEAD branch:'):
                continue
            default_branch = stripped.split(':', 1)[1].strip()
            return default_branch or None

        return None

    def list_skill_paths_for_ref(self, repo_root: Path, ref: str, should_skip_relative_path) -> list[str]:
        try:
            output = self._run_git_command(
                ['git', '-C', str(repo_root), 'ls-tree', '-r', '--name-only', ref]
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning('Failed to list skill paths for %s (%s): %s', repo_root, ref, exc)
            return []

        skill_paths: list[str] = []
        for line in output.splitlines():
            relative_path = line.strip()
            if not relative_path or not relative_path.endswith('SKILL.md'):
                continue
            if should_skip_relative_path(relative_path):
                continue
            skill_paths.append(relative_path)
        return skill_paths

    def load_skill_frontmatter_from_git_ref(
        self,
        repo_root: Path,
        ref: str,
        relative_path: str,
        parse_fn,
    ) -> tuple[dict[str, object], str] | None:
        try:
            text = self._run_git_command(
                ['git', '-C', str(repo_root), 'show', f'{ref}:{relative_path}']
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning(
                'Failed to read skill file from %s (%s:%s): %s',
                repo_root, ref, relative_path, exc,
            )
            return None
        return parse_fn(text)

    # ── Version snapshots ──────────────────────────────────────────

    @staticmethod
    def build_repository_version_snapshots(
        repository_git_metadata: dict[str, Any],
        as_optional_str,
        as_optional_str_list,
    ) -> list[dict[str, str]]:
        latest_tags = as_optional_str_list(repository_git_metadata.get('latest_tags')) or []
        latest_tag_commits = repository_git_metadata.get('latest_tag_commits') or {}
        snapshots: list[dict[str, str]] = []
        tag_commit_ids: set[str] = set()

        for tag in latest_tags:
            commit_id = as_optional_str(latest_tag_commits.get(tag))
            if commit_id is None:
                continue
            tag_commit_ids.add(commit_id)
            snapshots.append({
                'ref': tag,
                'version': tag,
                'commit_id': commit_id,
                'version_source': 'tag',
            })

        head_commit_id = as_optional_str(repository_git_metadata.get('commit_id'))
        if head_commit_id and head_commit_id not in tag_commit_ids:
            snapshots.append({
                'ref': 'HEAD',
                'version': 'latest',
                'commit_id': head_commit_id,
                'version_source': 'branch_head',
            })
        return snapshots

    # ── Git command execution ──────────────────────────────────────

    def _run_git_command_with_auth_retry(
        self,
        command: list[str],
        clone_url: str,
        repo_url: str | None,
        action: str,
    ) -> None:
        auth_command = self._build_github_token_command(command, clone_url)
        if auth_command is not None:
            try:
                self._run_git_command_with_retries(command)
                return
            except subprocess.CalledProcessError:
                _logger.warning(
                    'Git %s failed for %s, retrying with GitHub token authentication',
                    action, repo_url or clone_url,
                )
                self._run_git_command_with_retries(auth_command)
                return
        self._run_git_command_with_retries(command)

    def _run_git_command_with_retries(self, command: list[str]) -> None:
        last_exc: subprocess.CalledProcessError | None = None
        last_timeout: subprocess.TimeoutExpired | None = None
        env = os.environ.copy()
        env.update(GIT_NON_INTERACTIVE_ENV)
        for _ in range(GIT_CLONE_RETRY_TIMES):
            try:
                subprocess.run(
                    command, check=True, capture_output=True, text=True,
                    env=env, timeout=GIT_CLONE_TIMEOUT_SECONDS,
                )
                return
            except subprocess.CalledProcessError as exc:
                last_exc = exc
            except subprocess.TimeoutExpired as exc:
                last_timeout = exc
        if last_timeout is not None:
            raise self._sanitize_timeout_error(last_timeout)
        assert last_exc is not None
        raise self._sanitize_called_process_error(last_exc)

    def _run_git_command(self, command: list[str]) -> str:
        env = os.environ.copy()
        env.update(GIT_NON_INTERACTIVE_ENV)
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True,
                env=env, timeout=GIT_CLONE_TIMEOUT_SECONDS,
            )
        except subprocess.CalledProcessError as exc:
            raise self._sanitize_called_process_error(exc)
        except subprocess.TimeoutExpired as exc:
            raise self._sanitize_timeout_error(exc)
        return result.stdout.strip()

    def _get_git_ref_commit_id(self, clone_dir: Path, ref: str) -> str | None:
        try:
            commit_id = self._run_git_command(
                ['git', '-C', str(clone_dir), 'rev-parse', ref]
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning('Failed to read git ref commit id for %s (%s): %s', clone_dir, ref, exc)
            return None
        return commit_id or None

    def _get_repository_latest_tags(
        self,
        clone_dir: Path,
        clone_url: str,
        repo_url: str | None,
    ) -> list[str]:
        fetch_tags_command = [
            'git', '-C', str(clone_dir), 'fetch',
            '--tags', '--force', '--depth', '1', 'origin',
        ]
        try:
            self._run_git_command_with_auth_retry(fetch_tags_command, clone_url, repo_url, 'fetch tags')
            output = self._run_git_command([
                'git', '-C', str(clone_dir), 'for-each-ref',
                '--sort=-creatordate', '--format=%(refname:short)', 'refs/tags',
            ])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning('Failed to read skill repo tags for %s: %s', clone_dir, exc)
            return []

        tags: list[str] = []
        for line in output.splitlines():
            tag = line.strip()
            if not tag or tag in tags:
                continue
            tags.append(tag)
            if len(tags) == self.max_tags_per_repo:
                break
        return tags

    # ── GitHub auth ────────────────────────────────────────────────

    @staticmethod
    def _load_github_token() -> str | None:
        try:
            config = load_crawler_config()
        except Exception as exc:
            _logger.warning('Failed to load crawler config: %s', exc)
            return None
        crawler_config = config.get('crawler')
        if not isinstance(crawler_config, dict):
            return None
        token = crawler_config.get('github_token')
        if not isinstance(token, str):
            return None
        token = token.strip()
        return token or None

    @staticmethod
    def _load_github_username() -> str | None:
        try:
            config = load_crawler_config()
        except Exception:
            return None
        crawler_config = config.get('crawler')
        if not isinstance(crawler_config, dict):
            return None
        username = crawler_config.get('github_username')
        if not isinstance(username, str):
            return 'git'
        username = username.strip()
        return username or 'git'

    @staticmethod
    def _load_max_tags_per_repo() -> int:
        try:
            config = load_crawler_config()
        except Exception:
            return DEFAULT_MAX_TAGS_PER_REPO
        crawler_config = config.get('crawler')
        if not isinstance(crawler_config, dict):
            return DEFAULT_MAX_TAGS_PER_REPO
        value = crawler_config.get('max_tags_per_repo')
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return DEFAULT_MAX_TAGS_PER_REPO
        return parsed if parsed > 0 else DEFAULT_MAX_TAGS_PER_REPO

    def _build_github_token_command(
        self, command: list[str], clone_url: str,
    ) -> list[str] | None:
        if not self.github_token:
            return None
        token_clone_url = self._build_github_token_clone_url(clone_url)
        if token_clone_url is None:
            return None
        fallback_command = list(command)
        for index, part in enumerate(fallback_command):
            if part == clone_url:
                fallback_command[index] = token_clone_url
                return fallback_command
        return None

    def _build_github_token_clone_url(self, clone_url: str) -> str | None:
        if not self.github_token:
            return None
        username = self.github_username or 'git'
        ssh_match = re.match(r'git@github\.com:(.+)', clone_url)
        if ssh_match:
            repository_path = ssh_match.group(1).strip('/')
            return f'https://{username}:{self.github_token}@github.com/{repository_path}'
        parsed = urlparse(clone_url)
        if parsed.scheme not in {'http', 'https'} or parsed.netloc.lower() != 'github.com':
            return None
        repository_path = parsed.path.lstrip('/')
        if not repository_path:
            return None
        return f'https://{username}:{self.github_token}@github.com/{repository_path}'

    # ── Error sanitization ─────────────────────────────────────────

    def _sanitize_called_process_error(
        self, error: subprocess.CalledProcessError,
    ) -> subprocess.CalledProcessError:
        if not self.github_token:
            return error
        sanitized_cmd: str | list[str]
        if isinstance(error.cmd, list):
            sanitized_cmd = [self._mask_github_token(part) for part in error.cmd]
        else:
            sanitized_cmd = self._mask_github_token(str(error.cmd))
        return subprocess.CalledProcessError(
            error.returncode, sanitized_cmd,
            output=self._mask_github_token(error.output),
            stderr=self._mask_github_token(error.stderr),
        )

    def _mask_github_token(self, value: str | None) -> str | None:
        if value is None or not self.github_token:
            return value
        return value.replace(self.github_token, '***')

    def summarize_exception(self, exc: Exception) -> str:
        if isinstance(exc, subprocess.TimeoutExpired):
            return self._format_timeout_error(exc)
        if isinstance(exc, subprocess.CalledProcessError):
            detail = self._extract_process_error_detail(exc)
            if detail:
                return detail
        cause = exc.__cause__
        if isinstance(cause, subprocess.TimeoutExpired):
            return self._format_timeout_error(cause)
        if isinstance(cause, subprocess.CalledProcessError):
            detail = self._extract_process_error_detail(cause)
            if detail:
                return detail
        return str(exc).strip() or exc.__class__.__name__

    def _extract_process_error_detail(
        self, error: subprocess.CalledProcessError,
    ) -> str:
        candidates = [
            self._mask_github_token(error.stderr),
            self._mask_github_token(error.output),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            lines = [line.strip() for line in candidate.splitlines() if line.strip()]
            if lines:
                return lines[-1]
        return str(error).strip()

    def _sanitize_timeout_error(
        self, error: subprocess.TimeoutExpired,
    ) -> subprocess.TimeoutExpired:
        cmd = error.cmd
        if isinstance(cmd, list):
            sanitized_cmd = [self._mask_github_token(part) for part in cmd]
        else:
            sanitized_cmd = self._mask_github_token(str(cmd))
        return subprocess.TimeoutExpired(
            sanitized_cmd, error.timeout,
            output=self._mask_github_token(error.output),
            stderr=self._mask_github_token(error.stderr),
        )

    @staticmethod
    def _format_timeout_error(error: subprocess.TimeoutExpired) -> str:
        timeout_seconds = int(error.timeout) if error.timeout else GIT_CLONE_TIMEOUT_SECONDS
        return f'git clone timed out after {timeout_seconds}s'
