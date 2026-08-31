"""DiscoverScheduler 单元测试：时间计算、配置接入与调度循环。"""

import logging
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.api.services.discover_scheduler import (
    DiscoverScheduler,
    compute_next_run,
)
from src.core.config import DiscoverSchedulerConfig


class TestComputeNextRun:
    def test_daily_before_trigger_time_today(self):
        now = datetime(2026, 8, 28, 1, 30)  # 周五
        nxt = compute_next_run(now, "daily", 3, 0, "sun")
        assert nxt == datetime(2026, 8, 28, 3, 0)

    def test_daily_after_trigger_time_rolls_to_tomorrow(self):
        now = datetime(2026, 8, 28, 4, 0)
        nxt = compute_next_run(now, "daily", 3, 0, "sun")
        assert nxt == datetime(2026, 8, 29, 3, 0)

    def test_daily_at_exact_trigger_time_rolls_to_tomorrow(self):
        now = datetime(2026, 8, 28, 3, 0, 0, 1)
        nxt = compute_next_run(now, "daily", 3, 0, "sun")
        assert nxt == datetime(2026, 8, 29, 3, 0)

    def test_weekly_same_day_before_time(self):
        now = datetime(2026, 8, 28, 1, 0)  # 周五
        nxt = compute_next_run(now, "weekly", 3, 0, "fri")
        assert nxt == datetime(2026, 8, 28, 3, 0)

    def test_weekly_same_day_after_time_rolls_to_next_week(self):
        now = datetime(2026, 8, 28, 4, 0)  # 周五
        nxt = compute_next_run(now, "weekly", 3, 0, "fri")
        assert nxt == datetime(2026, 9, 4, 3, 0)  # 下周五

    def test_weekly_later_weekday_in_same_week(self):
        now = datetime(2026, 8, 28, 4, 0)  # 周五
        nxt = compute_next_run(now, "weekly", 3, 0, "sat")
        assert nxt == datetime(2026, 8, 29, 3, 0)  # 周六

    def test_weekly_earlier_weekday_in_next_week(self):
        now = datetime(2026, 8, 28, 4, 0)  # 周五
        nxt = compute_next_run(now, "weekly", 3, 0, "mon")
        assert nxt == datetime(2026, 8, 31, 3, 0)  # 下周一


class TestConfigIntegration:
    def test_settings_has_discover_scheduler_defaults(self):
        from src.core.config import Settings

        settings = Settings()
        assert settings.discover_scheduler.enabled is False
        assert settings.discover_scheduler.interval == "daily"
        assert settings.discover_scheduler.time == "03:00"
        assert settings.discover_scheduler.weekday == "sun"

    def test_config_yaml_section_parsed(self):
        # config.yaml 中 discover_scheduler.enabled=false，get_settings 有缓存，
        # 直接验证 from_yaml 的解析路径
        from src.core.config import Settings

        settings = Settings.from_yaml("config.yaml")
        assert settings.discover_scheduler.enabled is False
        assert settings.discover_scheduler.interval == "daily"
        assert settings.discover_scheduler.time == "03:00"
        assert settings.discover_scheduler.weekday == "sun"

    def test_invalid_interval_rejected_on_start(self):
        config = DiscoverSchedulerConfig(enabled=True, interval="hourly")
        scheduler = DiscoverScheduler(config)
        with pytest.raises(ValueError, match="daily or weekly"):
            import asyncio

            asyncio.run(scheduler.start())

    def test_invalid_weekday_rejected_on_start(self):
        config = DiscoverSchedulerConfig(enabled=True, interval="weekly", weekday="funday")
        scheduler = DiscoverScheduler(config)
        with pytest.raises(ValueError, match="weekday"):
            import asyncio

            asyncio.run(scheduler.start())


def _fake_result(**flags):
    return SimpleNamespace(skill_num=2, url="https://gitcode.com/a/b", **flags)


