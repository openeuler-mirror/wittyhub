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
    source_url: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    platform: str | None = Field(None, max_length=100)
    content: str | None = None
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("extra_metadata", "metadata"),
        serialization_alias="extra_metadata",
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
    content: str | None = None
    security_score: int | None = None
    download_count: int = 0
    rating: float | None = None
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
    risk_signals: list[RiskSignalSchema]
    details: dict[str, Any]
    audited_at: datetime


class DownloadResponse(BaseModel):
    download_url: str
    file_path: str | None = None
    security_audit: SecurityAuditResponse | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


class SkillVersionsResponse(BaseModel):
    source_url: str
    skill_id: str
    versions: list[SkillResponse]


SkillVersionResponse = SkillVersionsResponse
