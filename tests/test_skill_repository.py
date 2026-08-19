import asyncio
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class TestSkillRepositoryUnit:
    def test_models_package_exports_skill_repo_types(self):
        from src.models import SkillRepoModel, SkillRepoRepository

        assert SkillRepoModel is not None
        assert SkillRepoRepository is not None

    @pytest.mark.asyncio
    async def test_increment_download_does_not_update_skill_updated_at(self):
        from sqlalchemy.dialects import postgresql

        from src.models.repository import SkillRepository

        skill = SimpleNamespace(id=uuid.uuid4())
        session = AsyncMock()
        repo = SkillRepository(session)
        repo.get_by_skill_id = AsyncMock(return_value=skill)

        assert await repo.increment_download("github/acme/example") is True

        statement = session.execute.await_args.args[0]
        sql = str(statement.compile(dialect=postgresql.dialect()))
        assert "download_count=(skills.download_count +" in sql
        assert "updated_at=" not in sql

    @pytest.mark.asyncio
    async def test_update_only_changes_updated_at_when_explicitly_requested(self):
        from sqlalchemy.dialects import postgresql

        from src.models.repository import SkillRepository

        skill = SimpleNamespace(id=uuid.uuid4())
        session = AsyncMock()
        repo = SkillRepository(session)
        repo.get_by_skill_id = AsyncMock(side_effect=[skill, skill, skill, skill])

        await repo.update("github/acme/example", {"risk_score": 10})
        implicit_statement = session.execute.await_args_list[0].args[0]
        implicit_sql = str(implicit_statement.compile(dialect=postgresql.dialect()))
        assert "risk_score=" in implicit_sql
        assert "updated_at=" not in implicit_sql

        requested_time = datetime.now(timezone.utc)
        await repo.update(
            "github/acme/example",
            {"risk_score": 20, "updated_at": requested_time},
        )
        explicit_statement = session.execute.await_args_list[1].args[0]
        explicit_sql = str(explicit_statement.compile(dialect=postgresql.dialect()))
        assert "updated_at=" in explicit_sql

    def test_list_with_skill_id_prefix_filters_by_repo(self):
        from sqlalchemy import select
        from sqlalchemy.dialects import postgresql

        from src.models.orm import Skill
        from src.models.repository import SkillRepository

        session = AsyncMock()
        repo = SkillRepository(session)
        query = repo._apply_skill_filters(
            select(Skill),
            Skill,
            source="github",
            skill_id_prefix="github/anthropics/claude-code",
        )
        compiled = query.compile(dialect=postgresql.dialect())
        sql = str(compiled)
        # source_type 过滤 + repo 前缀过滤应同时生效
        assert "skills.source = " in sql
        assert "skills.skill_id LIKE " in sql
        assert "github/anthropics/claude-code/%" in compiled.params.values()

    @pytest.mark.asyncio
    async def test_list_skills_route_forwards_repo_filter(self):
        from src.api.routes.skills import list_skills
        from src.api.schemas.skill import SkillListResponse

        now = datetime.now(timezone.utc)
        skill = SimpleNamespace(
            id=str(uuid.uuid4()),
            skill_id="github/anthropics/claude-code/.ai/skills/add-or-fix-type-checking",
            name="add-or-fix-type-checking",
            description="Check types",
            version="1.0.0",
            commit_id="abc123",
            author="anthropics",
            source="github",
            source_url="https://github.com/anthropics/claude-code",
            repo_url=None,
            category="Development",
            tags=["types"],
            platform="personal",
            extra_metadata={},
            content=None,
            risk_score=10,
            download_count=3,
            _period_downloads=None,
            rating=None,
            created_at=now,
            updated_at=now,
            last_indexed_at=None,
        )
        skill_repository = MagicMock()
        skill_repository.list = AsyncMock(return_value=([skill], 1))
        db = AsyncMock()

        with patch("src.api.routes.skills.SkillRepository", return_value=skill_repository):
            response = await list_skills(
                skip=0,
                limit=20,
                category=None,
                platform=None,
                tags=None,
                security_level=None,
                source_type="github",
                repo="anthropics/claude-code",
                sort_by="updated_at",
                sort_period=None,
                db=db,
            )

        assert isinstance(response, SkillListResponse)
        kwargs = skill_repository.list.await_args.kwargs
        assert kwargs["source"] == "github"
        assert kwargs["skill_id_prefix"] == "github/anthropics/claude-code"
        assert kwargs["limit"] == 20

    def test_build_public_skill_id_uses_relative_skill_path(self):
        from skillcrawler.core.skill_parser import build_public_skill_id

        repo = SimpleNamespace(
            source="github",
            url="https://github.com/wix/react-native-navigation.git",
        )
        skill_id = build_public_skill_id(
            repo,
            Path("/tmp/repo"),
            Path("/tmp/repo/.github/skills/rnn-codebase/SKILL.md"),
        )

        assert skill_id == "github/wix/react-native-navigation/.github/skills/rnn-codebase"

    def test_build_public_skill_id_uses_repo_slug_for_root_skill(self):
        from skillcrawler.core.skill_parser import build_public_skill_id

        repo = SimpleNamespace(
            source="github",
            url="https://github.com/acme/agent-skills.git",
        )

        skill_id = build_public_skill_id(
            repo,
            Path("/tmp/github.com_acme_agent-skills"),
            Path("/tmp/github.com_acme_agent-skills/SKILL.md"),
        )

        assert skill_id == "github/acme/agent-skills/agent-skills"

    def test_has_skill_md_ignores_excluded_directories(self, tmp_path):
        from skillcrawler.core.skill_manager import SkillManager

        for directory in ("docs", "examples", "tests", "templates"):
            skill_file = tmp_path / directory / "example" / "SKILL.md"
            skill_file.parent.mkdir(parents=True)
            skill_file.write_text("# Example", encoding="utf-8")

        assert SkillManager._has_skill_md(tmp_path) is False

    def test_has_skill_md_accepts_scannable_skill(self, tmp_path):
        from skillcrawler.core.skill_manager import SkillManager

        excluded_skill = tmp_path / "docs" / "SKILL.md"
        excluded_skill.parent.mkdir()
        excluded_skill.write_text("# Documentation", encoding="utf-8")
        valid_skill = tmp_path / "skills" / "release-helper" / "SKILL.md"
        valid_skill.parent.mkdir(parents=True)
        valid_skill.write_text("# Release Helper", encoding="utf-8")

        assert SkillManager._has_skill_md(tmp_path) is True

    def test_skill_manager_workspace_defaults_to_storage_local_path(self, tmp_path):
        from skillcrawler.core import skill_manager

        storage_path = str(tmp_path)
        with patch.object(skill_manager.settings.storage, "local_path", storage_path):
            manager = skill_manager.SkillManager(MagicMock(), MagicMock())

        assert manager.workspace_base == tmp_path.resolve()

    def test_skillcrawler_platform_maps_to_config_key(self):
        from skillcrawler.main import _config_key_for_platform, _config_keys_for_platform

        assert _config_key_for_platform("enterprise") == "enterprise_repos"
        assert _config_key_for_platform("openeuler") == "openeuler_repos"
        assert _config_key_for_platform("personal") == "personal_repos"
        assert _config_key_for_platform("enterprise_repos") == "enterprise_repos"
        assert _config_keys_for_platform(None) == [
            "openeuler_repos",
            "personal_repos",
            "enterprise_repos",
        ]
        assert _config_keys_for_platform("personal") == ["personal_repos"]

    def test_single_url_discover_infers_openeuler_platform(self):
        from skillcrawler.main import _build_single_url_discover_request

        request = _build_single_url_discover_request(
            SimpleNamespace(
                url="https://gitcode.com/openeuler/mcp-servers",
                branch=None,
                platform=None,
            )
        )

        assert request.platform == "openeuler"

    def test_single_url_discover_explicit_platform_wins(self):
        from skillcrawler.main import _build_single_url_discover_request

        request = _build_single_url_discover_request(
            SimpleNamespace(
                url="https://gitcode.com/openeuler/mcp-servers",
                branch=None,
                platform="personal",
            )
        )

        assert request.platform == "personal"

    def test_settings_env_overrides_yaml(self, tmp_path, monkeypatch):
        from src.core.config import Settings

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
postgres:
  host: localhost
