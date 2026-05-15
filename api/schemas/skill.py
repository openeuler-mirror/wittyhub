from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SkillBase(BaseModel):
    skill_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    version: str | None = Field(None, max_length=50)
    author: str | None = Field(None, max_length=255)
    source: str = Field(..., max_length=50)
    source_url: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    platform: str | None = Field(None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {"github", "gitcode", "gitlab", "local"}
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
    metadata: dict[str, Any] | None = None


class SkillResponse(SkillBase):
    id: str
    security_score: int | None = None
    download_count: int = 0
    rating: float | None = None
    created_at: datetime
    updated_at: datetime
    last_indexed_at: datetime | None = None

    class Config:
        from_attributes = True


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
    audit_type: str
    risk_level: str
    risk_signals: list[RiskSignalSchema]
    details: dict[str, Any]
    audited_at: datetime

    class Config:
        from_attributes = True


class DownloadResponse(BaseModel):
    download_url: str
    file_path: str | None = None
    security_audit: SecurityAuditResponse | None = None


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
