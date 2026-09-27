from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sistema de minería de procesos con alertas predictivas"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"

    postgres_db: str = "gyv_process_mining"
    postgres_user: str = "gyv_user"
    postgres_password: str = "gyv_password"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None
    deviation_inactivity_hours: int = Field(default=72, gt=0)
    ml_snapshot_interval_hours: int = Field(default=12, gt=0)
    ml_model_dir: Path = Path("ml/models")
    alert_risk_threshold: float = Field(default=0.70, gt=0, le=1)
    alert_batch_limit: int = Field(default=100, gt=0, le=500)
    analyst_enabled: bool = True
    analyst_llm_provider: Literal["ollama"] = "ollama"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = Field(default="qwen2.5:7b", min_length=1, max_length=200)
    analyst_max_tool_rounds: int = Field(default=6, ge=1, le=12)
    analyst_max_history_messages: int = Field(default=10, ge=0, le=20)
    analyst_timeout_seconds: int = Field(default=60, ge=5, le=300)
    analyst_max_tool_result_items: int = Field(default=50, ge=1, le=100)
    analyst_temperature: float = Field(default=0.1, ge=0, le=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def empty_database_url_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL debe usar http:// o https://")
        return normalized

    @field_validator("ollama_model")
    @classmethod
    def normalize_ollama_model(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("OLLAMA_MODEL no puede estar vacío")
        return normalized

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
