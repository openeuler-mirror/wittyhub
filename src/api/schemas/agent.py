from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AgentBase(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    version: str | None = Field(None, max_length=50)
    commit_id: str | None = Field(None, max_length=40)
    author: str | None = Field(None, max_length=255)
    source: str = Field(..., max_length=50)
    source_url: str = Field(..., min_length=1)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    supported_platforms: list[str] | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        allowed = {"github", "gitcode", "gitlab", "gitee", "local"}
        if v not in allowed:
            raise ValueError(f"source must be one of {allowed}")
        return v


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    version: str | None = Field(None, max_length=50)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None


class ParsedConfigPromptIdentity(BaseModel):
    role: str | None = None
    emoji: str | None = None
    vibe: str | None = None


class ParsedConfigPrompt(BaseModel):
    system: str | None = None
    identity: ParsedConfigPromptIdentity | None = None
    workflow_file: str | None = None


class ParsedConfigTools(BaseModel):
    allowed: list[str] | None = None
    permission: dict[str, Any] | None = None


class AgentSkillRef(BaseModel):
    name: str
    source: str | None = None
    inline: str | None = None
    installed: str | None = None
    when: list[str] | None = None


class SubagentPrompt(BaseModel):
    system: str | None = None
    identity: ParsedConfigPromptIdentity | None = None


class SubagentConfig(BaseModel):
    name: str
    prompt: SubagentPrompt | None = None
    tools: ParsedConfigTools | None = None
    skills: list[AgentSkillRef] | None = None


class ParsedConfig(BaseModel):
    prompt: ParsedConfigPrompt | None = None
    tools: ParsedConfigTools | None = None
    skills: list[AgentSkillRef] | None = None
    subagents: list[SubagentConfig] | None = None


class AgentResponse(AgentBase):
    id: str
    logo_url: str | None = None
    homepage_url: str | None = None
    license: str | None = None
    readme_content: str | None = None
    agent_yaml_content: str | None = None
    parsed_config: dict[str, Any] = Field(default_factory=dict)
    verified: bool = False
    star_count: int = 0
    contributor_count: int = 0
    security_score: int | None = None
    download_count: int = 0
    rating: str | None = None
    latest_commit_id: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
    skip: int
    limit: int


class AgentVersionResponse(BaseModel):
    version: str
    commit_id: str | None = None
    author: str | None = None
    message: str | None = None
    released_at: datetime | None = None
    download_count: int = 0

    class Config:
        from_attributes = True


class AgentVersionsResponse(BaseModel):
    agent_id: str
    versions: list[AgentVersionResponse]
