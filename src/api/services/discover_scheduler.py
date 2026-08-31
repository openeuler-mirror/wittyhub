"""后台定时 discover 调度器。

按 DiscoverSchedulerConfig（config.yaml 的 discover_scheduler 段）在每天
或每周的固定时刻触发 skillcrawler 的 discover 流程：读取
skills/skill-repos.yaml 中全部仓库配置，逐仓库执行
SkillManager.discover_configured_skill_repository。

调度基于纯 asyncio（sleep 到下一个触发点），与 SkillspectorCollector
的后台任务模式一致，不引入额外依赖。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from skillcrawler.core.skill_manager import SkillManager
from skillcrawler.main import build_configured_discover_requests
from src.core.config import DiscoverSchedulerConfig
from src.core.database import AsyncSessionLocal
from src.models.repository import SkillRepoRepository, SkillRepository

logger = logging.getLogger(__name__)

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time (expected HH:MM): {value!r}")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time (expected HH:MM): {value!r}")
    return hour, minute


def compute_next_run(
    now: datetime,
    interval: str,
    hour: int,
    minute: int,
    weekday: str,
) -> datetime:
    """计算下一次触发时刻（本地时区）。

    daily：今天已过触发点则取明天同一时刻；
    weekly：取下一个指定 weekday 的触发时刻（今天已过则顺延一周）。
    """
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if interval == "weekly":
        target = WEEKDAYS.index(weekday)
        days_ahead = (target - now.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


class DiscoverScheduler:
    """定时触发 discover 流程的后台任务。

    循环结构天然防重入：每轮 run_discover_once 执行完毕后才计算下一个
    触发点，克隆扫描耗时较长时下一轮自动顺延，不会叠加执行。
    """

    def __init__(self, config: DiscoverSchedulerConfig):
        self._config = config
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def _check_interval_args(self) -> str:
        """校验 interval / weekday 配置，返回规范化后的 interval。"""
        interval = self._config.interval.strip().lower()
        if interval not in ("daily", "weekly"):
            raise ValueError(f"discover_scheduler.interval must be daily or weekly, got {interval!r}")
        if interval == "weekly" and self._config.weekday.strip().lower() not in WEEKDAYS:
            raise ValueError(f"discover_scheduler.weekday must be one of {WEEKDAYS}, got {self._config.weekday!r}")
        return interval

    async def start(self) -> None:
        if self._running:
            return
        interval = self._check_interval_args()
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "DiscoverScheduler started (interval=%s, time=%s, weekday=%s)",
            interval,
            self._config.time,
            self._config.weekday,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("DiscoverScheduler stopped")

    async def _loop(self) -> None:
        interval = self._config.interval.strip().lower()
        hour, minute = _parse_hhmm(self._config.time)
        weekday = self._config.weekday.strip().lower()

        while self._running:
            next_run = compute_next_run(datetime.now(), interval, hour, minute, weekday)
            wait_seconds = (next_run - datetime.now()).total_seconds()
            logger.info("Next scheduled discover run at %s (in %.0fs)", next_run, wait_seconds)
            try:
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                return
            if not self._running:
                return
            try:
                await self.run_discover_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # 单轮整体异常不应终止调度循环，记录后等待下一个调度点
                logger.exception("Scheduled discover run failed")

    async def run_discover_once(self) -> dict[str, int]:
        """执行一轮 discover（全部配置仓库），返回分类统计。

        每轮记录开始/结束日志与总耗时；每个仓库记录处理耗时，
        结束时汇总平均耗时与最慢的仓库，便于排查慢仓库。
        每轮结果（含每仓明细）写入 result_dir 下的 JSON 文件。
        """
        requests, config_keys = build_configured_discover_requests()
        total = len(requests)
        run_started = time.monotonic()
        run_started_wall = datetime.now()
        logger.info(
            "Scheduled discover round started: %d repos from %s",
            total,
            ", ".join(config_keys),
        )

        counters = {
            "created": 0,
            "rediscovered": 0,
            "security_retried": 0,
            "unchanged": 0,
            "removed": 0,
            "no_skill": 0,
            "failed": 0,
        }
        repo_durations: list[tuple[str, float]] = []
        repo_details: list[dict[str, Any]] = []

        async with AsyncSessionLocal() as session:
            manager = SkillManager(
                skill_repository=SkillRepository(session),
                skill_repo_repository=SkillRepoRepository(session),
            )
            for index, request in enumerate(requests, start=1):
                label = request.url or "<missing-url>"
                logger.info("[%d/%d] scanning %s", index, total, label)
                repo_started = time.monotonic()
                try:
                    result = await manager.discover_configured_skill_repository(request)
                except Exception as exc:
                    elapsed = time.monotonic() - repo_started
                    repo_durations.append((label, elapsed))
                    counters["failed"] += 1
                    repo_details.append(
                        {
                            "url": label,
                            "outcome": "failed",
                            "skill_num": 0,
                            "duration_seconds": round(elapsed, 3),
                            "error": str(exc),
                        }
                    )
                    logger.exception(
                        "Discover failed for %s after %.1fs", label, elapsed
                    )
                    continue

                elapsed = time.monotonic() - repo_started
                repo_durations.append((label, elapsed))
                outcome = self._classify_result(result)
                counters[outcome] += 1
                repo_details.append(
                    {
                        "url": label,
                        "outcome": outcome,
                        "skill_num": getattr(result, "skill_num", 0),
                        "duration_seconds": round(elapsed, 3),
                    }
                )
                logger.info(
                    "[%d/%d] %s: %s (%d skills, took %.1fs)",
                    index,
                    total,
                    outcome,
                    label,
                    getattr(result, "skill_num", 0),
                    elapsed,
                )

        run_elapsed = time.monotonic() - run_started
        avg_elapsed = run_elapsed / total if total else 0.0
        slowest = sorted(repo_durations, key=lambda item: item[1], reverse=True)[:3]
        slowest_text = (
            ", ".join(f"{label}={duration:.1f}s" for label, duration in slowest) or "n/a"
        )
        logger.info(
            "Scheduled discover round finished: %d repos, %s, total %.1fs, "
            "avg %.1fs/repo, slowest: %s",
            total,
            counters,
            run_elapsed,
            avg_elapsed,
            slowest_text,
        )

        self._save_result_file(
            {
                "started_at": run_started_wall.isoformat(timespec="seconds"),
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "total_repos": total,
                "config_keys": config_keys,
                "counters": counters,
                "total_seconds": round(run_elapsed, 3),
                "avg_seconds_per_repo": round(avg_elapsed, 3),
                "slowest_repos": [
                    {"url": label, "seconds": round(duration, 3)}
                    for label, duration in slowest
                ],
                "repos": repo_details,
            }
        )
        return counters

    def _resolve_result_dir(self) -> Path:
        """结果保存目录：优先 result_dir 配置，否则 storage.local_path/logs。"""
        configured = self._config.result_dir.strip()
        if configured:
            return Path(configured).expanduser()
        from src.core.config import get_settings

        return Path(get_settings().storage.local_path) / "logs"

    def _save_result_file(self, document: dict[str, Any]) -> Path | None:
        """把一轮结果写入 JSON 文件；失败仅记录 warning，不影响主流程。"""
        try:
            result_dir = self._resolve_result_dir()
            result_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = result_dir / f"discover-{timestamp}.json"
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info("Discover result saved to %s", path)
            return path
        except Exception:
            logger.warning("Failed to save discover result file", exc_info=True)
            return None

    @staticmethod
    def _classify_result(result: Any) -> str:
        """与 CLI discover 相同的口径对结果分类（基于 manager 标记的私有标志）。"""
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


async def start_discover_scheduler() -> DiscoverScheduler | None:
    """按配置创建并启动 discover 调度器；未启用时返回 None。"""
    from src.core.config import get_settings

    settings = get_settings()
    if not settings.discover_scheduler.enabled:
        logger.info("DiscoverScheduler disabled (discover_scheduler.enabled=false)")
        return None

    scheduler = DiscoverScheduler(settings.discover_scheduler)
    await scheduler.start()
    return scheduler
