from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

POSTGRES_DRIVER_NAMES = frozenset(
    {
        "postgresql",
        "postgresql+psycopg",
        "postgresql+asyncpg",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHATRPG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://chatrpg:chatrpg@localhost:5432/chatrpg"
    )
    artifact_root: Path = Field(default=Path("artifacts"))

    pi_base_url: str | None = None
    pi_api_key: str | None = None
    pi_model: str = "pi-latest"
    semantic_match_provider: str = "pi"

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        driver_name = make_url(value).drivername
        if driver_name not in POSTGRES_DRIVER_NAMES:
            raise ValueError(
                "CHATRPG_DATABASE_URL must target Postgres. "
                "Non-Postgres dialects are intentionally unsupported."
            )
        return value
