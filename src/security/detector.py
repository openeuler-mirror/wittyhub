import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.core.config import get_settings

settings = get_settings()


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


class SecurityDetector:
    SOCKET_API_URL = "https://api.socket.dev/v0"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.security.socket_api_key
        self.enable_audit = settings.security.enable_audit

    async def detect(self, source: str, source_url: str, metadata: dict[str, Any]) -> SecurityReport:
        if source == "github":
            return await self._detect_github(source_url, metadata)
        elif source == "gitcode":
            return await self._detect_gitcode(source_url, metadata)
        else:
            return self._create_unknown_report(source_url)

    async def _detect_github(self, source_url: str, metadata: dict[str, Any]) -> SecurityReport:
        risk_signals = []

        if not self.api_key:
            return SecurityReport(
                resource_type="skill",
                resource_id=source_url,
                risk_level="unknown",
                risk_signals=[],
                details={"note": "No Socket.dev API key configured"},
            )

        try:
            owner, repo = self._parse_github_url(source_url)
            if owner and repo:
                socket_result = await self._check_socket_npm(owner, repo)
                if socket_result:
                    risk_signals.extend(socket_result)
        except Exception:
            pass

        risk_level = self._calculate_risk_level(risk_signals)

        return SecurityReport(
            resource_type="skill",
            resource_id=source_url,
            risk_level=risk_level,
            risk_signals=risk_signals,
            details={"source": "github"},
        )

    async def _detect_gitcode(self, source_url: str, metadata: dict[str, Any]) -> SecurityReport:
        return SecurityReport(
            resource_type="skill",
            resource_id=source_url,
            risk_level="unknown",
            risk_signals=[],
            details={"note": "GitCode detection not yet implemented"},
        )

    async def _check_socket_npm(self, owner: str, repo: str) -> list[RiskSignal]:
        risk_signals = []

        headers = {"x-api-key": self.api_key} if self.api_key else {}
        url = f"{self.SOCKET_API_URL}/github/{owner}/{repo}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    risk_signals.extend(self._parse_socket_response(data))
            except Exception:
                pass

        return risk_signals

    def _parse_socket_response(self, data: dict[str, Any]) -> list[RiskSignal]:
        risk_signals = []

        if not isinstance(data, dict):
            return risk_signals

        issues = data.get("issues", [])
        for issue in issues:
            if not isinstance(issue, dict):
                continue

            severity = issue.get("severity", "unknown")
            risk_signals.append(
                RiskSignal(
                    id=issue.get("id", "unknown"),
                    name=issue.get("title", "Unknown Issue"),
                    description=issue.get("description", ""),
                    severity=severity,
                    data=issue,
                )
            )

        return risk_signals

    def _calculate_risk_level(self, risk_signals: list[RiskSignal]) -> str:
        if not risk_signals:
            return "low"

        critical_count = sum(1 for s in risk_signals if s.severity == "Critical")
        high_count = sum(1 for s in risk_signals if s.severity == "High")
        medium_count = sum(1 for s in risk_signals if s.severity == "Medium")

        if critical_count > 0:
            return "critical"
        elif high_count > 0:
            return "high"
        elif medium_count > 0:
            return "medium"
        else:
            return "low"

    def _parse_github_url(self, url: str) -> tuple[str | None, str | None]:
        patterns = [
            r"github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/|$)",
            r"github\.com/([^/]+)/([^/]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2).replace(".git", "")

        return None, None

    def _create_unknown_report(self, source_url: str) -> SecurityReport:
        return SecurityReport(
            resource_type="skill",
            resource_id=source_url,
            risk_level="unknown",
            risk_signals=[],
            details={"note": "Unknown source type"},
        )


class StaticSecurityAnalyzer:
    SENSITIVE_PATTERNS = [
        (r"api[_-]?key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]", "hardcoded_api_key", "High"),
        (r"password\s*=\s*['\"][^'\"]{8,}['\"]", "hardcoded_password", "High"),
        (r"secret\s*=\s*['\"][a-zA-Z0-9]{16,}['\"]", "hardcoded_secret", "High"),
        (r"token\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]", "hardcoded_token", "High"),
        (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key", "Critical"),
        (r"aws[_-]?access[_-]?key[_-]?id\s*=\s*['\"][A-Z0-9]{16,}['\"]", "aws_access_key", "Critical"),
        (r"os\.environ\[[\'\"](?:API_KEY|SECRET|PASSWORD)", "env_secret_access", "High"),
    ]

    NETWORK_PATTERNS = [
        (r"https?://(?:www\.)?sentry\.io", "sentry_tracking", "Low"),
        (r"https?://(?:www\.)?loggly\.com", "loggly_tracking", "Low"),
        (r"https?://(?:www\.)?datadog\.com", "datadog_tracking", "Low"),
    ]

    def analyze_content(self, content: str) -> list[RiskSignal]:
        risk_signals = []

        for pattern, name, severity in self.SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                risk_signals.append(
                    RiskSignal(
                        id=name,
                        name=self._format_name(name),
                        description=f"Potential {self._format_name(name).lower()} detected",
                        severity=severity,
                    )
                )

        for pattern, name, severity in self.NETWORK_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                risk_signals.append(
                    RiskSignal(
                        id=name,
                        name=self._format_name(name),
                        description=f"External service call to {self._format_name(name).lower()}",
                        severity=severity,
                    )
                )

        return risk_signals

    def _format_name(self, name: str) -> str:
        return name.replace("_", " ").replace("-", " ").title()
