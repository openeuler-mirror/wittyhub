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


class AIConfig(BaseSettings):
    embedding_model: str = "bge-base-zh-v1.5"
    embedding_host: str = "http://localhost:8081"
    embedding_dimension: int = 768
    enable_semantic_search: bool = True


class Settings(BaseSettings):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ai: AIConfig = Field(default_factory=AIConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        return cls(
            database=DatabaseConfig(**data.get("database", {})),
            storage=StorageConfig(**data.get("storage", {})),
            security=SecurityConfig(**data.get("security", {})),
            app=AppConfig(**data.get("app", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            ai=AIConfig(**data.get("ai", {})),
        )


@lru_cache
def get_settings() -> Settings:
    config_path = os.environ.get("SKILLHUB_CONFIG", "config.yaml")
    return Settings.from_yaml(config_path)
