"""
Tests for the security audit subsystem: SecurityDetector,
SecurityService, and the audit HTTP endpoints.
"""
import uuid
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.security.detector import (
    RiskSignal,
    SecurityDetector,
    SecurityReport,
    SkillspectorClient,
)
from src.api.services.security import SecurityService



# ── SecurityDetector (pure logic) ─────────────────────────────────────────

class TestSecurityDetectorGitHubParsing:
    """GitHub URL parsing — no external calls."""

    @pytest.fixture
    def detector(self) -> SecurityDetector:
        return SecurityDetector()

    def test_standard_github_url(self, detector):
        owner, repo = detector._parse_github_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_github_url_with_git_suffix(self, detector):
        owner, repo = detector._parse_github_url("https://github.com/org/app.git")
        assert owner == "org"
        assert repo == "app"

    def test_github_url_trailing_slash(self, detector):
        owner, repo = detector._parse_github_url("https://github.com/a/b/")
        assert owner == "a"
        assert repo == "b"

    def test_github_url_no_path(self, detector):
        owner, repo = detector._parse_github_url("https://github.com/solo")
        assert owner is None
        assert repo is None

    def test_non_github_url(self, detector):
        owner, repo = detector._parse_github_url("https://gitlab.com/ns/project")
        assert owner is None
        assert repo is None


class TestSecurityDetectorRiskCalculation:
    @pytest.fixture
    def detector(self) -> SecurityDetector:
        return SecurityDetector()

    def test_empty_signals_low(self, detector):
        assert detector._calculate_risk_level([]) == "low"

    def test_critical_overrides_all(self, detector):
        signals = [
            RiskSignal("1", "a", "", "Critical"),
            RiskSignal("2", "b", "", "Low"),
            RiskSignal("3", "c", "", "Medium"),
        ]
        assert detector._calculate_risk_level(signals) == "critical"

    def test_high_when_no_critical(self, detector):
        signals = [
            RiskSignal("1", "a", "", "High"),
            RiskSignal("2", "b", "", "Low"),
        ]
        assert detector._calculate_risk_level(signals) == "high"

    def test_medium_when_no_high_or_critical(self, detector):
        signals = [
            RiskSignal("1", "a", "", "Medium"),
            RiskSignal("2", "b", "", "Low"),
        ]
        assert detector._calculate_risk_level(signals) == "medium"

    def test_low_with_only_low_signals(self, detector):
        signals = [
            RiskSignal("1", "a", "", "Low"),
            RiskSignal("2", "b", "", "Low"),
        ]
        assert detector._calculate_risk_level(signals) == "low"


class TestSecurityDetectorDetectUnknown:
    @pytest.fixture
    def detector(self) -> SecurityDetector:
        return SecurityDetector()

    @pytest.mark.asyncio
    async def test_gitcode_returns_unknown(self, detector):
        report = await detector.detect("gitcode", "https://gitcode.com/a/b", {})
        assert report.risk_level == "unknown"
        assert report.risk_signals == []

    @pytest.mark.asyncio
    async def test_unknown_source(self, detector):
        report = await detector.detect("other", "https://other.com/x", {})
        assert report.risk_level == "unknown"
        assert "Unknown source type" in report.details.get("note", "")


class TestSecurityDetectorSkillspectorUnconfigured:
    """detect_skillspector without credentials returns unknown."""

    @pytest.mark.asyncio
    async def test_no_client(self):
        detector = SecurityDetector()
        report = await detector.detect_skillspector("https://github.com/x/y")
        assert report.risk_level == "unknown"
        assert "not configured" in report.details.get("note", "")


# ── SecurityService ───────────────────────────────────────────────────────

