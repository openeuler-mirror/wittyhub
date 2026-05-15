import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.repository import SecurityAuditRepository, SkillRepository
from security.detector import SecurityDetector, StaticSecurityAnalyzer, RiskSignal


class SecurityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.skill_repo = SkillRepository(session)
        self.audit_repo = SecurityAuditRepository(session)
        self.detector = SecurityDetector()
        self.static_analyzer = StaticSecurityAnalyzer()

    async def audit_skill(
        self, skill_id: str, source: str, source_url: str, metadata: dict[str, Any]
    ) -> dict[str, Any]:
        skill = await self.skill_repo.get_by_skill_id(skill_id)
        if not skill:
            return {"error": "Skill not found"}

        report = await self.detector.detect(source, source_url, metadata)

        audit_data = {
            "resource_type": "skill",
            "resource_id": skill.id,
            "audit_type": "socket_detection",
            "risk_level": report.risk_level,
            "risk_signals": [signal.__dict__ for signal in report.risk_signals],
            "details": report.details,
        }

        await self.audit_repo.create(audit_data)

        security_score = self._calculate_security_score(report.risk_level)
        await self.skill_repo.update(skill_id, {"security_score": security_score})

        return {
            "risk_level": report.risk_level,
            "risk_signals": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "severity": s.severity,
                }
                for s in report.risk_signals
            ],
            "security_score": security_score,
        }

    async def audit_content(self, content: str) -> list[dict[str, Any]]:
        risk_signals = self.static_analyzer.analyze_content(content)

        return [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "severity": s.severity,
            }
            for s in risk_signals
        ]

    def _calculate_security_score(self, risk_level: str) -> int:
        score_map = {
            "critical": 0,
            "high": 25,
            "medium": 50,
            "low": 75,
            "unknown": 100,
        }
        return score_map.get(risk_level, 100)
