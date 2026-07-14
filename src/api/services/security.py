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
                all_signals.extend(sp_report.risk_signals)
                merged_details.update(sp_report.details)
                scanner_names.append("skillspector")
                if sp_report.details.get("skillspector_score") is not None:
                    skillspector_score = sp_report.details["skillspector_score"]

        # --- Calculate risk level & score ---
        risk_level = self.detector._calculate_risk_level(all_signals)
        security_score = (
            skillspector_score
            if skillspector_score is not None
            else self._calculate_security_score(risk_level)
        )

        merged_details["scanners"] = scanner_names

        audit_data = {
            "resource_type": "skill",
            "resource_id": skill.id,
            "audit_type": "+".join(scanner_names) if scanner_names else "none",
            "risk_level": risk_level,
            "risk_signals": [signal.__dict__ for signal in all_signals],
            "details": merged_details,
        }

        await self.audit_repo.create(audit_data)
        await self.skill_repo.update(skill_id, {"security_score": security_score})

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
            "security_score": security_score,
            "scanners": scanner_names,
        }


    def _calculate_security_score(self, risk_level: str) -> int:
        score_map = {
            "critical": 0,
            "high": 25,
            "medium": 50,
            "low": 75,
            "unknown": 100,
        }
        return score_map.get(risk_level, 100)
