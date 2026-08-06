#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skillcrawler.config import load_crawler_config, normalize_dict_keys
from skillcrawler.core.category_classifier import CategoryClassificationError
from skillcrawler.core.skill_manager import SkillManager, SkillRepositoryRequest
from src.core.config import get_settings
from src.core.database import get_db_context
from src.models.repository import SkillRepoRepository, SkillRepository

settings = get_settings()

_LOG_DIR = Path(settings.storage.local_path).expanduser().resolve() / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_LEVEL = getattr(logging, settings.logging.level.strip().upper(), logging.INFO)

logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_LOG_DIR / "skillcrawler.log"),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_KEYS = ["openeuler_repos", "personal_repos", "enterprise_repos"]
PLATFORM_CONFIG_KEYS = {
    "enterprise": "enterprise_repos",
    "enterprise_repos": "enterprise_repos",
    "openeuler": "openeuler_repos",
    "openeuler_repos": "openeuler_repos",
    "personal": "personal_repos",
    "personal_repos": "personal_repos",
}
PLATFORM_CHOICES = list(PLATFORM_CONFIG_KEYS)

DISCOVER_RESULT_COLUMNS = [
    ("#", "#", 5),
    ("result", "result", 14),
    ("status", "status", 16),
    ("skills", "skills", 8),
    ("name", "name", 36),
    ("url", "url", 64),
    ("error", "error", 80),
]


def _build_requests_from_config(
    config_path: Path | None,
    key: str,
    platform: str,
    *,
    allow_empty: bool = False,
) -> list[SkillRepositoryRequest]:
    """Read url entries from <key> in config."""
    config = load_crawler_config(config_path)
    urls = config.get(key)
    if not isinstance(urls, list) or not urls:
        if allow_empty and (urls == [] or urls is None):
            return []
        raise ValueError(f"No {key} entries found in config")

    seen: set[str] = set()
    requests: list[SkillRepositoryRequest] = []
    for item in urls:
        if hasattr(item, "model_dump"):
            normalized_item = item.model_dump()
        elif isinstance(item, dict):
            normalized_item = normalize_dict_keys(item)
        else:
            raise ValueError(f"Invalid entry in {key}: {item!r}")
        url = normalized_item.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"Invalid url entry in {key}: {item!r}")
        url = url.strip()
        if url in seen:
            continue
        seen.add(url)
        branch = normalized_item.get("branch") or None
        requests.append(
            SkillRepositoryRequest(
                url=url,
                branch=branch,
                platform=platform,
            )
        )
    return requests


def _platform_for_config_key(key: str) -> str:
    return key.removesuffix("_repos")


def _config_key_for_platform(platform: str) -> str:
    normalized = platform.strip().lower()
    if normalized not in PLATFORM_CONFIG_KEYS:
        raise ValueError(
            f"Unsupported platform {platform!r}; expected enterprise, openeuler, or personal"
        )
    return PLATFORM_CONFIG_KEYS[normalized]


def _config_keys_for_platform(platform: str | None) -> list[str]:
    if platform is None:
        return list(DEFAULT_CONFIG_KEYS)
    return [_config_key_for_platform(platform)]


def _format_skill_repo(repository: Any) -> str:
    display_name = _display_skill_repo_name(repository)
    return (
        f"repo_id={repository.id} "
        f"repo_name={display_name} "
        f"source={repository.source} "
        f"platform={repository.platform or '-'} "
        f"branch={repository.branch} "
        f"repo_url={repository.url} "
        f"status={repository.skill_discover_status} "
        f"skill_num={repository.skill_num}"
    )


def _display_skill_repo_name(repository: Any) -> str:
    repo_name = str(repository.repo_name or "")
    branch = str(repository.branch or "").strip()
    if branch and repo_name.endswith(f"@{branch}"):
        return repo_name[: -(len(branch) + 1)]
    return repo_name or "-"


def _format_exception(exc: Exception) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        return _format_process_error(exc)
    if isinstance(exc, subprocess.TimeoutExpired):
        return _format_timeout_error(exc)

    message = str(exc).strip()
    cause = exc.__cause__
    if isinstance(cause, subprocess.CalledProcessError):
        detail = _format_process_error(cause)
        return f"{message}\nCaused by:\n{detail}" if message else detail
    if isinstance(cause, subprocess.TimeoutExpired):
        detail = _format_timeout_error(cause)
        return f"{message}\nCaused by:\n{detail}" if message else detail

    if message:
        return message
    if cause is not None:
        cause_message = str(cause).strip()
        if cause_message:
            return cause_message
    return exc.__class__.__name__


