import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.repository import SecurityAuditRepository, SkillRepository
from src.security.detector import SecurityDetector, RiskSignal
class SecurityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.skill_repo = SkillRepository(session)
        self.audit_repo = SecurityAuditRepository(session)
        self.detector = SecurityDetector()

    async def audit_skill(
        self,
        skill_id: str,
        source: str,
        source_url: str,
        metadata: dict[str, Any],
        scanners: list[str] | None = None,
        async_mode: bool = False,
    ) -> dict[str, Any]:
        """Run security audit for a skill.

        Parameters
        ----------
        scanners:
            Which scanners to run.  Supported: ``skillspector``.
            When *None* the default set is used.
        async_mode:
            When *True* and skillspector is enabled, only **trigger** the
            Jenkins scan without waiting for the result.  The build number is
            recorded in ``details.skillspector_build_number`` so a background
            worker can collect results later.  All other scanners still run
            synchronously.
        """
        skill = await self.skill_repo.get_by_skill_id(skill_id)
        if not skill:
            return {"error": "Skill not found"}

        if scanners is None:
            scanners = []
            if self.detector.has_skillspector:
                scanners.append("skillspector")

        all_signals: list[RiskSignal] = []
        merged_details: dict[str, Any] = {}
        scanner_names: list[str] = []
        skillspector_score: int | None = None
        sp_report: Any = None
        # --- Skillspector ---
        if "skillspector" in scanners:
            version = metadata.get("version") if isinstance(metadata, dict) else None
            skill_path = metadata.get("skill_path", "") if isinstance(metadata, dict) else ""
            if async_mode:
                # Fire-and-forget: trigger only, don't wait
                build_number = await self.detector.trigger_skillspector(
                    source_url, version=version, skill_path=skill_path,
                )
                merged_details["skillspector_build_number"] = build_number
                merged_details["skillspector_async"] = True
                scanner_names.append("skillspector")
            else:
                # Full synchronous scan
                sp_report = await self.detector.detect_skillspector(
                    source_url, version=version, skill_path=skill_path,
                )
                # Only count this scanner when it actually produced results
                if sp_report.risk_level != "unknown" or sp_report.risk_signals:
                    all_signals.extend(sp_report.risk_signals)
                    merged_details.update(sp_report.details)
                    scanner_names.append("skillspector")
                    if sp_report.details.get("skillspector_score") is not None:
                        skillspector_score = sp_report.details["skillspector_score"]

        # --- Calculate risk level & score ---
        if async_mode:
            # Scan triggered but result not yet collected; unknown until
            # SkillspectorCollector writes back the real values.
            risk_level = "unknown"
            risk_score = None
        elif scanner_names:
            # Prefer Jenkins raw risk_level when available
            if sp_report is not None and sp_report.risk_level != "unknown":
                risk_level = sp_report.risk_level
            else:
                risk_level = self.detector._calculate_risk_level(all_signals)
            risk_score = (
                skillspector_score
                if skillspector_score is not None
                else self._calculate_risk_score(risk_level)
            )
        else:
            risk_level = "unknown"
            risk_score = None

        merged_details["scanners"] = scanner_names

        audit_data = {
            "resource_type": "skill",
            "resource_id": skill.id,
            "version": skill.version,
            "commit_id": skill.commit_id,
            "audit_type": "+".join(scanner_names) if scanner_names else "none",
            "risk_level": risk_level,
            "risk_signals": [signal.__dict__ for signal in all_signals],
            "details": merged_details,
        }

        await self.audit_repo.create(audit_data)
        await self.skill_repo.update(skill_id, {"risk_score": risk_score})

        await self.session.commit()

        return {
            "risk_level": risk_level,
            "risk_signals": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "severity": s.severity,
                }
                for s in all_signals
            ],
            "risk_score": risk_score,
            "scanners": scanner_names,
        }

    async def audit_external(
        self,
        git_url: str,
        ref: str = "main",
        skill_path: str = "",
        scanners: list[str] | None = None,
        async_mode: bool = False,
    ) -> dict[str, Any]:
        """Run a one-off security audit for a git URL that is NOT registered.

        Used by the openEuler-skills PR gate to audit proposed content
        (a skill repository or a single SKILL.md) before it is merged and
        registered.  Nothing is persisted to the database.

        Returns a dict with ``git_url``, ``ref``, ``skill_path``,
        ``risk_level``, ``risk_score``, ``risk_signals`` and ``details``.
        """
        if scanners is None:
            scanners = []
            if self.detector.has_skillspector:
                scanners.append("skillspector")

        all_signals: list[RiskSignal] = []
        merged_details: dict[str, Any] = {}
        scanner_names: list[str] = []
        skillspector_score: int | None = None
        sp_report: Any = None

        # --- Skillspector ---
        if "skillspector" in scanners:
            if async_mode:
                build_number = await self.detector.trigger_skillspector(
                    git_url, version=ref, skill_path=skill_path,
                )
                merged_details["skillspector_build_number"] = build_number
                merged_details["skillspector_async"] = True
                scanner_names.append("skillspector")
            else:
                sp_report = await self.detector.detect_skillspector(
                    git_url, version=ref, skill_path=skill_path,
                )
                if sp_report.risk_level != "unknown" or sp_report.risk_signals:
                    all_signals.extend(sp_report.risk_signals)
                    merged_details.update(sp_report.details)
                    scanner_names.append("skillspector")
                    if sp_report.details.get("skillspector_score") is not None:
                        skillspector_score = sp_report.details["skillspector_score"]

        # --- Calculate risk level & score ---
        if async_mode:
            risk_level = "unknown"
            risk_score = None
        elif scanner_names:
            if sp_report is not None and sp_report.risk_level != "unknown":
                risk_level = sp_report.risk_level
            else:
                risk_level = self.detector._calculate_risk_level(all_signals)
            risk_score = (
                skillspector_score
                if skillspector_score is not None
                else self._calculate_risk_score(risk_level)
            )
        else:
            risk_level = "unknown"
            risk_score = None

        merged_details["scanners"] = scanner_names

        return {
            "git_url": git_url,
            "ref": ref,
            "skill_path": skill_path,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_signals": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "severity": s.severity,
                    "data": s.data,
                }
                for s in all_signals
            ],
            "details": merged_details,
        }


    def _calculate_risk_score(self, risk_level: str) -> int | None:
        """Map risk_level to SkillSpector-compatible risk score (0-100, higher = riskier)."""
        if risk_level == "unknown":
            return None
        score_map = {
            "critical": 90,
            "high": 65,
            "medium": 35,
            "low": 10,
        }
        return score_map.get(risk_level)

    async def get_external_result(self, build_number: int) -> dict[str, Any]:
        """Query the result of a previously-triggered one-off audit-by-URL scan.

        The PR gate triggers a scan with ``async_mode=True`` and polls this
        until the Jenkins build finishes.  Nothing is persisted.
        """
        return await self.detector.get_external_result(build_number)

    async def get_external_report_md(self, build_number: int) -> str | None:
        """Fetch the Markdown report (report.md) for a one-off audit-by-URL scan.

        Served to PR reviewers via the ``/audit-by-url/report`` download link.
        """
        return await self.detector.fetch_external_report_md(build_number)
