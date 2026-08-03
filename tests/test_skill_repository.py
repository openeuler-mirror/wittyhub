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
        skill_repository.get_category_by_skill_id = AsyncMock(return_value=None)
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
        assert skills[0].extra_metadata["skill_directory_commit_id"] == skill_dir_commit

    async def test_configured_discover_force_does_not_skip_commit_unchanged_check(self):
        from skillcrawler.core.skill_manager import SkillManager, SkillRepositoryRequest

        manager = SkillManager(MagicMock(), MagicMock())
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
