#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skillcrawler.config import (
    load_catalog_skill_url_entries,
    load_crawler_config,
    load_single_catalog_entry,
    sync_openEuler_skills_repo,
)
from skillcrawler.core.category_classifier import CategoryClassificationError
from skillcrawler.core.popularity import (
    PopularityCollector,
    allocate_skill_downloads,
    estimate_repo_downloads,
)
from skillcrawler.core.skill_manager import SkillManager, SkillRepositoryRequest
from skillcrawler.core.skill_parser import normalize_git_clone_url, parse_skill_md_url
from src.core.config import get_settings
from src.core.database import get_db_context
from src.models.repository import (
    ContributorRepository,
    SkillRepoRepository,
    SkillRepository,
)

settings = get_settings()

_LOG_DIR = Path(settings.storage.local_path).expanduser().resolve() / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_LEVEL = getattr(logging, settings.logging.level.strip().upper(), logging.INFO)

logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(_LOG_DIR / "skillcrawler.log"),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

PLATFORM_CHOICES = ("community", "enterprise", "personal")


def _normalize_platform(platform: str) -> str:
    normalized = platform.strip().lower()
    if normalized not in PLATFORM_CHOICES:
        raise ValueError(
            f"Unsupported platform {platform!r}; expected community, enterprise, or personal"
        )
    return normalized

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
    repos_dict: dict[str, Any],
    platform: str,
    seen_urls: set[str] | None = None,
) -> list[SkillRepositoryRequest]:
    """Build requests for one catalog group from an already-loaded catalog."""
    platform_urls = repos_dict.get(platform)
    if not isinstance(platform_urls, list) or not platform_urls:
        logger.warning(f"Discover: No {platform} entries found in config")
        return []

    seen = seen_urls if seen_urls is not None else set()
    requests: list[SkillRepositoryRequest] = []
    for item in platform_urls:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid entry in {platform}: {item!r}")
        url = item.get("url")
        if not isinstance(url, str) or not url.strip():
            raise ValueError(f"Invalid url entry in {platform}: {item!r}")
        url = url.strip()
        if url in seen:
            continue
        seen.add(url)
        branch = item.get("branch") or None
        sig_name = item.get("sig_name") if platform == "community" else None
        if sig_name is not None:
            sig_name = str(sig_name).strip() or None
        requests.append(
            SkillRepositoryRequest(
                url=url,
                branch=branch,
                platform=platform,
                sig_name=sig_name,
            )
        )
    return requests