class TestRunDiscoverOnce:
    @pytest.fixture
    def requests(self):
        return (
            [
                SimpleNamespace(url="https://gitcode.com/a/b"),
                SimpleNamespace(url="https://gitcode.com/c/d"),
                SimpleNamespace(url="https://gitcode.com/e/f"),
            ],
            ["openeuler_repos"],
        )

    async def test_classifies_each_repo_and_logs_summary(self, requests, caplog, tmp_path):
        scheduler = DiscoverScheduler(
            DiscoverSchedulerConfig(enabled=True, result_dir=str(tmp_path))
        )
        caplog.set_level(logging.INFO, logger="src.api.services.discover_scheduler")

        results = [
            _fake_result(_created_new=True),
            _fake_result(_unchanged=True),
            _fake_result(_removed_existing=True),
        ]

        with (
            patch(
                "src.api.services.discover_scheduler.build_configured_discover_requests",
                return_value=requests,
            ),
            patch(
                "src.api.services.discover_scheduler.AsyncSessionLocal"
            ) as session_factory,
        ):
            session_ctx = AsyncMock()
            session_factory.return_value = session_ctx
            manager = SimpleNamespace(
                discover_configured_skill_repository=AsyncMock(side_effect=results)
            )
            with patch(
                "src.api.services.discover_scheduler.SkillManager", return_value=manager
            ):
                counters = await scheduler.run_discover_once()

        assert counters == {
            "created": 1,
            "rediscovered": 0,
            "security_retried": 0,
            "unchanged": 1,
            "removed": 1,
            "no_skill": 0,
            "failed": 0,
        }

        # 每轮开始/结束日志与每仓耗时日志均已输出
        assert "round started" in caplog.text
        assert "round finished" in caplog.text
        assert "total" in caplog.text
        assert "avg" in caplog.text
        assert "slowest" in caplog.text
        assert caplog.text.count("took") == 3

    async def test_result_file_saved_with_details(self, requests, tmp_path):
        """每轮结果写入 JSON 文件，包含汇总统计与每仓明细。"""
        import json as json_lib

        scheduler = DiscoverScheduler(
            DiscoverSchedulerConfig(enabled=True, result_dir=str(tmp_path))
        )
        results = [
            _fake_result(_created_new=True),
            _fake_result(_unchanged=True),
            _fake_result(_removed_existing=True),
        ]

        with (
            patch(
                "src.api.services.discover_scheduler.build_configured_discover_requests",
                return_value=requests,
            ),
            patch(
                "src.api.services.discover_scheduler.AsyncSessionLocal"
            ) as session_factory,
        ):
            session_factory.return_value = AsyncMock()
            manager = SimpleNamespace(
                discover_configured_skill_repository=AsyncMock(side_effect=results)
            )
            with patch(
                "src.api.services.discover_scheduler.SkillManager", return_value=manager
            ):
                await scheduler.run_discover_once()

        files = list(tmp_path.glob("discover-*.json"))
        assert len(files) == 1
        document = json_lib.loads(files[0].read_text(encoding="utf-8"))

        assert document["total_repos"] == 3
        assert document["counters"] == {
            "created": 1,
            "rediscovered": 0,
            "security_retried": 0,
            "unchanged": 1,
            "removed": 1,
            "no_skill": 0,
            "failed": 0,
        }
        assert document["config_keys"] == ["openeuler_repos"]
        assert "started_at" in document
        assert "finished_at" in document
        assert "total_seconds" in document
        assert "avg_seconds_per_repo" in document
        assert len(document["slowest_repos"]) == 3

        by_url = {repo["url"]: repo for repo in document["repos"]}
        assert len(by_url) == 3
        created = by_url["https://gitcode.com/a/b"]
        assert created["outcome"] == "created"
        assert created["skill_num"] == 2
        assert "duration_seconds" in created
        assert "error" not in created

    async def test_failed_repo_error_message_saved(self, requests, tmp_path):
        """失败仓库的异常信息写入结果文件。"""
        import json as json_lib

        scheduler = DiscoverScheduler(
            DiscoverSchedulerConfig(enabled=True, result_dir=str(tmp_path))
        )
        with (
            patch(
                "src.api.services.discover_scheduler.build_configured_discover_requests",
                return_value=requests,
            ),
            patch(
                "src.api.services.discover_scheduler.AsyncSessionLocal"
            ) as session_factory,
        ):
            session_factory.return_value = AsyncMock()
            manager = SimpleNamespace(
                discover_configured_skill_repository=AsyncMock(
                    side_effect=[RuntimeError("clone timeout"), None, None]
                )
            )
            with patch(
                "src.api.services.discover_scheduler.SkillManager", return_value=manager
            ):
                await scheduler.run_discover_once()

        document = json_lib.loads(
            next(tmp_path.glob("discover-*.json")).read_text(encoding="utf-8")
        )
        failed = next(repo for repo in document["repos"] if repo["outcome"] == "failed")
        assert failed["error"] == "clone timeout"

    async def test_result_save_failure_does_not_break_run(self, requests, caplog):
        """结果文件写失败（目录不可写）不影响本轮执行与返回值。"""
        scheduler = DiscoverScheduler(
            DiscoverSchedulerConfig(enabled=True, result_dir="/proc/forbidden-dir")
        )
        caplog.set_level(logging.WARNING, logger="src.api.services.discover_scheduler")

        with (
            patch(
                "src.api.services.discover_scheduler.build_configured_discover_requests",
                return_value=requests,
            ),
            patch(
                "src.api.services.discover_scheduler.AsyncSessionLocal"
            ) as session_factory,
        ):
            session_factory.return_value = AsyncMock()
            manager = SimpleNamespace(
                discover_configured_skill_repository=AsyncMock(
                    side_effect=[
                        _fake_result(_created_new=True),
                        _fake_result(_unchanged=True),
                        _fake_result(_removed_existing=True),
                    ]
                )
            )
            with patch(
                "src.api.services.discover_scheduler.SkillManager", return_value=manager
            ):
                counters = await scheduler.run_discover_once()

        assert counters["created"] == 1
        assert "Failed to save discover result file" in caplog.text

    async def test_single_repo_failure_does_not_abort_run(self, requests, caplog, tmp_path):
        scheduler = DiscoverScheduler(
            DiscoverSchedulerConfig(enabled=True, result_dir=str(tmp_path))
        )
        caplog.set_level(logging.INFO, logger="src.api.services.discover_scheduler")

        with (
            patch(
                "src.api.services.discover_scheduler.build_configured_discover_requests",
                return_value=requests,
            ),
            patch(
                "src.api.services.discover_scheduler.AsyncSessionLocal"
            ) as session_factory,
        ):
            session_factory.return_value = AsyncMock()
            manager = SimpleNamespace(
                discover_configured_skill_repository=AsyncMock(
                    side_effect=[_fake_result(_created_new=True), RuntimeError("boom"), None]
                )
            )
            with patch(
                "src.api.services.discover_scheduler.SkillManager", return_value=manager
            ):
                counters = await scheduler.run_discover_once()

        assert counters["created"] == 1
        assert counters["failed"] == 1
        assert counters["no_skill"] == 1

        # 失败仓库的日志带耗时（after Xs）
        assert "Discover failed for" in caplog.text
        assert "after" in caplog.text


