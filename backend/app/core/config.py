from functools import lru_cache
from pathlib import Path

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