def _build_requests_from_skill_urls(
    entries: list[dict[str, Any]],
    platform_keys: list[str],
    covered_urls: set[str],
) -> list[SkillRepositoryRequest]:
    """把 catalog 的 skills[].skill_url 单 Skill 贡献合并为收窄扫描请求。

    - 按规范化 repo URL 分组：同一仓库多条贡献合并为一个请求、路径取并集
      （部分扫描按请求同步入库，拆成多个请求会互相删掉对方的 skill）；
    - 同一仓库的多条贡献必须同 ref（/blob/ 后第一段，约定为分支名），
      否则无法消歧，抛 ValueError；
    - 仓库已被 skill_repos 整仓登记（covered_urls 命中）时跳过，整仓扫描
      已覆盖该 skill；
    - skill_name / skill_url 均必填（openEuler-skills README 的 URL 贡献约定）。
    """
    covered = {normalize_git_clone_url(url) for url in covered_urls}
    grouped: dict[str, dict[str, Any]] = {}
    for item in entries:
        platform = str(item.get("platform") or "").strip()
        if platform not in platform_keys:
            continue
        skill_name = str(item.get("skill_name") or "").strip()
        skill_url = str(item.get("skill_url") or "").strip()
        if not skill_name or not skill_url:
            raise ValueError(
                f"Invalid skills entry in {platform} (skill_name and skill_url "
                f"are required): {item!r}"
            )
        repo_url, ref, skill_path = parse_skill_md_url(skill_url)
        if repo_url in covered:
            continue
        group = grouped.get(repo_url)
        if group is None:
            grouped[repo_url] = {
                "branch": ref,
                "platform": platform,
                "sig_name": str(item.get("owner") or "").strip()
                if platform == "community"
                else None,
                "skill_paths": {skill_path},
            }
        elif group["branch"] != ref:
            raise ValueError(
                f"skill_url entries for {repo_url} must share one ref, "
                f"got {group['branch']!r} and {ref!r}"
            )
        else:
            group["skill_paths"].add(skill_path)

    return [
        SkillRepositoryRequest(
            url=repo_url,
            branch=group["branch"],
            platform=group["platform"],
            sig_name=group["sig_name"],
            skill_paths=sorted(group["skill_paths"]),
        )
        for repo_url, group in grouped.items()
    ]


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
    config_keys: list[str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """逐仓库执行 discover，输出表格，返回 (退出码, 本轮运行数据)。

    运行数据供 `_run_discover` 在补建 embedding 后构建结果 JSON（与自动
    调度输出完全对齐）。
    """
    total = len(requests)
    counters = {
        "created": 0,
        "rediscovered": 0,
        "security_retried": 0,
        "unchanged": 0,
        "removed": 0,
        "no_skill": 0,
        "failed": 0,
    }
    fatal_error = False
    result_rows: list[dict[str, str]] = []
    failure_details: list[dict[str, str]] = []
    repo_details: list[dict[str, Any]] = []
    run_started = time.monotonic()
    started_at = datetime.now()

    logger.info("Preparing to discover %d repos%s for SKILL.md", total, source_label)

    for index, request in enumerate(requests, start=1):
        label = request.url or "<missing-url>"
        logger.info("[%d/%d] scanning %s", index, total, label)
        repo_started = time.monotonic()

        try:
            result = await manager.discover_configured_skill_repository(request)
        except Exception as exc:
            elapsed = time.monotonic() - repo_started
            await manager.rollback()
            counters["failed"] += 1
            fatal_error = isinstance(exc, CategoryClassificationError)
            error = _format_exception(exc)
            repo_details.append(
                {
                    "url": label,
                    "outcome": "failed",
                    "skill_num": 0,
                    "duration_seconds": round(elapsed, 3),
                    "error": error,
                }
            )
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
            continue

        elapsed = time.monotonic() - repo_started
        # outcome 口径与自动调度共用（classify_discover_result）
        outcome = classify_discover_result(result)
        counters[outcome] += 1
        repo_details.append(
            {
                "url": label,
                "outcome": outcome,
                "skill_num": getattr(result, "skill_num", 0) or 0,
                "duration_seconds": round(elapsed, 3),
            }
        )

        if outcome == "no_skill":
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
        elif outcome == "removed":
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
        elif outcome == "security_retried":
            candidates = int(getattr(result, "_security_retry_candidates", 0))
            triggered = int(getattr(result, "_security_retriggered", 0))
            result_rows.append(
                {
                    "#": str(index),
                    "result": "security_retried",
                    "status": str(result.skill_discover_status or "-"),
                    "skills": str(result.skill_num),
                    "name": _display_skill_repo_name(result),
                    "url": result.url or label,
                    "error": f"commit unchanged; triggered {triggered}/{candidates}",
                }
            )
        elif outcome == "unchanged":
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
            result_rows.append(
                {
                    "#": str(index),
                    "result": outcome,
                    "status": str(result.skill_discover_status or "-"),
                    "skills": str(result.skill_num),
                    "name": _display_skill_repo_name(result),
                    "url": result.url or label,
                    "error": "-",
                }
            )

    print()
    _print_table(
        result_rows,
        DISCOVER_RESULT_COLUMNS,
        empty_message="No repos discovered.",
    )
    _print_failure_details(failure_details)
    print()
    logger.info(
        "Discover summary: total=%d created=%d rediscovered=%d security_retried=%d "
        "unchanged=%d removed=%d no_skill=%d failed=%d",
        total,
        counters["created"],
        counters["rediscovered"],
        counters["security_retried"],
        counters["unchanged"],
        counters["removed"],
        counters["no_skill"],
        counters["failed"],
    )

    run_data = {
        "started_at": started_at,
        "run_started": run_started,
        "total_repos": total,
        "config_keys": list(config_keys or []),
        "counters": counters,
        "repo_details": repo_details,
    }
    return (1 if counters["failed"] else 0), run_data


def _build_requests_from_skill_yaml(skill_yaml: str) -> list[SkillRepositoryRequest]:
    """从单个 skill.yaml 构建 discover 请求（``--url`` 单文件模式）。

    与全量构建同口径：``skill_repos`` 整仓条目 + ``skills[].skill_url`` 单
    Skill 收窄请求（整仓登记覆盖同文件的 skills[] 条目）；platform / owner
    取自文件目录结构（不再由 URL 推断）。路径先按本地文件解析，不存在时按
    catalog 根（``-r`` / 自动同步）解析。
    """
    resolved = Path(skill_yaml).expanduser()
    if not resolved.is_file():
        resolved = (sync_openEuler_skills_repo() / skill_yaml).expanduser()
    platform, owner, entry = load_single_catalog_entry(resolved)

    seen_urls: set[str] = set()
    repos = entry.get("skill_repos", [])
    enriched: list[Any] = []
    if isinstance(repos, list):
        for repo in repos:
            if isinstance(repo, dict):
                repo = dict(repo)
                if platform == "community":
                    repo.setdefault("sig_name", owner)
            enriched.append(repo)
    requests = _build_requests_from_config({platform: enriched}, platform, seen_urls)

    skill_entries = [
        {
            "platform": platform,
            "owner": owner,
            "skill_name": skill.get("skill_name"),
            "skill_url": skill.get("skill_url"),
        }
        for skill in (entry.get("skills") or [])
        if isinstance(skill, dict)
    ]
    requests.extend(_build_requests_from_skill_urls(skill_entries, [platform], seen_urls))
    return requests


def build_configured_discover_requests(
    platform: str | None = None,
    repository_path: Path | None = None,
) -> tuple[list[SkillRepositoryRequest], list[str]]:
    """从 openEuler-skills catalog（或显式覆盖配置）构建 discover 请求列表。

    供 CLI discover 与后台定时调度共用：读取全部三个 key
    （community / personal / enterprise）并按 URL 去重。
    指定 platform 时仅读取对应 key 且要求非空；否则每个 key 都允许为空。
    """
    # The default source is the openEuler-skills catalog repository.
    if repository_path is not None:
        repository_path = repository_path.expanduser()
        if not repository_path.exists():
            raise ValueError(f"openEuler-skills repository path does not exist: {repository_path}")
        if not repository_path.is_dir():
            raise ValueError(f"openEuler-skills repository path is not a directory: {repository_path}")
    else:
        repository_path = sync_openEuler_skills_repo()
    repos_dict = load_crawler_config(repository_path)

    if platform is None:
        platform_keys = list(PLATFORM_CHOICES)
    else:
        platform_keys = [_normalize_platform(platform)]

    requests: list[SkillRepositoryRequest] = []
    seen_urls: set[str] = set()
    for platform in platform_keys:
        requests.extend(
            _build_requests_from_config(
                repos_dict,
                platform,
                seen_urls,
            )
        )

    # URL 方式贡献（skills[].skill_url）：整仓登记覆盖不到的单 Skill，
    # 按仓库分组合并为收窄扫描请求（skill_paths 只收录登记的 SKILL.md）
    requests.extend(
        _build_requests_from_skill_urls(
            load_catalog_skill_url_entries(repository_path),
            platform_keys,
            seen_urls,
        )
    )

    return requests, platform_keys


# ============ discover 结果 JSON（CLI 与自动调度共用，口径完全一致） ============

# counters 各项含义，随结果文件内嵌为 <key>_note，便于离线解读（与设计文档 §11 口径一致）
COUNTER_NOTES: dict[str, str] = {
    "created": "新建仓库记录并完成扫描",
    "rediscovered": "已有仓库 commit 变化并完成重扫",
    "security_retried": "commit 未变化，但为 NULL risk_score 记录重新提交安全检测",
    "unchanged": "HEAD commit 与数据库相同，跳过扫描",
    "removed": "已有仓库不再包含可扫描 Skill，删除 DB 仓库记录",
    "no_skill": "新仓库没有可扫描 Skill，不创建 DB 仓库记录",
    "failed": "当前仓库处理失败（clone/fetch 或扫描异常），详见 repos[].error",
}

# skill_stats / embedding_run 各项含义，同样以 <key>_note 内嵌输出（与设计文档 §11 口径一致）
SKILL_STATS_NOTES: dict[str, str] = {
    "total_skills": "skills 表 Skill 总数（latest Skill，不含 Tag 版本）",
    "category_distribution": "分类分布 {category: count}，按数量降序；NULL / 空 / other / others 统一归入 others",
    "security_audit": "安全检测结果，各子项含义见其 <key>_note",
    "index_creation": "索引创建状态（互斥三分法，indexed + missing + not_required = total），各子项含义见其 <key>_note",
}
SECURITY_AUDIT_NOTES: dict[str, str] = {
    "audited": "安全检测完成（risk_score 非空）的 Skill 数",
    "pending": "异步检测进行中（有 skillspector_collected 为空的检测记录）的 Skill 数",
    "failed": "安全检测失败：risk_score 为空且无异步检测进行中",
    "failed_skills": "失败明细（skill_id / name / source_url），最多 50 条",
    "failed_skills_truncated": "失败明细被截断标记（超出 50 条只计数不列明细）",
}
INDEX_CREATION_NOTES: dict[str, str] = {
    "total": "skills 表 Skill 总数",
    "indexed": "已建 embedding 的 Skill 数（不论是否已审计）",
    "missing": "已审计但 embedding 缺失的 Skill 数（索引创建失败，等下轮 discover 或 API 启动补跑自愈）",
    "not_required": "未审计且未建索引（risk_score 与 embedding 均为空）的 Skill 数，暂不建索引属预期状态",
}
EMBEDDING_RUN_NOTES: dict[str, str] = {
    "total": "本轮扫描到的待编码行数",
    "indexed": "本轮成功写入 embedding 的行数",
    "failed_batches": "embedding 请求或写库失败的批次数",
    "failed_rows": "embedding 请求或响应校验失败的行数",
    "skipped_empty": "文本为空被跳过的行数",
    "stale_skipped": "编码期间内容发生变化或记录消失的行数",
    "skipped": "本轮跳过补建的原因",
}


def _with_notes(data: dict[str, Any], notes: dict[str, str]) -> dict[str, Any]:
    """每个 <key> 后补 <key>_note 说明，便于离线解读（与 counters 同风格）。"""
    merged: dict[str, Any] = {}
    for key, value in data.items():
        merged[key] = value
        merged[f"{key}_note"] = notes.get(key, "")
    return merged


def skill_stats_with_notes(skill_stats: dict[str, Any]) -> dict[str, Any]:
    """skill_stats 输出前补 <key>_note，security_audit / index_creation 子对象同样补。"""
    merged = _with_notes(skill_stats, SKILL_STATS_NOTES)
    security = skill_stats.get("security_audit")
    if isinstance(security, dict):
        merged["security_audit"] = _with_notes(security, SECURITY_AUDIT_NOTES)
    index = skill_stats.get("index_creation")
    if isinstance(index, dict):
        merged["index_creation"] = _with_notes(index, INDEX_CREATION_NOTES)
    return merged


# security_audits 中「异步检测仍在进行」的判定条件（JSONB 字段，无外键，
# resource_type='skill' + resource_id 关联 skills.id / skill_versions.id）
_PENDING_ASYNC_AUDIT_EXISTS = """
EXISTS (
    SELECT 1 FROM security_audits a
    WHERE a.resource_type = 'skill' AND a.resource_id = skills.id
      AND coalesce((a.details ->> 'skillspector_async')::boolean, false)
      AND a.details ->> 'skillspector_collected' IS NULL
)
"""
_NO_PENDING_ASYNC_AUDIT = f"NOT ({_PENDING_ASYNC_AUDIT_EXISTS})"

# 安全检测失败 skill_id 列表的输出上限，避免结果文件过大
FAILED_SKILL_IDS_LIMIT = 50


async def collect_skill_stats(session: Any) -> dict[str, Any]:
    """skill 级统计：分类分布、安全检测结果、索引创建状态。

    口径：以 skills 表（latest Skill）为准；skill_versions（Tag 版本）不计入。
    安全检测「失败」= risk_score 仍为空且无异步检测在进行（触发失败或终态
    无报告）；「进行中」= 存在 skillspector_collected 为空的异步检测记录。
    查询失败由调用方兜底，不影响主流程。
    """
    from sqlalchemy import case, func, select, text

    from src.models.orm import Skill

    # 1. 分类分布（NULL/空/other/others 统一归入 others）
    category_expr = func.lower(func.nullif(func.trim(Skill.category), ""))
    normalized_category = case(
        (category_expr.is_(None), "others"),
        (category_expr.in_(["other", "others"]), "others"),
        else_=category_expr,
    )
    category_rows = await session.execute(
        select(normalized_category.label("category_key"), func.count())
        .group_by("category_key")
        .order_by(func.count().desc())
    )
    category_distribution = {
        row.category_key: row[1] for row in category_rows.fetchall()
    }

    # 2. 安全检测：按 risk_score 是否就绪 + 是否有异步检测进行中拆分
    security_rows = await session.execute(
        select(
            func.count(),
            func.count().filter(Skill.risk_score.is_not(None)),
            func.count().filter(
                Skill.risk_score.is_(None),
                text(_PENDING_ASYNC_AUDIT_EXISTS),
            ),
        )
    )
    total_skills, audited, security_pending = security_rows.one()
    security_failed = total_skills - audited - security_pending

    # 失败明细（上限 FAILED_SKILL_IDS_LIMIT 条，超出部分只计数）
    failed_rows = await session.execute(
        select(Skill.skill_id, Skill.name, Skill.source_url)
        .where(
            Skill.risk_score.is_(None),
            text(_NO_PENDING_ASYNC_AUDIT),
        )
        .order_by(Skill.skill_id)
        .limit(FAILED_SKILL_IDS_LIMIT)
    )
    security_failed_skills = [
        {"skill_id": row.skill_id, "name": row.name, "source_url": row.source_url}
        for row in failed_rows.fetchall()
    ]

    # 3. 索引创建（embedding）：indexed / missing / not_required 为互斥三分法，
    #    各项之和恒等于 total。只有已审计（risk_score 非空）的行才会建索引，
    #    未审计且未建索引的 embedding 为空是预期状态，单列出来避免误判为失败。
    index_rows = await session.execute(
        select(
            func.count(),
            func.count().filter(Skill.embedding.is_not(None)),
            func.count().filter(
                Skill.embedding.is_(None), Skill.risk_score.is_not(None)
            ),
            func.count().filter(
                Skill.embedding.is_(None), Skill.risk_score.is_(None)
            ),
        )
    )
    index_total, indexed, index_missing, index_not_required = index_rows.one()

    return {
        "total_skills": total_skills,
        "category_distribution": category_distribution,
        "security_audit": {
            "audited": audited,
            "pending": security_pending,
            "failed": security_failed,
            "failed_skills": security_failed_skills,
            "failed_skills_truncated": security_failed > len(security_failed_skills),
        },
        "index_creation": {
            "total": index_total,
            "indexed": indexed,
            "missing": index_missing,
            "not_required": index_not_required,
        },
    }


def log_skill_stats(skill_stats: dict[str, Any]) -> None:
    """skill 统计输出到日志（多行结构化，便于排查时直接查看）。

    汇总一行 + 分类分布一行 + 安全检测失败明细逐条（上限
    FAILED_SKILL_IDS_LIMIT，超出只记总数），与结果文件同口径。
    """
    security = skill_stats.get("security_audit", {})
    index = skill_stats.get("index_creation", {})
    logger.info(
        "Skill stats after discover: total_skills=%s, security: audited=%s "
        "pending=%s failed=%s, index: total=%s indexed=%s missing=%s "
        "not_required=%s",
        skill_stats.get("total_skills"),
        security.get("audited"),
        security.get("pending"),
        security.get("failed"),
        index.get("total"),
        index.get("indexed"),
        index.get("missing"),
        index.get("not_required"),
    )
    category_distribution = skill_stats.get("category_distribution", {})
    if category_distribution:
        category_text = ", ".join(
            f"{name}={count}"
            for name, count in category_distribution.items()
        )
        logger.info("Skill category distribution: %s", category_text)
    failed_skills = security.get("failed_skills") or []
    for item in failed_skills:
        logger.warning(
            "Security audit failed skill: skill_id=%s name=%s source_url=%s",
            item.get("skill_id"),
            item.get("name"),
            item.get("source_url"),
        )
    if security.get("failed_skills_truncated"):
        logger.warning(
            "Security audit failed skills truncated: %s more not listed "
            "(limit=%d)",
            security.get("failed", 0) - len(failed_skills),
            FAILED_SKILL_IDS_LIMIT,
        )


def classify_discover_result(result: Any) -> str:
    """按 manager 标记的私有标志对单仓结果分类（CLI 与自动调度同口径）。"""
    if result is None:
        return "no_skill"
    if getattr(result, "_removed_existing", False):
        return "removed"
    if getattr(result, "_security_retry_candidates", 0):
        return "security_retried"
    if getattr(result, "_unchanged", False):
        return "unchanged"
    if getattr(result, "_created_new", False):
        return "created"
    return "rediscovered"


def resolve_discover_result_dir(result_dir: str = "") -> Path:
    """结果保存目录：优先显式 result_dir 配置，否则 storage.local_path/logs。"""
    if result_dir.strip():
        return Path(result_dir.strip()).expanduser()
    from src.core.config import get_settings

    configured = get_settings().discover_scheduler.result_dir.strip()
    if configured:
        return Path(configured).expanduser()
    return Path(get_settings().storage.local_path) / "logs"


def save_discover_result_file(
    document: dict[str, Any], result_dir: str = ""
) -> Path | None:
    """把一轮结果写入 JSON 文件；失败仅记录 warning，不影响主流程。"""
    try:
        target_dir = resolve_discover_result_dir(result_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = target_dir / f"discover-{timestamp}.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Discover result saved to %s", path)
        return path
    except Exception:
        logger.warning("Failed to save discover result file", exc_info=True)
        return None


def build_discover_result_document(
    *,
    started_at: datetime,
    run_started: float,
    total_repos: int,
    config_keys: list[str],
    counters: dict[str, int],
    repo_details: list[dict[str, Any]],
    embed_stats_dict: dict[str, Any] | None,
    skill_stats: dict[str, Any] | None,
) -> dict[str, Any]:
    """构建一轮 discover 的结果文档（CLI 与自动调度共用，口径完全一致）。

    skill_stats 由调用方采集传入（查询失败传 None）；counters / skill_stats /
    embedding_run 的每个字段均内嵌 <key>_note 说明。耗时与最慢仓库统计由
    repo_details 推导。
    """
    if skill_stats is not None:
        log_skill_stats(skill_stats)

    run_elapsed = time.monotonic() - run_started
    avg_elapsed = run_elapsed / total_repos if total_repos else 0.0
    durations = [
        (detail.get("url", ""), detail.get("duration_seconds", 0.0))
        for detail in repo_details
    ]
    slowest = sorted(durations, key=lambda item: item[1], reverse=True)[:3]

    return {
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "total_repos": total_repos,
        "config_keys": config_keys,
        "counters": _with_notes(counters, COUNTER_NOTES),
        "skill_stats": skill_stats_with_notes(skill_stats)
        if skill_stats is not None
        else None,
        "embedding_run": _with_notes(embed_stats_dict, EMBEDDING_RUN_NOTES)
        if embed_stats_dict is not None
        else None,
        "total_seconds": round(run_elapsed, 3),
        "avg_seconds_per_repo": round(avg_elapsed, 3),
        "slowest_repos": [
            {"url": label, "seconds": round(duration, 3)}
            for label, duration in slowest
        ],
        "repos": repo_details,
    }


async def _backfill_embeddings_after_discover() -> dict[str, Any] | None:
    """扫描结束后补建缺失 embedding（索引创建），返回本轮执行结果。

    只为 `embedding IS NULL` 且 `risk_score` 就绪的行生成向量，使其立即可被
    语义搜索命中；与全量重建脚本 `scripts/reindex_embeddings.py` 通过
    `pg_advisory_lock` 互斥，锁被占用时跳过（全量本身覆盖一切）。语义搜索
    未启用时跳过（返回 None）。失败只记录日志不重试，漏掉的行由下轮
    discover 或 API 启动时的 `_backfill_embeddings()` 自愈。
    """
    if not get_settings().ai.enable_semantic_search:
        logger.info("Incremental embedding skipped: semantic search disabled")
        return None

    from src.ai.embedding_indexer import LockBusyError, embed_missing

    try:
        stats = await embed_missing()
        stats_dict = stats.as_dict()
        logger.info("Incremental embedding after discover: %s", stats_dict)
        return stats_dict
    except LockBusyError:
        logger.info(
            "Incremental embedding skipped: reindex lock held by another task"
        )
        return {"skipped": "reindex lock held by another task"}
    except Exception:
        logger.exception("Incremental embedding after discover failed")
        return None


async def _collect_skill_stats_safe() -> dict[str, Any] | None:
    """采集 skill 级统计；查询失败返回 None，不影响主流程。"""
    try:
        from src.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            return await collect_skill_stats(session)
    except Exception:
        logger.exception("Failed to collect skill stats after discover")
        return None


async def _run_discover(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> int:
    """执行一轮 discover：扫描 → 补建 embedding → 采集统计 → 落结果 JSON。

    结果文件结构与自动调度完全一致（build_discover_result_document 共用）。
    """
    if args.url:
        exit_code, run_data = await _run_discover_single_skill_yaml(manager, args)
    else:
        exit_code, run_data = await _run_discover_from_config(manager, args)
    embed_stats_dict = await _backfill_embeddings_after_discover()
    skill_stats = await _collect_skill_stats_safe()
    save_discover_result_file(
        build_discover_result_document(
            started_at=run_data["started_at"],
            run_started=run_data["run_started"],
            total_repos=run_data["total_repos"],
            config_keys=run_data["config_keys"],
            counters=run_data["counters"],
            repo_details=run_data["repo_details"],
            embed_stats_dict=embed_stats_dict,
            skill_stats=skill_stats,
        )
    )
    return exit_code


async def _run_discover_single_skill_yaml(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> tuple[int, dict[str, Any]]:
    """--url 单文件模式：只扫描指定 skill.yaml 登记的 skill_repos / skills[]。"""
    requests = _build_requests_from_skill_yaml(args.url)
    return await _discover_repositories_from_requests(
        manager,
        requests,
        source_label=f" from {args.url}",
        config_keys=[args.url],
    )


async def _run_discover_from_config(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> tuple[int, dict[str, Any]]:
    # 统一解析 catalog 路径（未指定 --repository-path 时自动同步一次），
    # 供请求构建与路径打印共用，避免重复 sync
    repository_path = (
        Path(args.repository_path).expanduser()
        if args.repository_path
        else sync_openEuler_skills_repo()
    )
    requests, config_keys = build_configured_discover_requests(
        platform=args.platform,
        repository_path=repository_path,
    )
    return await _discover_repositories_from_requests(
        manager,
        requests,
        source_label=f" from {', '.join(config_keys)} (catalog: {repository_path})",
        config_keys=config_keys,
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


POPULARITY_RESULT_COLUMNS = [
    ("#", "#", 5),
    ("source", "source", 10),
    ("type", "type", 12),
    ("stars", "stars", 10),
    ("forks", "forks", 10),
    ("watchers", "watchers", 12),
    ("est_downloads", "est.downloads", 14),
    ("url", "url", 64),
]


async def _run_popularity(
    manager: "SkillManager",
    args: argparse.Namespace,
) -> int:
    """Collect popularity (stars/forks/watchers) for configured repos.

    Fetches metrics from the hosting platform API, stores them on the
    matching ``skill_repos`` row (matched by URL), then distributes each
    repository's estimated total downloads across its skills. Repos are
    weighted by type (enterprise / community / personal) and individual
    skills by category popularity and risk score, so every skill ends up
    with a different download count. The frontend ranks popularity by the
    existing ``download_count`` field, so no frontend changes are needed.
    """
    collector = PopularityCollector()
    results = await collector.collect(None, only=args.source)

    if not results:
        logger.info("No repos to collect popularity for")
        return 0

    saved = 0
    not_found = 0
    skills_updated = 0
    rows: list[dict[str, str]] = []
    for index, popularity in enumerate(results, start=1):
        repo_downloads = estimate_repo_downloads(
            popularity.stars, popularity.forks, popularity.watchers, popularity.repo_type
        )
        rows.append(
            {
                "#": str(index),
                "source": popularity.source,
                "type": popularity.repo_type,
                "stars": str(popularity.stars),
                "forks": str(popularity.forks),
                "watchers": str(popularity.watchers),
                "est_downloads": str(repo_downloads),
                "url": popularity.url,
            }
        )
        repository = await manager.skill_repo_repository.get_skill_repository_by_url(
            popularity.url
        )
        if repository is None:
            not_found += 1
            logger.info(
                "No skill_repos row for %s (URL not registered); skip persist",
                popularity.url,
            )
            continue
        await manager.skill_repo_repository.update_skill_repository(
            repository.id,
            stars_count=popularity.stars,
            forks_count=popularity.forks,
            watchers_count=popularity.watchers,
            popularity_updated_at=datetime.now(timezone.utc),
        )
        skills = await manager.skill_repository.list_by_skill_repo_id(repository.id)
        allocations = allocate_skill_downloads(repo_downloads, skills)
        for skill_id, download_count in allocations.items():
            await manager.skill_repository.update_download_count_by_skill_id(
                skill_id, download_count
            )
        skills_updated += len(allocations)
        saved += 1

    print()
    _print_table(
        rows,
        POPULARITY_RESULT_COLUMNS,
        empty_message="No popularity results.",
    )
    print()
    logger.info(
        "Popularity summary: total=%d saved=%d not_registered=%d skills_updated=%d",
        len(results), saved, not_found, skills_updated,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage skill repository discovery.",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    _add_query_parser(subparsers)
    _add_discover_parser(subparsers)
    _add_delete_parser(subparsers)
    _add_popularity_parser(subparsers)
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
        help="Register, clone, and scan skills from config or a single skill.yaml",
    )
    parser.add_argument(
        "-u",
        "--url",
        help=(
            "Single skill.yaml to discover: a local file path, or a path "
            "relative to the openEuler-skills catalog (e.g. "
            "personal/<owner>/skill.yaml); scans only its skill_repos / "
            "skills[] entries"
        ),
    )
    parser.add_argument(
        "-r",
        "--repository-path",
        default=None,
        help="Local openEuler-skills checkout (default: auto-download)",
    )
    parser.add_argument(
        "-p",
        "--platform",
        choices=PLATFORM_CHOICES,
        default=None,
        help="Config repo list to read (default: all repo lists)",
    )


def _add_delete_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser("delete", help="Delete a skill repo")
    parser.add_argument("-i", "--id", required=True, help="Skill repo ID to delete")


def _add_popularity_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "popularity",
        help="Collect popularity (stars/forks/watchers) for configured repos",
        description=(
            "Query GitHub/GitCode public APIs for repository popularity metrics "
            "and persist them on the matching skill_repos rows."
        ),
    )
    parser.add_argument(
        "-s",
        "--source",
        choices=("github", "gitcode"),
        default=None,
        help="Only collect from this platform (default: all)",
    )


async def _main() -> int:
    args = _build_parser().parse_args()

    # Resolve the catalog once for discover so the classifier and request
    # builder share the same checkout and do not issue duplicate pulls.
    if args.action == "discover" and not getattr(args, "repository_path", None):
        args.repository_path = str(sync_openEuler_skills_repo())

    async with get_db_context() as session:
        skill_repository = SkillRepository(session)
        skill_repo_repository = SkillRepoRepository(session)
        manager = SkillManager(
            skill_repository=skill_repository,
            skill_repo_repository=skill_repo_repository,
            contributor_repository=ContributorRepository(session),
            catalog_path=(Path(args.repository_path).expanduser() if getattr(args, "repository_path", None) else None),
        )

        if args.action == "query":
            return await _run_query(manager, args)
        if args.action == "discover":
            return await _run_discover(manager, args)
        if args.action == "delete":
            return await _run_delete(manager, args)
        if args.action == "popularity":
            return await _run_popularity(manager, args)
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