class TestSchedulerLoop:
    async def test_loop_triggers_run_at_scheduled_time(self):
        """循环睡眠到调度点后触发 run_discover_once，run 返回后继续等待。"""
        config = DiscoverSchedulerConfig(enabled=True, interval="daily", time="03:00")
        scheduler = DiscoverScheduler(config)

        calls = []

        async def fake_sleep(seconds: float):
            # 记录计算出的等待间隔后立即“到点”
            calls.append(seconds)

        async def fake_run(sched):
            calls.append("run")
            sched._running = False  # 首轮执行后停止循环

        fixed_now = datetime(2026, 8, 28, 1, 0)
        with (
            patch("src.api.services.discover_scheduler.asyncio.sleep", fake_sleep),
            patch("src.api.services.discover_scheduler.datetime") as dt_mock,
            patch.object(DiscoverScheduler, "run_discover_once", fake_run),
        ):
            dt_mock.now.return_value = fixed_now
            dt_mock.side_effect = lambda *a, **k: datetime(*a, **k)
            scheduler._running = True  # 直接驱动 _loop（不经 start() 创建 task）
            await scheduler._loop()

        # 1:00 -> 3:00 间隔 2 小时；run 恰好执行一次
        assert calls[0] == timedelta(hours=2).total_seconds()
        assert calls[1] == "run"

    async def test_start_stop_lifecycle(self):
        config = DiscoverSchedulerConfig(enabled=True)
        scheduler = DiscoverScheduler(config)
        await scheduler.start()
        assert scheduler._running is True
        assert scheduler._task is not None
        await scheduler.stop()
        assert scheduler._running is False
        assert scheduler._task is None

    async def test_start_is_idempotent(self):
        config = DiscoverSchedulerConfig(enabled=True)
        scheduler = DiscoverScheduler(config)
        await scheduler.start()
        task = scheduler._task
        await scheduler.start()
        assert scheduler._task is task
        await scheduler.stop()


class TestStartDiscoverScheduler:
    async def test_returns_none_when_disabled(self):
        from src.api.services.discover_scheduler import start_discover_scheduler

        settings = SimpleNamespace(
            discover_scheduler=DiscoverSchedulerConfig(enabled=False)
        )
        with patch("src.core.config.get_settings", return_value=settings):
            result = await start_discover_scheduler()
        assert result is None

    async def test_starts_and_returns_scheduler_when_enabled(self):
        from src.api.services.discover_scheduler import start_discover_scheduler

        settings = SimpleNamespace(
            discover_scheduler=DiscoverSchedulerConfig(enabled=True)
        )
        with patch("src.core.config.get_settings", return_value=settings):
            scheduler = await start_discover_scheduler()
        assert scheduler is not None
        await scheduler.stop()
