from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class SkillBase(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    version: str | None = Field(None, max_length=50)
    commit_id: str | None = Field(None, max_length=40)
    author: str | None = Field(None, max_length=255)
    source: str = Field(..., max_length=50)
    source_url: str = Field(..., min_length=1, max_length=2048)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = Field(None, max_length=100)
    platform: str | None = Field(None, max_length=100)
    content: str | None = Field(None, max_length=2_000_000)
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("extra_metadata", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {"github", "gitcode", "gitlab", "gitee", "clawhub", "local"}
        if v not in allowed:
            raise ValueError(f"source must be one of {allowed}")
        return v


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    version: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    extra_metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("extra_metadata", "metadata"),
        serialization_alias="extra_metadata",
    )


class SkillResponse(SkillBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    repo_url: str | None = None
    content: str | None = None
    category_label: str | None = None
    risk_score: int | None = None
    download_count: int = 0
    period_downloads: int | None = None
    rating: str | None = None
    created_at: datetime
    updated_at: datetime
    last_indexed_at: datetime | None = None


class SkillListResponse(BaseModel):
    skills: list[SkillResponse]
    total: int
    skip: int
    limit: int


class SkillSearchResult(BaseModel):
    skill: SkillResponse
    score: float | None = None


class RiskSignalSchema(BaseModel):
    id: str
    name: str
    description: str
    severity: str
    data: dict[str, Any] = Field(default_factory=dict)


class SecurityAuditResponse(BaseModel):
    id: str
    resource_type: str
    resource_id: str
    version: str | None = None
    commit_id: str | None = None
    audit_type: str
    risk_level: str
    risk_score: int | None = None
    risk_signals: list[RiskSignalSchema]
    details: dict[str, Any]
    audited_at: datetime


class AuditByUrlRequest(BaseModel):
    """One-off security audit for a skill repository URL or a SKILL.md URL.

    Either ``repo_url`` (scan the whole repository) or ``skill_url`` (a
    ``<host>/<owner>/<repo>/blob/<ref>/<path>/SKILL.md`` link) must be provided.
    """

    repo_url: str | None = Field(
        None, max_length=2048, description="Git repository URL to scan (whole repo)"
    )
    branch: str | None = Field(
        None, max_length=255, description="Git ref/branch to scan (default: main)"
    )
    skill_url: str | None = Field(
        None, max_length=2048, description="SKILL.md blob URL to scan (single skill)"
    )
    scanners: str | None = Field(
        None, description="Comma-separated scanner list (default: skillspector)"
    )
    async_mode: bool = Field(
        False, description="Trigger scan without waiting for the result"
    )


class AuditByUrlResponse(BaseModel):
    """Result of a one-off audit-by-URL scan (not persisted)."""

    git_url: str
    ref: str
    skill_path: str
    risk_level: str
    risk_score: int | None = None
    risk_signals: list[RiskSignalSchema] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class AuditByUrlResultResponse(BaseModel):
    """Polling result of an async audit-by-URL scan (not persisted).

    ``status`` is one of ``pending`` / ``done`` / ``error``.  Only when
    ``status == "done"`` are ``risk_level`` / ``risk_score`` /
    ``risk_signals`` / ``details`` populated.
    """

    status: str
    build_number: int
    jenkins_status: str | None = None
    risk_level: str | None = None
    risk_score: int | None = None
    risk_signals: list[RiskSignalSchema] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class SkillVersionsResponse(BaseModel):
    source_url: str
    skill_id: str
    versions: list[SkillResponse]


SkillVersionResponse = SkillVersionsResponse
