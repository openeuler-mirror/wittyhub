import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    user: str = "wittyhub"
    password: str = "wittyhub_secret"
    dbname: str = "wittyhub"
    sslmode: str = "disable"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class StorageConfig(BaseSettings):
    type: str = "local"
    local_path: str = "/opt/wittyhub/skill-data"
    github_token: str = ""


class ModelConfig(BaseSettings):
    name: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    api_key: str = ""
    timeout: float = 30


class CrawlerConfig(BaseSettings):
    github_token: str = ""
    github_username: str = "git"
    max_tags_per_repo: int = 3


class SkillRepoEntry(BaseSettings):
    url: str
    branch: str | None = None


class SecurityConfig(BaseSettings):
    # Skillspector (Jenkins-based scanner)
    enable_audit: bool = False
    skillspector_jenkins_url: str = ""
    skillspector_jenkins_user: str = ""  # env: SKILLSPECTOR_JENKINS_USER
    skillspector_jenkins_token: str = ""  # env: SKILLSPECTOR_JENKINS_TOKEN


class AppConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    format: str = "json"


class AIConfig(BaseSettings):
    embedding_model: str = "bge-base-zh-v1.5"
    embedding_host: str = "http://localhost:8081"
    embedding_dimension: int = 768
    enable_semantic_search: bool = True


class Settings(BaseSettings):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    openeuler_repos: list[SkillRepoEntry] = Field(default_factory=list)
    personal_repos: list[SkillRepoEntry] = Field(default_factory=list)
    enterprise_repos: list[SkillRepoEntry] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        path = Path(path)
        data: dict[str, Any] = {}
        if path.exists():
            with open(path) as f:
                data = yaml.safe_load(f) or {}
        _apply_env_overrides(data)

        return cls(
            database=DatabaseConfig(**data.get("database", {})),
            storage=StorageConfig(**data.get("storage", {})),
            model=ModelConfig(**data.get("model", {})),
            crawler=CrawlerConfig(**data.get("crawler", {})),
            security=SecurityConfig(**data.get("security", {})),
            app=AppConfig(**data.get("app", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            ai=AIConfig(**data.get("ai", {})),
            openeuler_repos=data.get("openeuler_repos", []) or [],
            personal_repos=data.get("personal_repos", []) or [],
            enterprise_repos=data.get("enterprise_repos", []) or [],
        )


def _apply_env_overrides(data: dict[str, Any]) -> None:
    for key, value in os.environ.items():
        if "__" not in key:
            continue
        section, field = key.split("__", 1)
        section = section.strip().lower()
        field = field.strip().lower()
        if not section or not field:
            continue
        section_data = data.setdefault(section, {})
        if isinstance(section_data, dict):
            section_data[field] = _parse_env_value(value)


def _parse_env_value(value: str) -> Any:
    if value == "":
        return ""
    try:
        return yaml.safe_load(value)
    except yaml.YAMLError:
        return value


@lru_cache
def get_settings() -> Settings:
    default_config_path = Path(__file__).resolve().parents[2] / "config.yaml"
    config_path = os.environ.get("WITTYHUB_CONFIG", str(default_config_path))
    return Settings.from_yaml(config_path)