def _format_process_error(exc: subprocess.CalledProcessError) -> str:
    lines = [
        f"Command failed with exit code {exc.returncode}: {_format_command(exc.cmd)}"
    ]
    stdout = str(exc.output or "").strip()
    stderr = str(exc.stderr or "").strip()
    if stdout:
        lines.append(f"stdout:\n{stdout}")
    if stderr:
        lines.append(f"stderr:\n{stderr}")
    if not stdout and not stderr:
        fallback = str(exc).strip()
        if fallback:
            lines.append(fallback)
    return "\n".join(lines)


def _format_timeout_error(exc: subprocess.TimeoutExpired) -> str:
    lines = [
        f"Command timed out after {exc.timeout}s: {_format_command(exc.cmd)}"
    ]
    stdout = str(exc.output or "").strip()
    stderr = str(exc.stderr or "").strip()
    if stdout:
        lines.append(f"stdout:\n{stdout}")
    if stderr:
        lines.append(f"stderr:\n{stderr}")
    return "\n".join(lines)


def _format_command(command: Any) -> str:
    if isinstance(command, (list, tuple)):
        return " ".join(str(part) for part in command)
    return str(command)


def _print_failure_details(failures: list[dict[str, str]]) -> None:
    if not failures:
        return
    print()
    logger.error("Failure details:")
    for failure in failures:
        logger.error("[%s] %s", failure['#'], failure['url'])
        logger.error("%s", failure["error"])
        print()


def _print_failure_detail(index: str, url: str, error: str) -> None:
    logger.error("[%s] failed: %s", index, url)
    logger.error("%s", error)
    print()


def _build_cli_error(action: str, message: str, tip: str | None = None) -> ValueError:
    lines = [f"{action} Error: {message}"]
    if tip:
        lines.append(f"Tip: {tip}")
    return ValueError("\n".join(lines))


