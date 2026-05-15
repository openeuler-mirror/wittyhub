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
    user: str = "skillhub"
    password: str = "skillhub_secret"
    dbname: str = "skillhub"
    sslmode: str = "disable"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"


class MeilisearchConfig(BaseSettings):
    host: str = "http://localhost:7700"
    api_key: str = ""


class StorageConfig(BaseSettings):
    type: str = "local"
    local_path: str = "./data/skills"
    github_token: str = ""


class SecurityConfig(BaseSettings):
    socket_api_key: str = ""
    enable_audit: bool = True


class AppConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    format: str = "json"


class Settings(BaseSettings):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    meilisearch: MeilisearchConfig = Field(default_factory=MeilisearchConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        return cls(
            database=DatabaseConfig(**data.get("database", {})),
            meilisearch=MeilisearchConfig(**data.get("meilisearch", {})),
            storage=StorageConfig(**data.get("storage", {})),
            security=SecurityConfig(**data.get("security", {})),
            app=AppConfig(**data.get("app", {})),
            logging=LoggingConfig(**data.get("logging", {})),
        )


@lru_cache
def get_settings() -> Settings:
    config_path = os.environ.get("SKILLHUB_CONFIG", "config.yaml")
    return Settings.from_yaml(config_path)