"""Git clone, fetch, metadata, and authentication operations."""

from __future__ import annotations

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.core.config import get_settings

_logger = logging.getLogger(__name__)
settings = get_settings()

GIT_CLONE_RETRY_TIMES = 3
GIT_CLONE_TIMEOUT_SECONDS = 120
DEFAULT_MAX_TAGS_PER_REPO = 5
TAG_CANDIDATE_REF_PREFIX = 'refs/crawler/tag-candidates'
UNSUPPORTED_FILTER_MESSAGES = (
    'filtering not recognized by server',
    'server does not support filter',
)
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
        command = ['git', 'clone', '--depth', '1', '--no-checkout', '--filter=blob:none']
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
        is_shallow = self.is_shallow_repository(clone_dir)
        if target_branch:
            fetch_command = [
                'git', '-C', str(clone_dir), 'fetch',
            ]
            if is_shallow:
                fetch_command.extend(['--depth', '1'])
            fetch_command.extend(['origin', target_branch])
            self._run_git_command_with_auth_retry(
                fetch_command, clone_url, repo_url, 'fetch',
            )
            self._run_git_command_with_retries(
                ['git', '-C', str(clone_dir), 'update-ref', f'refs/heads/{target_branch}', 'FETCH_HEAD']
            )
            return

        fetch_command = ['git', '-C', str(clone_dir), 'fetch']
        if is_shallow:
            fetch_command.extend(['--depth', '1'])
        fetch_command.append('origin')
        self._run_git_command_with_auth_retry(
            fetch_command, clone_url, repo_url, 'fetch',
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
            'is_shallow_repository': self.is_shallow_repository(clone_dir),
        }

    def get_repository_head_commit_id(self, clone_dir: Path) -> str | None:
        return self._get_git_ref_commit_id(clone_dir, 'HEAD')

    def is_shallow_repository(self, clone_dir: Path) -> bool:
        try:
            is_shallow = self._run_git_command(
                ['git', '-C', str(clone_dir), 'rev-parse', '--is-shallow-repository']
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return (clone_dir / '.git' / 'shallow').exists()
        return is_shallow.strip().lower() == 'true'

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

    def get_skill_tree_hashes(
        self,
        repo_root: Path,
        relative_skill_paths: list[str],
        *,
        ref: str = 'HEAD',
    ) -> dict[str, str | None]:
        """Return directory tree hashes for multiple skills in one ``rev-parse``.

        Maps each repo-relative SKILL.md path to its parent directory's tree
        hash (the root tree hash when SKILL.md sits at the repository root).
        Unresolvable paths map to ``None`` instead of raising.
        """
        if not relative_skill_paths:
            return {}

        def _treeish(relative_skill_path: str) -> str:
            skill_dir = Path(relative_skill_path).parent.as_posix()
            if skill_dir == '.':
                skill_dir = ''
            return f'{ref}:{skill_dir}'

        command = ['git', '-C', str(repo_root), 'rev-parse']
        command.extend(_treeish(path) for path in relative_skill_paths)

        try:
            lines = self._run_git_command(command).splitlines()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning(
                'Failed to read tree hashes for %s (%s): %s',
                repo_root, ref, exc,
            )
            lines = []

        hashes: dict[str, str | None] = {}
        for index, path in enumerate(relative_skill_paths):
            if index < len(lines):
                hashes[path] = lines[index] or None
            else:
                hashes[path] = None
        return hashes

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

        for tag in latest_tags:
            commit_id = as_optional_str(latest_tag_commits.get(tag))
            if commit_id is None:
                continue
            snapshots.append({
                'ref': tag,
                'version': tag,
                'commit_id': commit_id,
                'version_source': 'tag',
            })

        return snapshots

    # ── Git command execution ──────────────────────────────────────

    def _run_git_command_with_auth_retry(
        self,
        command: list[str],
        clone_url: str,
        repo_url: str | None,
        action: str,
        *,
        reject_unsupported_filter: bool = False,
    ) -> None:
        auth_command = self._build_github_token_command(command, clone_url)
        if auth_command is not None:
            try:
                self._run_git_command_with_retries(
                    command, reject_unsupported_filter=reject_unsupported_filter,
                )
                return
            except subprocess.CalledProcessError:
                _logger.warning(
                    'Git %s failed for %s, retrying with GitHub token authentication',
                    action, repo_url or clone_url,
                )
                self._run_git_command_with_retries(
                    auth_command, reject_unsupported_filter=reject_unsupported_filter,
                )
                return
        self._run_git_command_with_retries(
            command, reject_unsupported_filter=reject_unsupported_filter,
        )

    def _run_git_command_with_retries(
        self,
        command: list[str],
        *,
        reject_unsupported_filter: bool = False,
    ) -> None:
        last_exc: subprocess.CalledProcessError | None = None
        last_timeout: subprocess.TimeoutExpired | None = None
        env = os.environ.copy()
        env.update(GIT_NON_INTERACTIVE_ENV)
        for _ in range(GIT_CLONE_RETRY_TIMES):
            try:
                result = subprocess.run(
                    command, check=True, capture_output=True, text=True,
                    env=env, timeout=GIT_CLONE_TIMEOUT_SECONDS,
                )
                if reject_unsupported_filter and self._has_unsupported_filter_warning(
                    result.stderr,
                ):
                    raise subprocess.CalledProcessError(
                        1, command, output=result.stdout, stderr=result.stderr,
                    )
                return
            except subprocess.CalledProcessError as exc:
                last_exc = exc
                if reject_unsupported_filter and self._has_unsupported_filter_warning(
                    exc.stderr,
                ):
                    break
            except subprocess.TimeoutExpired as exc:
                last_timeout = exc
        if last_timeout is not None:
            raise self._sanitize_timeout_error(last_timeout)
        assert last_exc is not None
        raise self._sanitize_called_process_error(last_exc)

    @staticmethod
    def _has_unsupported_filter_warning(stderr: str | bytes | None) -> bool:
        if stderr is None:
            return False
        text = stderr.decode(errors='replace') if isinstance(stderr, bytes) else stderr
        lowered = text.lower()
        return any(message in lowered for message in UNSUPPORTED_FILTER_MESSAGES)

    def _run_git_command(self, command: list[str], input_data: str | None = None) -> str:
        env = os.environ.copy()
        env.update(GIT_NON_INTERACTIVE_ENV)
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True,
                env=env, timeout=GIT_CLONE_TIMEOUT_SECONDS, input=input_data,
            )
        except subprocess.CalledProcessError as exc:
            raise self._sanitize_called_process_error(exc)
        except subprocess.TimeoutExpired as exc:
            raise self._sanitize_timeout_error(exc)
        return result.stdout.strip()

    def _get_git_ref_commit_id(self, clone_dir: Path, ref: str) -> str | None:
        try:
            commit_id = self._run_git_command(
                ['git', '-C', str(clone_dir), 'rev-parse', f'{ref}^{{commit}}']
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
        candidate_tags = self._list_remote_tags(clone_dir, clone_url, repo_url)
        if not candidate_tags:
            return []

        tags_by_date = self._sort_remote_tags_by_creator_date(
            clone_dir, clone_url, repo_url, candidate_tags,
        )
        latest_tags = tags_by_date[:self.max_tags_per_repo]
        if not latest_tags:
            return []

        # The metadata pass uses tree:0, so force a second fetch for the
        # selected tags with blob:none.  --refetch avoids negotiation deciding
        # that the already-present commit is sufficient while its tree is
        # still intentionally missing.
        fetch_tags_command = [
            'git', '-C', str(clone_dir), 'fetch',
            '--force', '--no-tags', '--refetch', '--filter=blob:none', 'origin',
        ]
        fetch_tags_command.extend(
            f'refs/tags/{tag}:refs/tags/{tag}' for tag in latest_tags
        )
        try:
            self._run_git_command_with_auth_retry(fetch_tags_command, clone_url, repo_url, 'fetch tags')
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning(
                'Failed to fetch skill repo tags for %s: %s', clone_dir, exc,
            )
            self._cleanup_orphaned_tmp_packs(clone_dir)
            return []
        return latest_tags

    def _sort_remote_tags_by_creator_date(
        self,
        clone_dir: Path,
        clone_url: str,
        repo_url: str | None,
        candidate_tags: list[str],
    ) -> list[str]:
        """Sort remote tags by tagger/commit time without fetching their trees.

        Annotated tags use their tagger date; lightweight tags use the target
        commit's committer date via Git's ``creatordate`` field.  If the remote
        does not support partial clone filters, retain the natural-name order
        returned by ``_list_remote_tags``.
        """
        # Stale candidate refs from a previous run trigger a Git client bug
        # (``pack-objects.c:4310 should_include_obj`` assertion) on some
        # servers, so drop them before fetching metadata again.
        self._cleanup_candidate_refs(clone_dir)

        probe_tag = candidate_tags[0]
        metadata_probe_command = [
            'git', '-C', str(clone_dir), 'fetch',
            '--force', '--no-tags', '--depth=1', '--filter=tree:0', 'origin',
            f'+refs/tags/{probe_tag}:{TAG_CANDIDATE_REF_PREFIX}/{probe_tag}',
        ]
        try:
            self._run_git_command_with_auth_retry(
                metadata_probe_command, clone_url, repo_url, 'probe tag metadata filter',
                reject_unsupported_filter=True,
            )
            if len(candidate_tags) > 1:
                metadata_fetch_command = [
                    'git', '-C', str(clone_dir), 'fetch',
                    '--force', '--no-tags', '--depth=1', '--filter=tree:0', 'origin',
                    f'+refs/tags/*:{TAG_CANDIDATE_REF_PREFIX}/*',
                ]
                self._run_git_command_with_auth_retry(
                    metadata_fetch_command, clone_url, repo_url, 'fetch tag metadata',
                    reject_unsupported_filter=True,
                )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning(
                'Failed to fetch tag metadata for %s; falling back to natural '
                'tag ordering: %s',
                clone_dir, exc,
            )
            self._cleanup_orphaned_tmp_packs(clone_dir)
            return candidate_tags

        command = [
            'git', '-C', str(clone_dir), 'for-each-ref',
            '--format=%(creatordate:unix)\t%(refname)',
            f'{TAG_CANDIDATE_REF_PREFIX}/',
        ]
        try:
            output = self._run_git_command(command)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning(
                'Failed to read tag creator dates for %s; falling back to '
                'natural tag ordering: %s',
                clone_dir, exc,
            )
            return candidate_tags

        candidate_set = set(candidate_tags)
        dated_tags: list[tuple[int, list[tuple[int, str]], str]] = []
        prefix = f'{TAG_CANDIDATE_REF_PREFIX}/'
        for line in output.splitlines():
            date_text, separator, ref = line.partition('\t')
            if not separator or not ref.startswith(prefix):
                continue
            tag = ref.removeprefix(prefix)
            if tag not in candidate_set:
                continue
            try:
                creator_timestamp = int(date_text)
            except ValueError:
                creator_timestamp = 0
            dated_tags.append((creator_timestamp, self._tag_sort_key(tag), tag))

        dated_tag_names = {tag for _, _, tag in dated_tags}
        undated_tags = [tag for tag in candidate_tags if tag not in dated_tag_names]
        dated_tags.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [tag for _, _, tag in dated_tags] + undated_tags

    def _list_remote_tags(
        self,
        clone_dir: Path,
        clone_url: str,
        repo_url: str | None,
    ) -> list[str]:
        command = ['git', '-C', str(clone_dir), 'ls-remote', '--tags', '--refs', 'origin']
        auth_command = self._build_github_token_command(command, clone_url)
        try:
            if auth_command is not None:
                try:
                    output = self._run_git_command(command)
                except subprocess.CalledProcessError:
                    _logger.warning(
                        'Git ls-remote failed for %s, retrying with GitHub token authentication',
                        repo_url or clone_url,
                    )
                    output = self._run_git_command(auth_command)
            else:
                output = self._run_git_command(command)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            _logger.warning('Failed to read skill repo tags for %s: %s', clone_dir, exc)
            return []

        tags: list[str] = []
        for line in output.splitlines():
            ref = line.split('\t', 1)[-1].strip()
            if not ref.startswith('refs/tags/'):
                continue
            tag = ref.removeprefix('refs/tags/')
            if not tag or tag in tags:
                continue
            tags.append(tag)
        # ``ls-remote`` has no sort option, so sort tags by version for a
        # stable "newest first" ordering.
        return sorted(tags, key=self._tag_sort_key, reverse=True)

    @staticmethod
    def _tag_sort_key(tag: str) -> list[tuple[int, str]]:
        """Natural sort key so version-like tags order correctly (v10 > v9)."""
        parts: list[tuple[int, str]] = []
        for token in re.split(r'(\d+)', tag):
            if not token:
                continue
            if token.isdigit():
                parts.append((1, f'{int(token):012d}'))
            else:
                parts.append((0, token.lower()))
        return parts

    @staticmethod
    def _cleanup_candidate_refs(clone_dir: Path) -> None:
        """Delete leftover ``refs/crawler/tag-candidates/*`` from earlier runs.

        These temporary refs are only meaningful within a single
        ``_sort_remote_tags_by_creator_date`` call.  Stale entries make the
        next ``tree:0`` fetch negotiate against refs whose objects may be
        missing, which trips the ``pack-objects`` assertion on some servers.
        """
        command = [
            'git', '-C', str(clone_dir), 'for-each-ref',
            '--format=delete %(refname)',
            f'{TAG_CANDIDATE_REF_PREFIX}/',
        ]
        try:
            output = subprocess.run(
                command, capture_output=True, text=True, check=False,
            )
        except OSError as exc:
            _logger.warning('Failed to enumerate candidate refs for %s: %s', clone_dir, exc)
            return
        if output.returncode != 0 or not output.stdout.strip():
            return
        delete_command = ['git', '-C', str(clone_dir), 'update-ref', '--stdin']
        try:
            subprocess.run(
                delete_command, input=output.stdout, text=True,
                capture_output=True, check=True,
            )
            _logger.debug(
                'Cleaned up stale tag candidate refs in %s', clone_dir,
            )
        except (subprocess.CalledProcessError, OSError) as exc:
            _logger.warning(
                'Failed to clean up candidate refs for %s: %s', clone_dir, exc,
            )

    @staticmethod
    def _cleanup_orphaned_tmp_packs(clone_dir: Path) -> None:
        """Delete ``tmp_pack_*`` leftovers from interrupted fetch transfers.

        Git streams incoming pack data into a ``tmp_pack_XXXXXX`` file and
        renames it only after a successful transfer; a timeout or kill leaves
        the partial file behind forever.  These orphans are never referenced
        by any index, so removing them is safe as long as no fetch for this
        repository is concurrently running.
        """
        pack_directory = clone_dir / '.git' / 'objects' / 'pack'
        if not pack_directory.is_dir():
            return
        for entry in pack_directory.glob('tmp_pack_*'):
            try:
                entry.unlink()
                _logger.info('Removed orphaned pack file %s', entry)
            except OSError as exc:
                _logger.warning('Failed to remove orphaned pack file %s: %s', entry, exc)

    # ── GitHub auth ────────────────────────────────────────────────

    @staticmethod
    def _load_github_token() -> str | None:
        token = settings.crawler.github_token.strip()
        return token or None

    @staticmethod
    def _load_github_username() -> str | None:
        username = settings.crawler.github_username.strip()
        return username or 'git'

    @staticmethod
    def _load_max_tags_per_repo() -> int:
        parsed = int(settings.crawler.max_tags_per_repo)
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

    def _mask_github_token(
        self,
        value: str | bytes | None,
    ) -> str | None:
        if value is None:
            return None
        text = value.decode(errors='replace') if isinstance(value, bytes) else value
        if not self.github_token:
            return text
        return text.replace(self.github_token, '***')

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