def _status_counts(repositories: list[Any]) -> OrderedDict[str, int]:
    counts: OrderedDict[str, int] = OrderedDict()
    for repository in repositories:
        status = str(repository.skill_discover_status or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _clip(value: Any, max_width: int) -> str:
    text = str(value or "-")
    if len(text) <= max_width:
        return text
    if max_width <= 3:
        return text[:max_width]
    return text[: max_width - 3] + "..."


def _print_table(
    rows: list[dict[str, str]],
    columns: list[tuple[str, str, int]],
    *,
    empty_message: str,
) -> None:
    if not rows:
        print(empty_message)
        return

    normalized_rows = [
        {
            key: _clip(row.get(key, "-"), max_width)
            for key, _, max_width in columns
        }
        for row in rows
    ]
    widths = {
        key: max(len(label), *(len(row[key]) for row in normalized_rows))
        for key, label, _ in columns
    }

    header = "  ".join(label.ljust(widths[key]) for key, label, _ in columns)
    separator = "  ".join("-" * widths[key] for key, _, _ in columns)
    print(header)
    print(separator)
    for row in normalized_rows:
        print("  ".join(row[key].ljust(widths[key]) for key, _, _ in columns))


def _print_repository_table(repositories: list[Any]) -> None:
    if not repositories:
        print("No skill repos found.")
        return

    rows: list[dict[str, str]] = []
    for repository in repositories:
        rows.append(
            {
                "id": str(repository.id),
                "status": str(repository.skill_discover_status or ""),
                "skills": str(repository.skill_num),
                "platform": repository.platform or "-",
                "branch": repository.branch or "-",
                "name": _display_skill_repo_name(repository),
                "url": repository.url or "-",
            }
        )

    _print_table(
        rows,
        [
            ("id", "repo_id", 36),
            ("status", "repo_status", 16),
            ("skills", "skill_count", 11),
            ("platform", "platform", 12),
            ("branch", "branch", 18),
            ("name", "repo_name", 36),
            ("url", "repo_url", 80),
        ],
        empty_message="No skill repos found.",
    )

    counts = _status_counts(repositories)
    summary = ", ".join(f"{status}={count}" for status, count in counts.items())
    print()
    print(f"Total: {len(repositories)} skill repos")
    print(f"Statuses: {summary}")


async def _run_query(manager: "SkillManager", args: argparse.Namespace) -> int:
    if args.id:
        repository = await manager.get_repository_by_id(args.id)
        logger.info("%s", _format_skill_repo(repository))
        return 0

    repositories = await manager.list_skill_repositories()
    _print_repository_table(repositories)
    return 0


async def _discover_repositories_from_requests(
    manager: "SkillManager",
    requests: list[SkillRepositoryRequest],
    *,
    source_label: str = "",
) -> int:
    total = len(requests)
    created_count = 0
    rediscovered_count = 0
    unchanged_count = 0
    removed_count = 0
    skipped_no_skill = 0
    failed_count = 0
    fatal_error = False
    result_rows: list[dict[str, str]] = []
    failure_details: list[dict[str, str]] = []

    logger.info("Preparing to discover %d repos%s for SKILL.md", total, source_label)

    for index, request in enumerate(requests, start=1):
        label = request.url or "<missing-url>"
        logger.info("[%d/%d] scanning %s", index, total, label)

        try:
            result = await manager.discover_configured_skill_repository(request)
            if result is None:
                skipped_no_skill += 1
                result_rows.append(
                    {
                        "#": str(index),
                        "result": "no_skill",
                        "status": "-",
                        "skills": "0",
                        "name": "-",
                        "url": label,
                        "error": "SKILL.md not found",
                    }
                )
            elif getattr(result, "_removed_existing", False):
                removed_count += 1
                result_rows.append(
                    {
                        "#": str(index),
                        "result": "removed",
                        "status": "deleted",
                        "skills": str(result.skill_num),
                        "name": _display_skill_repo_name(result),
                        "url": result.url or label,
                        "error": "SKILL.md not found",
                    }
                )
            elif getattr(result, "_unchanged", False):
                unchanged_count += 1
                result_rows.append(
                    {
                        "#": str(index),
                        "result": "unchanged",
                        "status": str(result.skill_discover_status or "-"),
                        "skills": str(result.skill_num),
                        "name": _display_skill_repo_name(result),
                        "url": result.url or label,
                        "error": "commit unchanged",
                    }
                )
            else:
                if getattr(result, "_created_new", False):
                    created_count += 1
                    row_result = "created"
                else:
                    rediscovered_count += 1
                    row_result = "rediscovered"
                result_rows.append(
                    {
                        "#": str(index),
                        "result": row_result,
                        "status": str(result.skill_discover_status or "-"),
                        "skills": str(result.skill_num),
                        "name": _display_skill_repo_name(result),
                        "url": result.url or label,
                        "error": "-",
                    }
                )
        except Exception as exc:
            await manager.rollback()
            failed_count += 1
            fatal_error = isinstance(exc, CategoryClassificationError)
            error = _format_exception(exc)
            _print_failure_detail(str(index), label, error)
            result_rows.append(
                {
                    "#": str(index),
                    "result": "failed",
                    "status": "-",
                    "skills": "-",
                    "name": "-",
                    "url": label,
                    "error": error,
                }
            )
            failure_details.append(
                {
                    "#": str(index),
                    "url": label,
                    "error": error,
                }
            )
            if fatal_error:
                break

    print()
    _print_table(
        result_rows,
        DISCOVER_RESULT_COLUMNS,
        empty_message="No repos discovered.",
    )
    _print_failure_details(failure_details)
    print()
    logger.info(
        "Discover summary: total=%d created=%d rediscovered=%d unchanged=%d removed=%d no_skill=%d failed=%d",
        total, created_count, rediscovered_count, unchanged_count,
        removed_count, skipped_no_skill, failed_count,
    )

    return 1 if fatal_error else 0


def _platform_from_cli_value(platform: str | None) -> str | None:
    if not platform:
        return None
    return _platform_for_config_key(_config_key_for_platform(platform))


def _infer_platform_from_repo_url(repo_url: str | None) -> str | None:
    if not repo_url:
        return None
    parsed = urlparse(repo_url.strip())
    if parsed.netloc.lower() != "gitcode.com":
        return None
    path_parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(path_parts) >= 2 and path_parts[0].lower() == "openeuler":
        return "openeuler"
    return None


def _build_single_url_discover_request(
    args: argparse.Namespace,
) -> SkillRepositoryRequest:
    platform = (
        _platform_from_cli_value(args.platform)
        or _infer_platform_from_repo_url(args.url)
    )
    return SkillRepositoryRequest(
        url=args.url,
        branch=args.branch,
        platform=platform,
    )


def _build_configured_discover_requests(
    args: argparse.Namespace,
) -> tuple[list[SkillRepositoryRequest], list[str]]:
    config_path = Path(args.config) if args.config else None
    config_keys = _config_keys_for_platform(args.platform)
    requests: list[SkillRepositoryRequest] = []
    seen_urls: set[str] = set()

    for config_key in config_keys:
        platform = _platform_for_config_key(config_key)
        for request in _build_requests_from_config(
            config_path,
            config_key,
            platform,
            allow_empty=args.platform is None,
        ):
            if request.url in seen_urls:
                continue
            seen_urls.add(request.url)
            requests.append(request)

    return requests, config_keys


async def _get_refresh_target_repositories(
    manager: "SkillManager",
    platform: str | None,
) -> list[Any]:
    repositories = await manager.list_skill_repositories()
    return [
        repository
        for repository in repositories
        if platform is None or repository.platform == platform
    ]


async def _discover_single_existing_repository(
    manager: "SkillManager",
    repo_id: str,
    *,
    force: bool,
) -> int:
    repository = await manager.discover_skills_from_single_existing_repository(repo_id, force=force)
    _print_table(
        [_successful_existing_repository_row("1", repository)],
        DISCOVER_RESULT_COLUMNS,
        empty_message="No skill repos to discover.",
    )
    print()
    logger.info("Discover summary: total=1 success=1 failed=0 skipped=0")
    return 0


async def _refresh_existing_repositories(
    manager: "SkillManager",
    repositories: list[Any],
    *,
    force: bool,
    source_label: str = "",
) -> int:
    total = len(repositories)
    success_count = 0
    failed_count = 0
    skipped_count = 0
    fatal_error = False
    result_rows: list[dict[str, str]] = []
    failure_details: list[dict[str, str]] = []

    logger.info("Preparing to refresh existing skill repos%s: total=%d", source_label, total)

    for index, repository in enumerate(repositories, start=1):
        logger.info("[%d/%d] discover %s", index, total, _display_skill_repo_name(repository))
        if not force and repository.skill_discover_status == "discovering":
            skipped_count += 1
            result_rows.append(_skipped_existing_repository_row(str(index), repository))
            continue

        try:
            refreshed = await manager.discover_skills_from_single_existing_repository(
                str(repository.id),
                force=force,
            )
            success_count += 1
            result_rows.append(
                _successful_existing_repository_row(str(index), refreshed)
            )
        except Exception as exc:
            await manager.rollback()
            failed_count += 1
            fatal_error = isinstance(exc, CategoryClassificationError)
            error = _format_exception(exc)
            _print_failure_detail(str(index), repository.url or "-", error)
            result_rows.append(_failed_existing_repository_row(str(index), repository, error))
            failure_details.append(
                {
                    "#": str(index),
                    "url": repository.url or "-",
                    "error": error,
                }
            )
            if fatal_error:
                break

    print()
    _print_table(
        result_rows,
        DISCOVER_RESULT_COLUMNS,
        empty_message="No skill repos to discover.",
    )
    _print_failure_details(failure_details)
    print()
    logger.info(
        "Discover summary: total=%d success=%d failed=%d skipped=%d",
        total, success_count, failed_count, skipped_count,
    )
    return 1 if fatal_error else 0


def _successful_existing_repository_row(index: str, repository: Any) -> dict[str, str]:
    return {
        "#": index,
        "result": "success",
        "status": str(repository.skill_discover_status or "-"),
        "skills": str(repository.skill_num),
        "name": _display_skill_repo_name(repository),
        "url": repository.url or "-",
        "error": "-",
    }


def _skipped_existing_repository_row(index: str, repository: Any) -> dict[str, str]:
    return {
        "#": index,
        "result": "skipped",
        "status": str(repository.skill_discover_status or "-"),
        "skills": str(repository.skill_num),
        "name": _display_skill_repo_name(repository),
        "url": repository.url or "-",
        "error": "already discovering",
    }


def _failed_existing_repository_row(
    index: str,
    repository: Any,
    error: str,
) -> dict[str, str]:
    return {
        "#": index,
        "result": "failed",
        "status": str(repository.skill_discover_status or "-"),
        "skills": str(repository.skill_num),
        "name": _display_skill_repo_name(repository),
        "url": repository.url or "-",
        "error": error,
    }


async def _run_discover(manager: "SkillManager", args: argparse.Namespace) -> int:
    if args.id:
        return await _run_discover_existing_repo_by_id(manager, args)
    if args.url:
        return await _run_discover_single_url(manager, args)
    if args.refresh:
        return await _run_refresh_existing_repos(manager, args)
    return await _run_discover_from_config(manager, args)


async def _run_discover_single_url(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> int:
    if args.refresh:
        raise _build_cli_error(
            "discover",
            "--refresh cannot be used with --url",
            "python main.py discover --url \"https://example.com/repo\"",
        )
    if args.config:
        raise _build_cli_error(
            "discover",
            "--config cannot be used with --url",
            "python main.py discover --url \"https://example.com/repo\"",
        )
    request = _build_single_url_discover_request(args)
    return await _discover_repositories_from_requests(
        manager,
        [request],
    )


async def _run_discover_from_config(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> int:
    if args.branch:
        raise _build_cli_error(
            "discover",
            "--branch requires --url for discover",
            "python main.py discover --url \"https://example.com/repo\" --branch main",
        )

    requests, config_keys = _build_configured_discover_requests(args)
    return await _discover_repositories_from_requests(
        manager,
        requests,
        source_label=f" from {', '.join(config_keys)}",
    )


async def _run_refresh_existing_repos(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> int:
    if args.config:
        raise _build_cli_error(
            "discover",
            "--config cannot be used with --refresh",
            "python main.py discover --refresh",
        )
    if args.branch:
        raise _build_cli_error(
            "discover",
            "--branch requires --url for discover",
            "python main.py discover --url \"https://example.com/repo\" --branch main",
        )

    platform = _platform_from_cli_value(args.platform)
    repositories = await _get_refresh_target_repositories(manager, platform)
    source_label = f" platform={platform}" if platform else ""
    return await _refresh_existing_repositories(
        manager,
        repositories,
        force=args.force,
        source_label=source_label,
    )


async def _run_discover_existing_repo_by_id(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> int:
    if args.refresh:
        raise _build_cli_error(
            "discover",
            "--refresh cannot be used with --id",
            "python main.py discover --id <repo_id>",
        )

    if args.url or args.branch:
        raise _build_cli_error(
            "discover",
            "discover --id no longer supports --url/--branch; update skill repo config separately",
            "python main.py discover --id <repo_id>",
        )

    return await _discover_single_existing_repository(
        manager,
        args.id,
        force=args.force,
    )


async def _run_delete(manager: "SkillManager", args: argparse.Namespace) -> int:
    if not args.id:
        raise _build_cli_error(
            "delete",
            "--id is required for delete",
            "python main.py delete --id <repo_id>",
        )
    await manager.delete_skill_repository(args.id)
    logger.info("Deleted skill repo: id=%s", args.id)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage skill repository discovery.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    _add_query_parser(subparsers)
    _add_discover_parser(subparsers)
    _add_delete_parser(subparsers)
    return parser


def _add_query_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "query",
        help="Query skill repo records",
        description="Query skill repo records.",
    )
    parser.add_argument("-i", "--id", help="Skill repo ID to look up")


def _add_discover_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "discover",
        help="Register, clone, and scan skills from config or existing repos",
    )
    parser.add_argument("-i", "--id", help="Existing skill repo ID to rediscover")
    parser.add_argument("-u", "--url", help="Single Git repo URL to discover")
    parser.add_argument("-b", "--branch", help="Git branch to clone with --url")
    parser.add_argument(
        "-c",
        "--config",
        default=None,
        help="Repo list YAML path (default: skills/skill-repos.yaml)",
    )
    parser.add_argument(
        "-p",
        "--platform",
        choices=PLATFORM_CHOICES,
        default=None,
        help="Config repo list to read (default: all repo lists)",
    )
    parser.add_argument(
        "-f", "--force",
        dest="force",
        action="store_true",
        help="Force rediscover existing repos even when status is discovering",
    )
    parser.add_argument(
        "-r",
        "--refresh",
        dest="refresh",
        action="store_true",
        help="Refresh existing skill repos from the database instead of reading config",
    )


def _add_delete_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("delete", help="Delete a skill repo")
    parser.add_argument("-i", "--id", required=True, help="Skill repo ID to delete")


async def _main() -> int:
    args = _build_parser().parse_args()

    async with get_db_context() as session:
        skill_repository = SkillRepository(session)
        skill_repo_repository = SkillRepoRepository(session)
        manager = SkillManager(
            skill_repository=skill_repository,
            skill_repo_repository=skill_repo_repository,
        )

        if args.action == "query":
            return await _run_query(manager, args)
        if args.action == "discover":
            return await _run_discover(manager, args)
        if args.action == "delete":
            return await _run_delete(manager, args)
    raise ValueError(f"Unsupported action: {args.action}")


def main() -> int:
    """Run the async skill discovery CLI from a console-script or Python process."""
    try:
        return asyncio.run(_main())
    except KeyboardInterrupt:
        logger.warning("Canceled")
        return 130
    except Exception as exc:
        logger.error("%s", _format_exception(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