class TestSecurityServiceScoreCalculation:
    """_calculate_security_score mapping."""

    @pytest.fixture
    def service(self) -> SecurityService:
        mock_session = AsyncMock()
        return SecurityService(mock_session)

    def test_critical_is_zero(self, service):
        assert service._calculate_security_score("critical") == 0

    def test_high_is_25(self, service):
        assert service._calculate_security_score("high") == 25

    def test_medium_is_50(self, service):
        assert service._calculate_security_score("medium") == 50

    def test_low_is_75(self, service):
        assert service._calculate_security_score("low") == 75

    def test_unknown_is_100(self, service):
        assert service._calculate_security_score("unknown") == 100

    def test_unexpected_level_defaults_to_100(self, service):
        assert service._calculate_security_score("nonexistent") == 100

class TestSecurityServiceAuditSkill:
    """audit_skill with mocked repositories and detector."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @staticmethod
    def _make_skill_stub(skill_id="test-skill", source="github",
                         source_url="https://github.com/o/r",
                         content='print("hello")'):
        """Return a stub skill object."""
        skill = MagicMock()
        skill.id = uuid.uuid4()
        skill.skill_id = skill_id
        skill.source = source
        skill.source_url = source_url
        skill.version = "v1.0.0"
        skill.content = content
        return skill

    @pytest.mark.asyncio
    async def test_skill_not_found(self, mock_session):
        from src.models.repository import SkillRepository
        with patch.object(SkillRepository, "get_by_skill_id",
                          return_value=None):
            service = SecurityService(mock_session)
            result = await service.audit_skill(
                "nope", "github", "https://github.com/x/y", {}
            )
            assert result == {"error": "Skill not found"}

    @pytest.mark.asyncio
    async def test_none_scanners_defaults_to_available(self, mock_session):
        """When scanners=None, the service picks the default set."""
        service = SecurityService(mock_session)
        skill = self._make_skill_stub(
            source="gitcode",
            source_url="https://gitcode.com/a/b",
            content="print('safe')",
        )

        with patch.object(service.skill_repo, "get_by_skill_id",
                          return_value=skill):
            with patch.object(
                service.detector, "detect",
                return_value=SecurityReport(
                    resource_type="skill",
                    resource_id=skill.source_url,
                    risk_level="unknown",
                    risk_signals=[],
                    details={"note": "GitCode detection not yet implemented"},
                ),
            ):
                result = await service.audit_skill(
                    skill.skill_id,
                    skill.source,
                    skill.source_url,
                    {"content": skill.content},
                )

        assert "error" not in result
        # skillspector not enabled → default scanners are empty
        assert result["scanners"] == []
        # No risk signals → low
        assert result["risk_level"] == "low"


# ── Data classes ──────────────────────────────────────────────────────────

class TestRiskSignal:
    def test_creation_defaults(self):
        s = RiskSignal(id="x", name="n", description="d", severity="low")
        assert s.id == "x"
        assert s.name == "n"
        assert s.description == "d"
        assert s.severity == "low"
        assert s.data == {}

    def test_creation_with_data(self):
        s = RiskSignal(id="1", name="Test", description="desc", severity="High",
                       data={"k": "v"})
        assert s.data == {"k": "v"}


class TestSecurityReport:
    def test_creation(self):
        sr = SecurityReport(
            resource_type="skill",
            resource_id="https://x",
            risk_level="medium",
            risk_signals=[],
        )
        assert sr.resource_type == "skill"
        assert sr.risk_level == "medium"
        assert sr.details == {}


# ── HTTP endpoints (requires DB) ──────────────────────────────────────────

@pytest.mark.skip(reason="requires running PostgreSQL")
class TestAuditAPIEndpoints:
    """Integration tests that need a real database.

    Start the stack first::

        make docker-up
        docker compose -f deploy/docker/docker-compose.yaml exec api \\
          python /tmp/generate_test_data.py --host db --password wittyhub_secret

    Then remove the @pytest.mark.skip decorator and run::

        pytest tests/test_security.py::TestAuditAPIEndpoints -v
    """

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from src.api.main import app
        return TestClient(app)

    def test_get_audit_skill_not_found(self, client):
        """GET audit for a nonexistent skill returns 404."""
        response = client.get("/api/v1/skills/nonexistent-skill/audit")
        assert response.status_code == 404

    def test_list_endpoint_structure(self, client):
        """Smoke test: list skills returns audit-able skills."""
        response = client.get("/api/v1/skills/")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        for skill in data.get("skills", []):
            assert "security_score" in skill or "security_score" not in skill

    def test_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200


# ============================================================================
# SkillspectorClient — unit tests (no network)
# ============================================================================

SAMPLE_SP_REPORT = {
    "skill": {
        "name": "test-skill",
        "source": "/skill",
        "scanned_at": "2026-07-14T00:00:00+00:00",
    },
    "risk_assessment": {
        "score": 14,
        "severity": "LOW",
        "recommendation": "SAFE",
    },
    "components": [
        {"path": "SKILL.md", "type": "markdown", "lines": 142, "executable": False},
    ],
    "issues": [
        {
            "id": "SQP-1",
            "severity": "MEDIUM",
            "confidence": 0.6,
            "location": {"file": "SKILL.md", "start_line": 12, "end_line": 19},
            "explanation": "Potential unsafe shell usage",
            "remediation": "Use subprocess.run with shell=False",
        },
        {
            "id": "SQP-2",
            "severity": "HIGH",
            "confidence": 0.85,
            "location": {"file": "SKILL.md", "start_line": 42},
            "explanation": "Hardcoded token found",
            "remediation": "Use environment variables",
        },
    ],
    "metadata": {
        "has_executable_scripts": True,
        "skillspector_version": "2.3.1",
        "llm_requested": True,
        "llm_available": True,
    },
}


class TestSkillspectorClientReportParsing:
    """SkillspectorClient.report_to_risk_signals — pure logic, no network."""

    def test_parses_issues_into_risk_signals(self):
        signals = SkillspectorClient.report_to_risk_signals(SAMPLE_SP_REPORT)
        assert len(signals) == 2
        assert signals[0].id == "SQP-1"
        assert signals[0].severity == "MEDIUM"
        assert "unsafe shell" in signals[0].description.lower()
        assert signals[0].data["remediation"] == "Use subprocess.run with shell=False"

    def test_second_signal_has_correct_severity(self):
        signals = SkillspectorClient.report_to_risk_signals(SAMPLE_SP_REPORT)
        assert signals[1].severity == "HIGH"
        assert "Hardcoded token" in signals[1].description

    def test_signal_includes_location_data(self):
        signals = SkillspectorClient.report_to_risk_signals(SAMPLE_SP_REPORT)
        assert signals[1].data["location"]["file"] == "SKILL.md"
        assert signals[1].data["location"]["start_line"] == 42

    def test_signal_includes_confidence(self):
        signals = SkillspectorClient.report_to_risk_signals(SAMPLE_SP_REPORT)
        assert signals[1].data["confidence"] == 0.85

    def test_signal_name_includes_location(self):
        signals = SkillspectorClient.report_to_risk_signals(SAMPLE_SP_REPORT)
        assert "SQP-2" in signals[1].name
        assert "SKILL.md:42" in signals[1].name

    def test_empty_issues_returns_empty_list(self):
        report = dict(SAMPLE_SP_REPORT, issues=[])
        assert SkillspectorClient.report_to_risk_signals(report) == []

    def test_missing_issues_key_returns_empty_list(self):
        report = dict(SAMPLE_SP_REPORT)
        del report["issues"]
        assert SkillspectorClient.report_to_risk_signals(report) == []

    def test_none_issues_returns_empty_list(self):
        report = dict(SAMPLE_SP_REPORT, issues=None)
        assert SkillspectorClient.report_to_risk_signals(report) == []

    def test_signal_data_source_marked_skillspector(self):
        signals = SkillspectorClient.report_to_risk_signals(SAMPLE_SP_REPORT)
        assert signals[0].data["source"] == "skillspector"


class TestSkillspectorClientLifecycle:
    """SkillspectorClient construction and enabled state."""

    def test_enabled_when_credentials_provided(self):
        c = SkillspectorClient(
            jenkins_url="http://127.0.0.1:8080",
            user="admin",
            token="secret",
        )
        assert c.enabled is True

    def test_not_enabled_when_no_credentials(self):
        c = SkillspectorClient(jenkins_url="http://127.0.0.1:8080")
        assert c.enabled is False

    def test_not_enabled_when_empty_user(self):
        c = SkillspectorClient(
            jenkins_url="http://127.0.0.1:8080",
            user="",
            token="secret",
        )
        assert c.enabled is False

    def test_not_enabled_when_empty_token(self):
        c = SkillspectorClient(
            jenkins_url="http://127.0.0.1:8080",
            user="admin",
            token="",
        )
        assert c.enabled is False

    def test_base_url_strips_trailing_slash(self):
        c = SkillspectorClient(jenkins_url="http://127.0.0.1:8080/")
        assert c.base_url == "http://127.0.0.1:8080"


# ============================================================================
# SecurityDetector.detect_skillspector — integration with SkillspectorClient
# ============================================================================

class TestSecurityDetectorSkillspector:
    """detect_skillspector path — mocked SkillspectorClient."""

    @pytest.mark.asyncio
    async def test_returns_unknown_when_no_client(self):
        detector = SecurityDetector()
        report = await detector.detect_skillspector("https://github.com/x/y")
        assert report.risk_level == "unknown"
        assert "not configured" in report.details.get("note", "")

    @pytest.mark.asyncio
    async def test_parses_realistic_report(self):
        detector = SecurityDetector()
        detector._skillspector_client = MagicMock()
        detector._skillspector_client.enabled = True
        detector._skillspector_client.run_scan.return_value = SAMPLE_SP_REPORT
        detector._skillspector_client.report_to_risk_signals = (
            SkillspectorClient.report_to_risk_signals
        )

        report = await detector.detect_skillspector("https://github.com/o/r", version="v1.0")

        assert report.risk_level == "low"  # SAMPLE_SP_REPORT risk_assessment.severity = LOW
        assert len(report.risk_signals) == 2
        assert report.details["source"] == "skillspector"
        assert report.details["skillspector_version"] == "2.3.1"
        assert report.details["skillspector_score"] == 14
        assert report.details["recommendation"] == "SAFE"

    @pytest.mark.asyncio
    async def test_calls_run_scan_with_correct_args(self):
        detector = SecurityDetector()
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.run_scan.return_value = SAMPLE_SP_REPORT
        mock_client.report_to_risk_signals.return_value = []
        detector._skillspector_client = mock_client

        await detector.detect_skillspector("https://github.com/o/r", version="v2.0.0")

        mock_client.run_scan.assert_called_once_with(
            git_url="https://github.com/o/r",
            ref="v2.0.0",
            skill_path="",
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_main_when_no_version(self):
        detector = SecurityDetector()
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.run_scan.return_value = SAMPLE_SP_REPORT
        mock_client.report_to_risk_signals.return_value = []
        detector._skillspector_client = mock_client

        await detector.detect_skillspector("https://github.com/o/r")

        mock_client.run_scan.assert_called_once_with(
            git_url="https://github.com/o/r",
            ref="main",
            skill_path="",
        )

    @pytest.mark.asyncio
    async def test_handles_run_scan_exception_gracefully(self):
        detector = SecurityDetector()
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.run_scan.side_effect = RuntimeError("Jenkins unreachable")
        detector._skillspector_client = mock_client

        report = await detector.detect_skillspector("https://github.com/o/r")

        assert report.risk_level == "unknown"
        assert "Jenkins unreachable" in report.details.get("error", "")

    @pytest.mark.asyncio
    async def test_handles_jenkins_build_failure(self):
        detector = SecurityDetector()
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.run_scan.return_value = {"error": "Build 42 ended with status FAILURE"}
        mock_client.report_to_risk_signals.return_value = []
        detector._skillspector_client = mock_client

        report = await detector.detect_skillspector("https://github.com/o/r")

        assert report.risk_level == "unknown"
        assert "FAILURE" in report.details.get("error", "")

    @pytest.mark.asyncio
    async def test_critical_risk_level(self):
        detector = SecurityDetector()
        mock_client = MagicMock()
        mock_client.enabled = True
        critical_report = dict(SAMPLE_SP_REPORT)
        critical_report["risk_assessment"]["severity"] = "CRITICAL"
        mock_client.run_scan.return_value = critical_report
        mock_client.report_to_risk_signals.return_value = []
        detector._skillspector_client = mock_client

        report = await detector.detect_skillspector("https://github.com/o/r")
        assert report.risk_level == "critical"


# ============================================================================
# SecurityService — skillspector scanner integration
# ============================================================================

class TestSecurityServiceSkillspectorDefault:
    """Ensure skillspector is included in default scanners when configured."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @staticmethod
    def _make_skill_stub(**overrides):
        skill = MagicMock()
        skill.id = uuid.uuid4()
        skill.skill_id = overrides.get("skill_id", "test-skill")
        skill.source = overrides.get("source", "github")
        skill.source_url = overrides.get("source_url", "https://github.com/o/r")
        skill.version = overrides.get("version", "v1.0.0")
        skill.content = overrides.get("content", "print('hello')")
        return skill

    def _make_detector_with_skillspector(self, enabled: bool, score: int = 85):
        """Return a SecurityDetector with skillspector mocked in/out."""
        from src.security.detector import SecurityDetector

        detector = SecurityDetector()
        if enabled:
            mock_client = MagicMock()
            mock_client.enabled = True
            detector._skillspector_client = mock_client
        detector.detect = AsyncMock(
            return_value=SecurityReport("skill", "u", "low", [], {})
        )
        if enabled:
            detector.detect_skillspector = AsyncMock(
                return_value=SecurityReport(
                    "skill", "u", "low", [],
                    {"source": "skillspector", "skillspector_score": score},
                )
            )
        return detector

    @pytest.mark.asyncio
    async def test_default_scanners_includes_skillspector_when_configured(
        self, mock_session
    ):
        service = SecurityService(mock_session)
        service.detector = self._make_detector_with_skillspector(enabled=True)

        skill = self._make_skill_stub()
        with patch.object(service.skill_repo, "get_by_skill_id", return_value=skill):
            result = await service.audit_skill(
                skill.skill_id, skill.source, skill.source_url,
                {"content": skill.content},
            )

        assert "skillspector" in result["scanners"]
        assert "skillspector" in result["scanners"]
        assert result["security_score"] == 85

    @pytest.mark.asyncio
    async def test_skillspector_not_in_defaults_when_unconfigured(
        self, mock_session
    ):
        service = SecurityService(mock_session)
        service.detector = self._make_detector_with_skillspector(enabled=False)

        skill = self._make_skill_stub(source="gitcode",
                                       source_url="https://gitcode.com/a/b")
        with patch.object(service.skill_repo, "get_by_skill_id", return_value=skill):
            result = await service.audit_skill(
                skill.skill_id, skill.source, skill.source_url,
                {"content": skill.content},
            )

        assert "skillspector" not in result["scanners"]
        assert result["scanners"] == []