ai:
  embedding_host: http://localhost:8081
security:
  enable_audit: true
model:
  api_key: local-key
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("POSTGRES__HOST", "db")
        monkeypatch.setenv("AI__EMBEDDING_HOST", "http://embedding:8081")
        monkeypatch.setenv("SECURITY__ENABLE_AUDIT", "false")
        monkeypatch.setenv("MODEL__API_KEY", "")

        settings = Settings.from_yaml(config_path)

        assert settings.postgres.host == "db"
        assert settings.ai.embedding_host == "http://embedding:8081"
        assert settings.security.enable_audit is False
        assert settings.model.api_key == ""

    def test_openeuler_sig_mapping_uses_only_openeuler_repos(self, tmp_path):
        from skillcrawler.core.openeuler_sig import _load_sig_mapping

        sig_dir = tmp_path / "sig" / "sig-ops"
        sig_dir.mkdir(parents=True)
        (sig_dir / "sig-info.yaml").write_text(
            """
name: sig-ops
repositories:
- repo:
  - openeuler/PilotGo-plugin-llmops
  - src-openeuler/ignored-package
  - openeuler/intel-openvino
""",
            encoding="utf-8",
        )

        mapping = _load_sig_mapping(tmp_path)

        assert mapping["gitcode.com_openeuler_PilotGo-plugin-llmops"] == "sig-ops"
        assert mapping["gitcode.com_openeuler_intel-openvino"] == "sig-ops"
        assert "gitcode.com_src-openeuler_ignored-package" not in mapping

    def test_build_requests_from_config_keeps_openeuler_sig_lazy(self, tmp_path):
        from skillcrawler.main import _build_requests_from_config

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            """
openeuler_repos:
  - url: https://gitcode.com/openeuler/PilotGo-plugin-llmops
""",
            encoding="utf-8",
        )

        requests = _build_requests_from_config(
            config_path,
            "openeuler_repos",
            "openeuler",
        )

        assert requests[0].platform == "openeuler"
        assert not hasattr(requests[0], "sig_name")

    def test_skill_manager_resolves_openeuler_sig_lazily(self):
        from skillcrawler.core.skill_manager import SkillManager

        manager = SkillManager(MagicMock(), MagicMock())
        manager._openeuler_sig_by_repo_name = {
            "gitcode.com_openeuler_PilotGo-plugin-llmops": "sig-ops"
        }

        sig_name = manager._get_openeuler_sig_name(
            "gitcode.com_openeuler_PilotGo-plugin-llmops"
        )

        assert sig_name == "sig-ops"

    def test_git_operations_reads_latest_commit_for_skill_directory(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations

        repository = tmp_path / "repository"
        repository.mkdir()
        _git(repository, "init")
        _git(repository, "config", "user.email", "tests@example.com")
        _git(repository, "config", "user.name", "WittyHub Tests")

        skill_a = repository / "skills" / "a"
        skill_b = repository / "skills" / "b"
        skill_a.mkdir(parents=True)
        skill_b.mkdir(parents=True)
        (skill_a / "SKILL.md").write_text("# Skill A\n", encoding="utf-8")
        (skill_b / "SKILL.md").write_text("# Skill B\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "add skills")
        skill_b_commit = _git(repository, "rev-parse", "HEAD")

        (skill_a / "SKILL.md").write_text("# Skill A changed\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "change skill a")
        skill_a_commit = _git(repository, "rev-parse", "HEAD")

        git_ops = GitOperations()

        assert git_ops.get_latest_commit_id_for_path(repository, "skills/a") == skill_a_commit
        assert git_ops.get_latest_commit_id_for_path(repository, "skills/b") == skill_b_commit

    def test_git_operations_batches_latest_commits_for_skill_directories(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations

        repository = tmp_path / "repository"
        repository.mkdir()
        _git(repository, "init")
        _git(repository, "config", "user.email", "tests@example.com")
        _git(repository, "config", "user.name", "WittyHub Tests")

        skill_a = repository / "skills" / "a" / "SKILL.md"
        skill_a.parent.mkdir(parents=True)
        skill_a.write_text("# A\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "add a")
        skill_a_commit = _git(repository, "rev-parse", "HEAD")

        skill_b = repository / "skills" / "b" / "SKILL.md"
        skill_b.parent.mkdir(parents=True)
        skill_b.write_text("# B\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "add b")
        skill_b_commit = _git(repository, "rev-parse", "HEAD")

        git_ops = GitOperations()
        original_run = git_ops._run_git_command
        git_ops._run_git_command = MagicMock(wraps=original_run)

        commits = git_ops.get_latest_commit_ids_for_paths(
            repository,
            ["skills/a", "skills/b"],
        )

        assert commits == {
            "skills/a": skill_a_commit,
            "skills/b": skill_b_commit,
        }
        git_ops._run_git_command.assert_called_once()

    def test_full_repository_update_uses_regular_fetch(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations

        git_ops = GitOperations()
        git_ops._run_git_command_with_retries = MagicMock()
        git_ops._run_git_command_with_auth_retry = MagicMock()
        git_ops.is_shallow_repository = MagicMock(return_value=False)

        git_ops.update_existing_repository(
            tmp_path,
            "https://github.com/acme/repository.git",
            branch="main",
        )

        fetch_command = git_ops._run_git_command_with_auth_retry.call_args.args[0]
        assert fetch_command == [
            "git", "-C", str(tmp_path), "fetch", "origin", "main",
        ]

    def test_shallow_repository_update_keeps_depth_one_fetch(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations

        git_ops = GitOperations()
        git_ops._run_git_command_with_retries = MagicMock()
        git_ops._run_git_command_with_auth_retry = MagicMock()
        git_ops.is_shallow_repository = MagicMock(return_value=True)

        git_ops.update_existing_repository(
            tmp_path,
            "https://github.com/acme/repository.git",
            branch="main",
        )

        fetch_command = git_ops._run_git_command_with_auth_retry.call_args.args[0]
        assert fetch_command == [
            "git", "-C", str(tmp_path), "fetch", "--depth", "1", "origin", "main",
        ]

    def test_unshallow_prefers_blobless_history(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations

        git_ops = GitOperations()
        git_ops.is_shallow_repository = MagicMock(return_value=True)
        git_ops._run_git_command_with_retries = MagicMock()
        git_ops._run_git_command_with_auth_retry = MagicMock()

        git_ops.ensure_full_history(
            tmp_path,
            "https://github.com/acme/repository.git",
            "https://github.com/acme/repository",
        )

        fetch_command = git_ops._run_git_command_with_auth_retry.call_args.args[0]
        assert fetch_command == [
            "git", "-C", str(tmp_path), "fetch",
            "--unshallow", "--filter=blob:none", "origin",
        ]
        configured_keys = {
            call.args[0][-2]: call.args[0][-1]
            for call in git_ops._run_git_command_with_retries.call_args_list
        }
        assert configured_keys == {
            "remote.origin.promisor": "true",
            "remote.origin.partialclonefilter": "blob:none",
        }

    def test_unshallow_falls_back_when_filter_is_unsupported(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations

        git_ops = GitOperations()
        git_ops.is_shallow_repository = MagicMock(return_value=True)
        git_ops._run_git_command_with_retries = MagicMock()
        git_ops._run_git_command_with_auth_retry = MagicMock(
            side_effect=[subprocess.CalledProcessError(1, ["git", "fetch"]), None]
        )

        git_ops.ensure_full_history(
            tmp_path,
            "https://example.com/acme/repository.git",
            "https://example.com/acme/repository",
        )

        fetch_commands = [
            call.args[0]
            for call in git_ops._run_git_command_with_auth_retry.call_args_list
        ]
        assert fetch_commands == [
            [
                "git", "-C", str(tmp_path), "fetch",
                "--unshallow", "--filter=blob:none", "origin",
            ],
            ["git", "-C", str(tmp_path), "fetch", "--unshallow", "origin"],
        ]

    def test_git_timeout_sanitization_accepts_byte_output(self):
        from skillcrawler.core.git_operations import GitOperations

        git_ops = GitOperations(github_token="secret-token")
        timeout = subprocess.TimeoutExpired(
            ["git", "clone", "https://github.com/acme/repository"],
            120,
            output=b"clone output\n",
            stderr=b"authentication secret-token failed\n",
        )

        sanitized = git_ops._sanitize_timeout_error(timeout)

        assert sanitized.output == "clone output\n"
        assert sanitized.stderr == "authentication *** failed\n"
        assert git_ops.summarize_exception(sanitized) == (
            "git clone timed out after 120s"
        )

    async def test_skill_scanner_stores_skill_directory_commit_not_repo_head(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations
        from skillcrawler.core.skill_scanner import SkillScanner

        repository = tmp_path / "repository"
        repository.mkdir()
        _git(repository, "init")
        _git(repository, "config", "user.email", "tests@example.com")
        _git(repository, "config", "user.name", "WittyHub Tests")

        skill_dir = repository / "skills" / "a"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Skill A\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "add skill a")
        skill_dir_commit = _git(repository, "rev-parse", "HEAD")

        (repository / "README.md").write_text("# Changed repo head\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "change readme")
        repo_head_commit = _git(repository, "rev-parse", "HEAD")

        skill_repository = MagicMock()
        skill_repository.load_scan_records = AsyncMock(return_value=({}, {}))
        scanner = SkillScanner(
            git_ops=GitOperations(),
            skill_repository=skill_repository,
            category_classifier=None,
        )
        repo = SimpleNamespace(
            id=uuid.uuid4(),
            source="github",
            url="https://github.com/acme/agent-skills",
            branch="master",
            platform=None,
        )

        skills, _ = await scanner.start_scan(
            repo=repo,
            repo_root=repository,
            repository_git_metadata={"commit_id": repo_head_commit},
        )

        assert skills[0].commit_id == skill_dir_commit
        assert skills[0].commit_id != repo_head_commit

    def test_skill_scanner_reuses_security_result_for_unchanged_skill_commit(self, tmp_path):
        from skillcrawler.core.git_operations import GitOperations
        from skillcrawler.core.skill_scanner import SkillScanner
        from skillcrawler.core.skill_parser import build_public_skill_id

        repository = tmp_path / "repository"
        repository.mkdir()
        _git(repository, "init")
        _git(repository, "config", "user.email", "tests@example.com")
        _git(repository, "config", "user.name", "WittyHub Tests")

        skill_dir = repository / "skills" / "production-skill"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: example\n---\n# Example\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "add skill")
        skill_commit = _git(repository, "rev-parse", "HEAD")

        (repository / "README.md").write_text("# unrelated change\n", encoding="utf-8")
        _git(repository, "add", ".")
        _git(repository, "commit", "-m", "change readme")
        repo_head = _git(repository, "rev-parse", "HEAD")

        repo = SimpleNamespace(
            id=uuid.uuid4(),
            source="github",
            url="https://github.com/acme/repository",
            branch="master",
            platform=None,
        )
        skill_id = build_public_skill_id(repo, repository, skill_file)
        existing = SimpleNamespace(
            commit_id=skill_commit,
            risk_score=12,
            extra_metadata={
                "security_audit": {"skillspector_score": 12},
            },
        )
        skill_repository = MagicMock()
        skill_repository.load_scan_records = AsyncMock(
            return_value=({skill_id: existing}, {})
        )
        scanner = SkillScanner(
            git_ops=GitOperations(),
            skill_repository=skill_repository,
            category_classifier=None,
        )
        scanner._audit_skill_security = AsyncMock()

        skills, _ = asyncio.run(
            scanner.start_scan(
                repo=repo,
                repo_root=repository,
                repository_git_metadata={"commit_id": repo_head},
            )
        )

        scanner._audit_skill_security.assert_not_awaited()
        assert skills[0].skill_id == skill_id
        assert skills[0].commit_id == skill_commit
        assert skills[0].risk_score == 12
        assert getattr(skills[0], "_security_audit_triggered") is False

    def test_single_repository_discover_failure_marks_repository_failed(self):
        from skillcrawler.core.skill_manager import SkillDiscoverStatus, SkillManager

        repository_id = uuid.uuid4()
        repository = SimpleNamespace(
            id=repository_id,
            repo_name="github.com_acme_repository",
            url="https://github.com/acme/repository",
            branch="main",
            platform="personal",
            skill_num=7,
            skill_discover_status=SkillDiscoverStatus.DONE,
        )
        skill_repository = MagicMock()
        skill_repository.session = MagicMock()
        skill_repository.session.rollback = AsyncMock()
        repo_repository = MagicMock()
        repo_repository.get_skill_repository_by_id = AsyncMock(return_value=repository)
        repo_repository.update_skill_repository = AsyncMock(return_value=repository)
        manager = SkillManager(skill_repository, repo_repository)

        with patch.object(
            SkillManager,
            "_sync_git_repository",
            side_effect=RuntimeError("fetch failed"),
        ):
            with pytest.raises(ValueError, match="fetch failed"):
                asyncio.run(
                    manager.discover_skills_from_single_existing_repository(
                        str(repository_id),
                    )
                )

        skill_repository.session.rollback.assert_awaited_once()
        assert repo_repository.update_skill_repository.await_args_list[-1].args == (
            repository_id,
        )
        assert repo_repository.update_skill_repository.await_args_list[-1].kwargs == {
            "skill_discover_status": SkillDiscoverStatus.FAILED,
            "skill_num": 7,
        }

    async def test_configured_discover_force_does_not_skip_commit_unchanged_check(self):
        from skillcrawler.core.skill_manager import SkillManager, SkillRepositoryRequest

        skill_repository = MagicMock()
        skill_repository.list_unscored_by_skill_repo = AsyncMock(return_value=([], []))
        manager = SkillManager(skill_repository, MagicMock())
        discover_mock = AsyncMock()
        with (
            patch.object(SkillManager, "_sync_git_repository"),
            patch.object(SkillManager, "_has_skill_md", return_value=True),
            patch.object(SkillManager, "_is_commit_unchanged", return_value=True),
            patch.object(
                SkillManager,
                "_get_or_create_skill_repository",
                AsyncMock(return_value=(SimpleNamespace(id=uuid.uuid4()), False)),
            ),
            patch.object(SkillManager, "_discover_and_store_skills", discover_mock),
        ):
            result = await manager.discover_configured_skill_repository(
                SkillRepositoryRequest(url="https://github.com/acme/agent-skills")
            )

        assert getattr(result, "_unchanged") is True
        discover_mock.assert_not_called()

    async def test_commit_unchanged_retries_unscored_security_audits(self):
        from skillcrawler.core.skill_manager import SkillManager, SkillRepositoryRequest

        manager = SkillManager(MagicMock(), MagicMock())
        retry_mock = AsyncMock(return_value=(3, 2))
        discover_mock = AsyncMock()
        repository = SimpleNamespace(id=uuid.uuid4())
        with (
            patch.object(SkillManager, "_sync_git_repository"),
            patch.object(SkillManager, "_has_skill_md", return_value=True),
            patch.object(SkillManager, "_is_commit_unchanged", return_value=True),
            patch.object(
                SkillManager,
                "_get_or_create_skill_repository",
                AsyncMock(return_value=(repository, False)),
            ),
            patch.object(
                SkillManager,
                "_retry_unscored_security_audits",
                retry_mock,
            ),
            patch.object(SkillManager, "_discover_and_store_skills", discover_mock),
        ):
            result = await manager.discover_configured_skill_repository(
                SkillRepositoryRequest(url="https://github.com/acme/agent-skills")
            )

        assert getattr(result, "_security_retry_candidates") == 3
        assert getattr(result, "_security_retriggered") == 2
        retry_mock.assert_awaited_once_with(repository)
        discover_mock.assert_not_called()

    async def test_retry_unscored_security_audits_updates_pending_audit(self):
        from skillcrawler.core.skill_manager import SkillManager, settings

        session = MagicMock()
        session.commit = AsyncMock()
        skill_repository = MagicMock()
        skill_repository.session = session
        record = SimpleNamespace(
            id=uuid.uuid4(),
            skill_id="github/acme/agent-skills/skills/example",
            version="latest",
            commit_id="a" * 40,
            source_url=(
                "https://github.com/acme/agent-skills/"
                "blob/main/skills/example/SKILL.md"
            ),
            extra_metadata={},
        )
        skill_repository.list_unscored_by_skill_repo = AsyncMock(
            return_value=([record], []),
        )
        manager = SkillManager(skill_repository, MagicMock())
        manager._scanner.security_detector = SimpleNamespace(has_skillspector=True)
        manager._scanner.audit_existing_skill = AsyncMock(
            return_value=SimpleNamespace(
                details={
                    "skillspector_async": True,
                    "skillspector_build_number": 123,
                    "source": "skillspector",
                }
            )
        )
        repository = SimpleNamespace(
            id=uuid.uuid4(),
            repo_name="github.com_acme_agent-skills",
            source="github",
            url="https://github.com/acme/agent-skills",
            branch="main",
        )
        audit_repository = MagicMock()
        audit_repository.upsert_by_resource = AsyncMock()

        with (
            patch.object(settings.security, "enable_audit", True),
            patch(
                "skillcrawler.core.skill_manager.SecurityAuditRepository",
                return_value=audit_repository,
            ),
        ):
            candidates, triggered = await manager._retry_unscored_security_audits(
                repository,
            )

        assert (candidates, triggered) == (1, 1)
        manager._scanner.audit_existing_skill.assert_awaited_once_with(
            repo=repository,
            relative_path="skills/example/SKILL.md",
            commit_id="a" * 40,
            skill_id=record.skill_id,
        )
        assert record.extra_metadata["security_audit"]["skillspector_build_number"] == 123
        audit_repository.upsert_by_resource.assert_awaited_once()
        session.commit.assert_awaited_once()

    async def test_discover_store_uses_one_final_repository_commit(self, tmp_path):
        from skillcrawler.core.skill_manager import SkillManager

        skill_repository = MagicMock()
        skill_repository.store_skills_and_versions = AsyncMock()
        repo_repository = MagicMock()
        updated_repo = SimpleNamespace(id=uuid.uuid4())
        repo_repository.update_skill_repository = AsyncMock(return_value=updated_repo)
        manager = SkillManager(skill_repository, repo_repository)
        manager._git_ops.get_repository_head_commit_id = MagicMock(
            return_value="c" * 40,
        )
        repo = SimpleNamespace(
            id=updated_repo.id,
            platform=None,
        )

        with (
            patch.object(
                SkillManager,
                "_discover_skills",
                AsyncMock(return_value=([], [])),
            ),
            patch.object(
                SkillManager,
                "_store_to_security_audits",
                AsyncMock(),
            ),
        ):
            result = await manager._discover_and_store_skills(
                repo,
                clone_dir=tmp_path,
                repo_name="github.com_acme_skills",
            )

        skill_repository.store_skills_and_versions.assert_awaited_once_with(
            repo.id,
            [],
            [],
            commit=False,
        )
        repo_repository.update_skill_repository.assert_awaited_once_with(
            repo.id,
            repository_commit_id="c" * 40,
            skill_discover_status="done",
            skill_num=0,
        )
        assert result is updated_repo

    async def test_security_audit_store_uses_runtime_trigger_flag(self):
        from skillcrawler.core.skill_manager import SkillManager

        skill_repository = MagicMock()
        skill_repository.session = MagicMock()
        manager = SkillManager(skill_repository, MagicMock())
        audit_repository = MagicMock()
        audit_repository.upsert_by_resource = AsyncMock()
        details = {
            "skillspector_async": True,
            "skillspector_build_number": 123,
        }
        reused = SimpleNamespace(
            id=uuid.uuid4(),
            skill_id="reused",
            version="latest",
            commit_id="a" * 40,
            extra_metadata={"security_audit": details},
            _security_audit_triggered=False,
        )
        triggered = SimpleNamespace(
            id=uuid.uuid4(),
            skill_id="triggered",
            version="latest",
            commit_id="b" * 40,
            extra_metadata={"security_audit": details},
            _security_audit_triggered=True,
        )

        with patch(
            "skillcrawler.core.skill_manager.SecurityAuditRepository",
            return_value=audit_repository,
        ):
            await manager._store_to_security_audits(
                [reused, triggered],
                [],
            )

        audit_repository.upsert_by_resource.assert_awaited_once()
        assert (
            audit_repository.upsert_by_resource.call_args.kwargs["resource_id"]
            == triggered.id
        )

    def test_security_retry_resolves_path_from_commit_source_url(self):
        from skillcrawler.core.skill_manager import SkillManager

        commit_id = "bdf484685eb2a3e13eb223cbf52adf957a98ffb6"
        repository = SimpleNamespace(
            source="github",
            url="https://github.com/github/gh-aw",
            branch="main",
        )
        record = SimpleNamespace(
            commit_id=commit_id,
            source_url=(
                "https://github.com/github/gh-aw/blob/"
                f"{commit_id}/.github/skills/agentic-workflows/SKILL.md"
            ),
            skill_id="github/github/gh-aw/agentic-workflows",
        )

        assert SkillManager._relative_skill_path(repository, record) == (
            ".github/skills/agentic-workflows/SKILL.md"
        )

    def test_skill_manager_commit_unchanged_uses_skill_repo_commit_field(self, tmp_path):
        from skillcrawler.core.skill_manager import SkillManager

        manager = SkillManager(MagicMock(), MagicMock())
        manager._git_ops = MagicMock()
        manager._git_ops.get_repository_head_commit_id.return_value = "repo-head"

        repository = SimpleNamespace(repository_commit_id="repo-head")

        assert manager._is_commit_unchanged(repository, tmp_path) is True

        repository.repository_commit_id = "older-head"
        assert manager._is_commit_unchanged(repository, tmp_path) is False

    def test_select_skill_by_version_returns_only_match(self):
        from src.models.repository import SkillRepository

        repo = SkillRepository(MagicMock())
        skills = [SimpleNamespace(version="v1.0.0")]

        selected = repo._select_skill_by_version(skills, "v9.9.9")

        assert selected is skills[0]

    def test_select_skill_by_version_prefers_requested_version(self):
        from src.models.repository import SkillRepository

        repo = SkillRepository(MagicMock())
        latest = SimpleNamespace(version="latest")
        requested = SimpleNamespace(version="v1.2.3")
        skills = [latest, requested]

        selected = repo._select_skill_by_version(skills, "v1.2.3")

        assert selected is requested

    def test_select_skill_by_version_defaults_to_latest(self):
        from src.models.repository import SkillRepository

        repo = SkillRepository(MagicMock())
        latest = SimpleNamespace(version="latest")
        older = SimpleNamespace(version="v1.2.3")
        skills = [latest, older]

        selected = repo._select_skill_by_version(skills)

        assert selected is latest

    def test_select_skill_by_version_falls_back_to_original_logic_when_missing(self):
        from src.models.repository import SkillRepository

        repo = SkillRepository(MagicMock())
        latest = SimpleNamespace(version="latest")
        older = SimpleNamespace(version="v1.2.3")
        skills = [latest, older]

        selected = repo._select_skill_by_version(skills, "v9.9.9")

        assert selected is latest

    async def test_create_skill_data_validation(self):
        from src.api.schemas.skill import SkillCreate

        skill_data = {
            "skill_id": "test/skill:v1.0.0",
            "name": "test-skill",
            "description": "Test skill",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "test",
            "source": "clawhub",
            "source_url": "https://example.com/test",
            "category": "Testing",
            "tags": ["test"],
            "platform": "openclaw",
        }
        skill = SkillCreate(**skill_data)
        assert skill.skill_id == "test/skill:v1.0.0"
        assert skill.name == "test-skill"

    async def test_skill_create_missing_required_fields(self):
        from pydantic import ValidationError

        from src.api.schemas.skill import SkillCreate

        with pytest.raises(ValidationError):
            SkillCreate(
                name="test",
                source="clawhub",
                source_url="https://example.com",
            )

    async def test_skill_response_model(self):
        from src.api.schemas.skill import SkillResponse

        skill_dict = {
            "id": str(uuid.uuid4()),
            "skill_id": "test/skill:v1.0.0",
            "name": "test-skill",
            "description": "Test skill",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "test",
            "source": "clawhub",
            "source_url": "https://example.com/test",
            "category": "Testing",
            "tags": ["test"],
            "platform": "openclaw",
            "extra_metadata": {},
            "risk_score": 85,
            "download_count": 10,
            "rating": "4.5",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = SkillResponse(**skill_dict)
        assert response.skill_id == "test/skill:v1.0.0"
        assert response.name == "test-skill"


class TestSearchService:
    async def test_search_service_initialization(self):
        from src.indexer.search import SearchService

        mock_session = MagicMock()
        service = SearchService(mock_session)
        assert service is not None
        assert service.session == mock_session

    def test_semantic_search_skips_text_search(self):
        from unittest.mock import AsyncMock

        from src.indexer.search import SearchService

        service = SearchService(MagicMock())
        service._text_search = AsyncMock()
        service._vector_search = AsyncMock(
            return_value={"results": [], "total": 0, "mode": "semantic"}
        )

        result = asyncio.run(
            service.search_skills(
                query="rocm-kernels",
                embedding=[0.1, 0.2],
                mode="semantic",
            )
        )

        service._text_search.assert_not_awaited()
        service._vector_search.assert_awaited_once()
        assert result["mode"] == "semantic"

    def test_text_search_fetches_only_requested_page(self):
        from src.indexer.search import SearchService

        service = SearchService(MagicMock())
        service._text_search = AsyncMock(
            return_value={"results": [{"skill_id": "skill-1"}], "total": 1}
        )
        service._vector_search = AsyncMock()

        result = asyncio.run(
            service.search_skills(
                query="code",
                limit=12,
                offset=24,
                mode="text",
            )
        )

        service._text_search.assert_awaited_once_with(
            query="code",
            limit=12,
            offset=24,
            category=None,
            platform=None,
            tags=None,
            scope="summary",
            security_level=None,
        )
        service._vector_search.assert_not_awaited()
        assert result["results"] == [{"skill_id": "skill-1"}]


class TestConfig:
    async def test_get_settings(self):
        from src.core.config import get_settings

        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/wittyhub",
            },
        ):
            settings = get_settings()
            assert settings is not None
            assert "postgresql" in settings.postgres.url


class TestAPIRoutes:
    async def test_health_endpoint(self):
        from src.api.routes.health import router

        assert router is not None
        routes = [route.path for route in router.routes]
        assert "/health" in routes


class TestSkillSchema:
    async def test_skill_id_format(self):
        from src.api.schemas.skill import SkillResponse

        skill_data = {
            "id": str(uuid.uuid4()),
            "skill_id": "author/skill-name:v1.0.0",
            "name": "skill-name",
            "description": "Test",
            "version": "v1.0.0",
            "commit_id": "abc123",
            "author": "author",
            "source": "clawhub",
            "source_url": "https://example.com",
            "category": "Testing",
            "tags": ["test"],
            "platform": "openclaw",
            "extra_metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = SkillResponse(**skill_data)
        assert ":" in response.skill_id
        assert response.skill_id.startswith("author/")

    async def test_source_validation(self):
        from src.api.schemas.skill import SkillResponse

        valid_sources = ["local", "github", "clawhub", "gitcode", "gitlab"]
        for source in valid_sources:
            skill_data = {
                "id": str(uuid.uuid4()),
                "skill_id": "test/skill:v1.0.0",
                "name": "skill",
                "description": "Test",
                "version": "v1.0.0",
                "commit_id": "abc123",
                "author": "test",
                "source": source,
                "source_url": "https://example.com",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            response = SkillResponse(**skill_data)
            assert response.source == source
