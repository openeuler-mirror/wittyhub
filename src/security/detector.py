"""Security detection engine — unified entry point for all audit scanners.

Components
----------
* Skillspector       — Jenkins‑based deep code audit (sync + async)
"""
import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Shared data structures
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class RiskSignal:
    id: str
    name: str
    description: str
    severity: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityReport:
    resource_type: str
    resource_id: str
    risk_level: str
    risk_signals: list[RiskSignal]
    details: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# Skillspector — Jenkins‑based deep scanner
# ═══════════════════════════════════════════════════════════════════════════


class SkillspectorClient:
    """Client for the skill-scanner Jenkins job that runs Skillspector.

    The Jenkins job accepts parameters:
        GIT_URL, REF, SKILL_PATH, SCANNERS

    On success the build produces:
        reports/skillspector/report.json
    """

    JOB_PATH = "/job/skill-scanner"

    def __init__(
        self,
        jenkins_url: str,
        user: str = "",
        token: str = "",
        timeout: float = 150.0,
        poll_interval: float = 5.0,
    ):
        self.base_url = jenkins_url.rstrip("/")
        self.auth = (user, token) if user and token else None
        self.timeout = timeout
        self.poll_interval = poll_interval

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """True when the client has credentials and a valid URL."""
        return self.auth is not None and bool(self.base_url)

    def run_scan(
        self,
        git_url: str,
        ref: str = "main",
        skill_path: str = "",
        scanners: str = "skillspector",
    ) -> dict[str, Any]:
        """Convenience: trigger a build, wait for it, and return the report."""
        build_number = self.trigger_scan(git_url, ref, skill_path, scanners)
        if build_number is None:
            return {"error": "Failed to trigger Jenkins build"}
        status = self.wait_for_build(build_number)
        if status != "SUCCESS":
            return {"error": f"Build {build_number} ended with status {status}"}
        report = self.fetch_report(build_number)
        if report is None:
            return {"error": f"Failed to fetch report for build {build_number}"}
        return report

    # ------------------------------------------------------------------
    # Low-level Jenkins API
    # ------------------------------------------------------------------

    def _get_crumb(self, client: httpx.Client) -> tuple[str, str] | None:
        try:
            resp = client.get(
                f"{self.base_url}/crumbIssuer/api/json", auth=self.auth
            )
            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("crumbRequestField", "Jenkins-Crumb"),
                    data.get("crumb", ""),
                )
        except httpx.RequestError:
            pass
        return None

    def trigger_scan(
        self,
        git_url: str,
        ref: str = "main",
        skill_path: str = "",
        scanners: str = "skillspector",
    ) -> int | None:
        """Trigger a build via buildWithParameters; return the build number."""
        url = f"{self.base_url}{self.JOB_PATH}/buildWithParameters"
        params = {
            "GIT_URL": git_url,
            "REF": ref,
            "SKILL_PATH": skill_path,
            "SCANNERS": scanners,
        }

        with httpx.Client(timeout=30.0) as client:
            headers: dict[str, str] = {}
            crumb = self._get_crumb(client)
            if crumb is not None:
                headers[crumb[0]] = crumb[1]

            try:
                resp = client.post(url, data=params, auth=self.auth, headers=headers)
            except httpx.RequestError as exc:
                logger.error("Failed to reach Jenkins: %s", exc)
                return None

        if resp.status_code not in (200, 201, 302, 303):
            logger.error(
                "Jenkins trigger returned %d: %s", resp.status_code, resp.text[:500]
            )
            return None

        location = resp.headers.get("Location", "")
        if not location:
            logger.warning("No Location header in Jenkins response")
            return None

        return self._resolve_queue_item(location)

    def wait_for_build(
        self,
        build_number: int,
        max_wait: float | None = None,
    ) -> str | None:
        """Poll build status until it finishes.  Returns SUCCESS/FAILURE/ABORTED/UNSTABLE/None."""
        max_wait = max_wait if max_wait is not None else self.timeout
        url = f"{self.base_url}{self.JOB_PATH}/{build_number}/api/json"

        deadline = time.monotonic() + max_wait

        with httpx.Client(timeout=10.0) as client:
            while time.monotonic() < deadline:
                try:
                    resp = client.get(url, auth=self.auth)
                except httpx.RequestError as exc:
                    logger.warning("Polling Jenkins failed: %s", exc)
                    time.sleep(self.poll_interval)
                    continue

                if resp.status_code != 200:
                    time.sleep(self.poll_interval)
                    continue

                data = resp.json()
                building = data.get("building", False)
                result = data.get("result")

                if not building and result is not None:
                    return result

                time.sleep(self.poll_interval)

        logger.error("Build %d did not finish within %.0f s", build_number, max_wait)
        return None

    def fetch_report(self, build_number: int) -> dict[str, Any] | None:
        """Fetch the JSON report artifact from a completed build."""
        url = (
            f"{self.base_url}{self.JOB_PATH}/{build_number}"
            "/artifact/reports/skillspector/report.json"
        )
        with httpx.Client(timeout=30.0) as client:
            try:
                resp = client.get(url, auth=self.auth)
            except httpx.RequestError as exc:
                logger.error("Failed to fetch report: %s", exc)
                return None

        if resp.status_code != 200:
            logger.error(
                "Report fetch failed: build_number=%s status_code=%s url=%s response=%s",
                build_number,
                resp.status_code,
                url,
                resp.text[:500],
            )
            return None

        try:
            return resp.json()
        except ValueError as exc:
            logger.error("Invalid JSON in report: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Report parsing
    # ------------------------------------------------------------------

    @staticmethod
    def report_to_risk_signals(report: dict[str, Any]) -> list[RiskSignal]:
        """Convert a skillspector report dict into RiskSignal objects."""
        signals: list[RiskSignal] = []

        issues = report.get("issues", []) or []
        for issue in issues:
            issue_id = issue.get("id", "unknown")
            severity = issue.get("severity", "UNKNOWN").upper()
            explanation = issue.get("explanation", issue.get("finding", ""))
            remediation = issue.get("remediation", "")
            confidence = issue.get("confidence")
            location = issue.get("location", {})

            loc_str = ""
            if isinstance(location, dict):
                fname = location.get("file", "")
                line = location.get("start_line", "")
                if fname:
                    loc_str = f" ({fname}" + (f":{line})" if line else ")")
            name = f"Skillspector {issue_id}{loc_str}"

            signals.append(
                RiskSignal(
                    id=issue_id,
                    name=name,
                    description=explanation,
                    severity=severity,
                    data={
                        "remediation": remediation,
                        "confidence": confidence,
                        "location": location,
                        "source": "skillspector",
                    },
                )
            )

        return signals

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_queue_item(self, location: str) -> int | None:
        """Poll a Jenkins queue item URL until a build number is assigned."""
        if location.startswith("http"):
            url = f"{location.rstrip('/')}/api/json"
        else:
            url = f"{self.base_url}{location.rstrip('/')}/api/json"

        deadline = time.monotonic() + 60.0

        with httpx.Client(timeout=10.0) as client:
            while time.monotonic() < deadline:
                try:
                    resp = client.get(url, auth=self.auth)
                except httpx.RequestError:
                    time.sleep(self.poll_interval)
                    continue

                if resp.status_code != 200:
                    time.sleep(self.poll_interval)
                    continue

                data = resp.json()
                executable = data.get("executable")
                if executable and isinstance(executable, dict):
                    return executable.get("number")

                if data.get("cancelled") or data.get("stuck"):
                    logger.error("Queue item stuck/cancelled: %s", data)
                    return None

                time.sleep(self.poll_interval)

        logger.error("Queue item did not resolve within 60 s")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Background collector — polls Jenkins for async scan results
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_POLL_INTERVAL_SECONDS = 30


class SkillspectorCollector:
    """Polls Jenkins for completed async scans and updates DB records."""

    def __init__(
        self,
        client: SkillspectorClient,
        session_factory: Any,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ):
        self._client = client
        self._session_factory = session_factory
        self._poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("SkillspectorCollector started (poll every %ds)", self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SkillspectorCollector stopped")

    async def collect_once(self) -> int:
        """Scan for pending async audits and collect completed results.

        Returns the number of audits whose results were successfully collected.
        """
        processed = 0
        async with self._session_factory() as session:
            pending = await self._fetch_pending(session)
            for audit in pending:
                audit_id = audit.id
                build_number = (audit.details or {}).get("skillspector_build_number")
                if build_number is None:
                    continue
                try:
                    if await self._collect_one(session, audit, build_number):
                        processed += 1
                except Exception:
                    # Roll back to keep session usable for subsequent pending audits
                    await session.rollback()
                    logger.exception(
                        "Failed to collect result for audit %s (build #%s)",
                        audit_id, build_number,
                    )
        return processed

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        while self._running:
            try:
                processed = await self.collect_once()
                if processed:
                    logger.info("Collected %d async audit result(s)", processed)
            except Exception:
                logger.exception("SkillspectorCollector loop error")
            await asyncio.sleep(self._poll_interval)

    async def _fetch_pending(self, session: AsyncSession) -> list[Any]:
        # late import to avoid circular deps
        from src.models.orm import SecurityAudit

        result = await session.execute(
            select(SecurityAudit)
            .where(
                SecurityAudit.details["skillspector_async"].as_boolean() == True,  # noqa: E712
                SecurityAudit.details["skillspector_collected"].is_(None),
            )
            .limit(10)
        )
        return list(result.scalars().all())

    async def _collect_one(
        self, session: AsyncSession, audit: Any, build_number: int,
    ) -> bool:
        """Collect a single Jenkins result.  Returns True if collected."""
        from src.models.orm import SecurityAudit, Skill, SkillVersion

        logger.info(
            "Collecting Skillspector result: audit_id=%s build_number=%s",
            audit.id,
            build_number,
        )

        # 1. Wait for build (offload sync HTTP polling to a worker thread)
        status = await asyncio.to_thread(self._client.wait_for_build, build_number)
        if status != "SUCCESS":
            details = dict(audit.details or {})
            details["skillspector_collected"] = True
            details["skillspector_status"] = status
            await session.execute(
                update(SecurityAudit)
                .where(SecurityAudit.id == audit.id)
                .values(details=details)
            )
            await session.commit()
            return True

        # 2. Fetch report (also sync HTTP → offload)
        report = await asyncio.to_thread(self._client.fetch_report, build_number)
        if report is None:
            logger.warning(
                "Build #%d ended with %s but report is unavailable; will retry",
                build_number,
                status,
            )
            return False

        # 3. Parse & update
        signals = SkillspectorClient.report_to_risk_signals(report)
        severity = report.get("risk_assessment", {}).get("severity", "LOW").upper()
        score = report.get("risk_assessment", {}).get("score")

        risk_level_map = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "critical"}
        risk_level = risk_level_map.get(severity, "low")

        details = dict(audit.details or {})
        details["skillspector_collected"] = True
        details["skillspector_score"] = score
        details["skillspector_version"] = report.get("metadata", {}).get("skillspector_version")
        details["recommendation"] = report.get("risk_assessment", {}).get("recommendation")
        details["skillspector_report"] = report

        merged_signals = list(audit.risk_signals or []) + [s.__dict__ for s in signals]

        await session.execute(
            update(SecurityAudit)
            .where(SecurityAudit.id == audit.id)
            .values(risk_level=risk_level, risk_signals=merged_signals, details=details)
        )

        if score is not None:
            skill = await session.get(Skill, audit.resource_id)
            if skill is not None:
                skill.risk_score = score
            else:
                skill_version = await session.get(SkillVersion, audit.resource_id)
                if skill_version is not None:
                    skill_version.risk_score = score
                else:
                    logger.warning(
                        "Security audit resource not found: resource_id=%s",
                        audit.resource_id,
                    )

        await session.commit()
        logger.info(
            "Collected build #%d → score=%s risk=%s signals=%d",
            build_number, score, risk_level, len(signals),
        )
        return True


# ═══════════════════════════════════════════════════════════════════════════
# SecurityDetector — unified detection engine
# ═══════════════════════════════════════════════════════════════════════════


class SecurityDetector:

    def __init__(self):
        self.enable_audit = settings.security.enable_audit

        # Skillspector (Jenkins-based scanner)
        self._skillspector_client: SkillspectorClient | None = None
        if settings.security.enable_audit:
            self._skillspector_client = SkillspectorClient(
                jenkins_url=settings.security.skillspector_jenkins_url,
                user=settings.security.skillspector_jenkins_user,
                token=settings.security.skillspector_jenkins_token,
            )
            if not self._skillspector_client.enabled:
                logger.warning("skillspector enabled but no credentials configured")

    async def detect(self, source: str, source_url: str, metadata: dict[str, Any]) -> SecurityReport:
        return self._create_unknown_report(source_url)

    @staticmethod
    def _calculate_risk_level(risk_signals: list[RiskSignal]) -> str:
        if not risk_signals:
            return "low"

        critical_count = sum(1 for s in risk_signals if s.severity.upper() == "CRITICAL")
        high_count = sum(1 for s in risk_signals if s.severity.upper() == "HIGH")
        medium_count = sum(1 for s in risk_signals if s.severity.upper() == "MEDIUM")

        if critical_count > 0:
            return "critical"
        elif high_count > 0:
            return "high"
        elif medium_count > 0:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str | None, str | None]:
        patterns = [
            r"github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/|$)",
            r"github\.com/([^/]+)/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2).replace(".git", "")

        return None, None

    @staticmethod
    def _create_unknown_report(source_url: str) -> SecurityReport:
        return SecurityReport(
            resource_type="skill",
            resource_id=source_url,
            risk_level="unknown",
            risk_signals=[],
            details={"note": "Unknown source type"},
        )

    # ------------------------------------------------------------------
    # Skillspector (Jenkins-based scanner)
    # ------------------------------------------------------------------

    @property
    def has_skillspector(self) -> bool:
        return self._skillspector_client is not None and self._skillspector_client.enabled

    async def trigger_skillspector(
        self,
        source_url: str,
        version: str | None = None,
        skill_path: str = "",
    ) -> int | None:
        """Trigger a Jenkins scan **without waiting** for the result.

        Returns the build number so the caller can poll / collect later.
        """
        if not self.has_skillspector:
            return None
        ref = version if version else "main"
        try:
            return await asyncio.to_thread(
                self._skillspector_client.trigger_scan,
                git_url=source_url,
                ref=ref,
                skill_path=skill_path,
            )
        except Exception as exc:
            logger.error("Skillspector trigger failed: %s", exc)
            return None

    async def detect_skillspector(
        self,
        source_url: str,
        version: str | None = None,
        skill_path: str = "",
    ) -> SecurityReport:
        """Run a Jenkins-triggered Skillspector scan.

        Because the Jenkins client uses synchronous HTTP + polling we offload
        it to a thread to avoid blocking the async event loop.
        """
        if not self.has_skillspector:
            return SecurityReport(
                resource_type="skill",
                resource_id=source_url,
                risk_level="unknown",
                risk_signals=[],
                details={"note": "Skillspector not configured"},
            )

        ref = version if version else "main"

        try:
            report = await asyncio.to_thread(
                self._skillspector_client.run_scan,
                git_url=source_url,
                ref=ref,
                skill_path=skill_path,
            )
        except Exception as exc:
            logger.error("Skillspector scan failed: %s", exc)
            return SecurityReport(
                resource_type="skill",
                resource_id=source_url,
                risk_level="unknown",
                risk_signals=[],
                details={"error": str(exc), "source": "skillspector"},
            )

        if "error" in report:
            logger.warning("Skillspector returned error: %s", report["error"])
            return SecurityReport(
                resource_type="skill",
                resource_id=source_url,
                risk_level="unknown",
                risk_signals=[],
                details={"error": report["error"], "source": "skillspector"},
            )

        risk_signals = SkillspectorClient.report_to_risk_signals(report)
        severity = report.get("risk_assessment", {}).get("severity", "UNKNOWN").upper()
        score = report.get("risk_assessment", {}).get("score")

        risk_level_map = {"LOW": "low", "MEDIUM": "medium", "HIGH": "high", "CRITICAL": "critical"}
        risk_level = risk_level_map.get(severity, "unknown")

        return SecurityReport(
            resource_type="skill",
            resource_id=source_url,
            risk_level=risk_level,
            risk_signals=risk_signals,
            details={
                "source": "skillspector",
                "skillspector_version": report.get("metadata", {}).get("skillspector_version"),
                "skillspector_score": score,
                "recommendation": report.get("risk_assessment", {}).get("recommendation"),
                "skillspector_report": report,
            },
        )


# ═══════════════════════════════════════════════════════════════════════════
# Factory — start the background collector from app lifecycle
# ═══════════════════════════════════════════════════════════════════════════


async def start_skillspector_collector() -> SkillspectorCollector | None:
    """Create and start the Skillspector background collector.

    Returns the collector instance for later shutdown, or *None* if credentials
    are not configured.
    """
    from src.core.database import AsyncSessionLocal

    client = SkillspectorClient(
        jenkins_url=settings.security.skillspector_jenkins_url,
        user=settings.security.skillspector_jenkins_user,
        token=settings.security.skillspector_jenkins_token,
    )
    if not client.enabled:
        logger.warning("Skillspector enabled but no credentials — collector skipped")
        return None

    collector = SkillspectorCollector(
        client=client,
        session_factory=AsyncSessionLocal,
        poll_interval=30,
    )
    await collector.start()
    logger.info("SkillspectorCollector background task started")
    return collector