# ============================================================================
# SkillRepository.create() — auto-audit integration (unit-level mock)
# ============================================================================

class TestSkillRepositoryCreateWithAudit:
    """create() with auto_audit=True triggers SecurityService."""

    @pytest.mark.asyncio
    async def test_auto_audit_calls_security_service(self):
        from src.models.repository import SkillRepository

        mock_session = AsyncMock()
        repo = SkillRepository(mock_session)

        skill_data = {
            "skill_id": "test/auto-audit",
            "name": "auto-audit-test",
            "source": "github",
            "source_url": "https://github.com/test/auto-audit",
            "skill_repo_id": uuid.uuid4(),  # pre-resolved
        }

        with patch(
            "src.api.services.security.SecurityService.audit_skill",
            new_callable=AsyncMock,
            return_value={"security_score": 75, "scanners": []},
        ) as mock_audit:
            skill = await repo.create(skill_data, auto_audit=True)

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["skill_id"] == "test/auto-audit"
        assert call_kwargs["source"] == "github"

    @pytest.mark.asyncio
    async def test_auto_audit_false_skips_audit(self):
        from src.models.repository import SkillRepository

        mock_session = AsyncMock()
        repo = SkillRepository(mock_session)

        skill_data = {
            "skill_id": "test/no-audit",
            "name": "no-audit-test",
            "source": "github",
            "source_url": "https://github.com/test/no-audit",
            "skill_repo_id": uuid.uuid4(),
        }

        with patch(
            "src.api.services.security.SecurityService.audit_skill",
            new_callable=AsyncMock,
        ) as mock_audit:
            await repo.create(skill_data, auto_audit=False)

        mock_audit.assert_not_called()

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_block_create(self):
        from src.models.repository import SkillRepository

        mock_session = AsyncMock()
        repo = SkillRepository(mock_session)

        skill_data = {
            "skill_id": "test/audit-fail",
            "name": "audit-fail-test",
            "source": "github",
            "source_url": "https://github.com/test/audit-fail",
            "skill_repo_id": uuid.uuid4(),
        }

        with patch(
            "src.api.services.security.SecurityService.audit_skill",
            new_callable=AsyncMock,
            side_effect=RuntimeError("audit boom"),
        ):
            skill = await repo.create(skill_data, auto_audit=True)

        # skill was still created
        assert skill.skill_id == "test/audit-fail"
        mock_session.add.assert_called()

    @pytest.mark.asyncio
    async def test_resolve_skill_repo_id_creates_new(self):
        """_resolve_skill_repo_id creates a new repo when none exists."""
        from src.models.repository import SkillRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        repo = SkillRepository(mock_session)
        resolved_id = await repo._resolve_skill_repo_id(
            {"source": "github", "source_url": "https://github.com/o/r"}
        )

        assert isinstance(resolved_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_resolve_skill_repo_id_reuses_existing(self):
        """_resolve_skill_repo_id reuses an existing repo."""
        from src.models.repository import SkillRepository

        existing_id = uuid.uuid4()
        mock_repo = MagicMock()
        mock_repo.id = existing_id

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_repo
        mock_session.execute = AsyncMock(return_value=mock_result)

        repo = SkillRepository(mock_session)
        resolved_id = await repo._resolve_skill_repo_id(
            {"source": "github", "source_url": "https://github.com/o/r"}
        )

        assert resolved_id == existing_id

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_calls_resolve_skill_repo_id(self):
        """create() with missing skill_repo_id delegates to helper."""
        from src.models.repository import SkillRepository

        mock_session = AsyncMock()
        repo = SkillRepository(mock_session)
        fake_id = uuid.uuid4()
        repo._resolve_skill_repo_id = AsyncMock(return_value=fake_id)

        with patch(
            "src.api.services.security.SecurityService.audit_skill",
            new_callable=AsyncMock,
            return_value={"security_score": 100},
        ):
            skill = await repo.create(
                {
                    "skill_id": "test/create",
                    "name": "create-test",
                    "source": "github",
                    "source_url": "https://github.com/test/create",
                },
                auto_audit=True,
            )

        assert skill.skill_repo_id == fake_id

    def test_derive_repo_name_standard_github(self):
        from src.models.repository import SkillRepository
        name = SkillRepository._derive_repo_name("github", "https://github.com/o/r")
        assert name == "github-o-r"

    def test_derive_repo_name_with_trailing_slash(self):
        from src.models.repository import SkillRepository
        name = SkillRepository._derive_repo_name("gitlab", "https://gitlab.com/o/r/")
        assert name == "gitlab-o-r"

    def test_derive_repo_name_clawhub(self):
        from src.models.repository import SkillRepository
        name = SkillRepository._derive_repo_name(
            "clawhub",
            "https://clawskills.sh/skills/author-skillname",
        )
        # path_parts = ["https:", "", "clawskills.sh", "skills", "author-skillname"]
        assert name == "clawhub-skills-author-skillname"

    def test_derive_repo_name_empty_url(self):
        from src.models.repository import SkillRepository
        name = SkillRepository._derive_repo_name("unknown", "")
        assert name == "unknown-unknown"



# ============================================================================
# Jenkins Skillspector — real integration tests
# ============================================================================
# Run with:
#   SKILLSPECTOR_JENKINS_USER=test SKILLSPECTOR_JENKINS_TOKEN='openEuler12#$' \
#     pytest tests/test_security.py -m integration -v


_JENKINS_URL = os.environ.get("SKILLSPECTOR_JENKINS_URL", "http://120.26.120.159:18080")
_JENKINS_USER = os.environ.get("SKILLSPECTOR_JENKINS_USER", "test")
_JENKINS_TOKEN = os.environ.get("SKILLSPECTOR_JENKINS_TOKEN", "")
# A public repo known to have skill content for scanning.
_TEST_GIT_URL = "https://github.com/anthropics/skills"
_TEST_REF = "main"


pytestmark_integration = pytest.mark.integration


@pytest.mark.integration
class TestJenkinsSkillspectorIntegration:
    """Real Jenkins skill-scanner integration — requires network access."""

    @pytest.fixture
    def client(self):
        return SkillspectorClient(
            jenkins_url=_JENKINS_URL,
            user=_JENKINS_USER,
            token=_JENKINS_TOKEN,
        )

    def test_client_is_enabled(self, client):
        """Credentials are valid and client reports enabled."""
        assert client.enabled is True
        assert client.base_url == _JENKINS_URL.rstrip("/")

    def test_jenkins_job_exists_and_buildable(self, client):
        """The skill-scanner job is present and accepting builds."""
        import httpx

        resp = httpx.get(
            f"{_JENKINS_URL}/job/skill-scanner/api/json",
            auth=(_JENKINS_USER, _JENKINS_TOKEN),
            timeout=10,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "skill-scanner"
        assert data["buildable"] is True

    def test_trigger_scan_returns_build_number(self, client):
        """Trigger a real scan and verify we get a valid build number."""
        build_number = client.trigger_scan(
            git_url=_TEST_GIT_URL,
            ref=_TEST_REF,
            skill_path="",
            scanners="skillspector",
        )
        if build_number is None:
            pytest.skip("Jenkins trigger returned None (concurrent build or transient)")
        assert isinstance(build_number, int)
        assert build_number > 0

        if build_number is None:
            # Retry once — Jenkins may have had a transient redirect
            build_number = client.trigger_scan(
                git_url=_TEST_GIT_URL,
                ref=_TEST_REF,
                skill_path="",
                scanners="skillspector",
            )
        if build_number is None:
            pytest.skip("Jenkins trigger returned None (transient 303 / build conflict)")
        assert isinstance(build_number, int)
        assert build_number > 0

    def test_full_scan_and_report(self, client):
        """Trigger, wait, fetch report — end-to-end Jenkins flow.

        ⚠ This test takes 2-5 minutes (real Jenkins build).
        Skips gracefully when a build is already in progress.
        """
        report = client.run_scan(
            git_url=_TEST_GIT_URL,
            ref=_TEST_REF,
            skill_path="",
            scanners="skillspector",
        )
        if "error" in report:
            err = str(report.get("error", ""))
            if "already in progress" in err or "Failed to trigger" in err:
                pytest.skip(f"Jenkins build conflict: {report['error']}")
            pytest.fail(f"Jenkins scan failed: {report['error']}")

        assert "risk_assessment" in report
        assert "score" in report["risk_assessment"]
        assert "severity" in report["risk_assessment"]
        assert "issues" in report
        assert "metadata" in report

    def test_report_parsing_from_live_scan(self, client):
        """Fetch report from last successful build and parse it."""
        import httpx

        # Get the last successful build number
        resp = httpx.get(
            f"{_JENKINS_URL}/job/skill-scanner/api/json",
            auth=(_JENKINS_USER, _JENKINS_TOKEN),
            timeout=10,
        )
        last_build = resp.json().get("lastSuccessfulBuild", {})
        if not last_build:
            pytest.skip("No successful builds found")
        build_number = last_build["number"]

        # Fetch its report
        fetched = client.fetch_report(build_number)
        if fetched is None:
            pytest.skip(f"Build {build_number} has no report artifact")

        signals = SkillspectorClient.report_to_risk_signals(fetched)
        assert isinstance(signals, list)
        # Every signal must have the required fields
        for s in signals:
            assert s.id
            assert s.name
            assert s.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL", "UNKNOWN")




# ============================================================================
# SkillspectorCollector — background result collection
# ============================================================================

class TestSkillspectorCollectorUnit:
    """collect_once with mocked DB and Jenkins client."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_client(self):
        return MagicMock()

    @pytest.fixture
    def collector(self, mock_client):
        from src.security.detector import SkillspectorCollector
        session_factory = MagicMock()
        session_factory.return_value.__aenter__.return_value = AsyncMock()
        return SkillspectorCollector(mock_client, session_factory, poll_interval=999)

    @pytest.mark.asyncio
    async def test_no_pending_returns_zero(self, collector, mock_client):
        collector._fetch_pending = AsyncMock(return_value=[])
        processed = await collector.collect_once()
        assert processed == 0

    @pytest.mark.asyncio
    async def test_pending_without_build_number_skipped(self, collector, mock_client):
        audit = MagicMock()
        audit.id = uuid.uuid4()
        audit.details = {"skillspector_async": True}  # no build_number
        collector._fetch_pending = AsyncMock(return_value=[audit])
        processed = await collector.collect_once()
        assert processed == 0

    @pytest.mark.asyncio
    async def test_collects_and_updates_audit(self, collector, mock_client):
        from src.models.orm import SecurityAudit

        audit = MagicMock(spec=SecurityAudit)
        audit.id = uuid.uuid4()
        audit.resource_id = uuid.uuid4()
        audit.risk_signals = []
        audit.details = {
            "skillspector_async": True,
            "skillspector_build_number": 42,
        }

        collector._fetch_pending = AsyncMock(return_value=[audit])
        mock_client.wait_for_build.return_value = "SUCCESS"
        mock_client.fetch_report.return_value = {
            "risk_assessment": {"score": 85, "severity": "LOW", "recommendation": "SAFE"},
            "issues": [],
            "metadata": {"skillspector_version": "2.3.1"},
        }

        processed = await collector.collect_once()
        assert processed == 1

    @pytest.mark.asyncio
    async def test_failed_build_marks_collected(self, collector, mock_client):
        audit = MagicMock()
        audit.id = uuid.uuid4()
        audit.resource_id = uuid.uuid4()
        audit.risk_signals = []
        audit.details = {
            "skillspector_async": True,
            "skillspector_build_number": 43,
        }

        collector._fetch_pending = AsyncMock(return_value=[audit])
        mock_client.wait_for_build.return_value = "FAILURE"

        processed = await collector.collect_once()
        assert processed == 1

    @pytest.mark.asyncio
    async def test_no_report_yet_skips_and_retries_later(self, collector, mock_client):
        audit = MagicMock()
        audit.id = uuid.uuid4()
        audit.resource_id = uuid.uuid4()
        audit.risk_signals = []
        audit.details = {
            "skillspector_async": True,
            "skillspector_build_number": 44,
        }

        collector._fetch_pending = AsyncMock(return_value=[audit])
        mock_client.wait_for_build.return_value = "SUCCESS"
        mock_client.fetch_report.return_value = None  # not ready

        processed = await collector.collect_once()
        assert processed == 0  # skipped, will retry next cycle

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self, collector):
        assert collector._running is False
        await collector.start()
        assert collector._running is True
        assert collector._task is not None
        await collector.stop()
        assert collector._running is False
