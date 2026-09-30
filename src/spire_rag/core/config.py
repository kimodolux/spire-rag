"""One typed settings object for the whole project.

Secrets (DB URL, API keys, session secret) come from environment variables.
Pipeline settings (the embedding contract, and per-book overrides later) come
from ``config/config.yaml``. Both are merged into a single validated ``Settings``
object; environment variables win over YAML on any overlap.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

# Repo root: this file is src/spire_rag/core/config.py -> parents[3] is the root.
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_YAML = REPO_ROOT / "config" / "config.yaml"


class EmbeddingConfig(BaseModel):
    """The embedding contract enforced against the embedding_config table.

    ``dims`` must match the vector(N) columns created by the migration.
    """

    model: str
    version: str
    dims: int = Field(gt=0)


class Settings(BaseSettings):
    """Project-wide configuration, validated at load time.

    Missing a required secret raises a pydantic ``ValidationError`` naming the
    field, so start-up fails with a readable message rather than a later
    ``KeyError``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        yaml_file=CONFIG_YAML,
    )

    # Secrets, from the environment.
    database_url: str
    anthropic_api_key: str
    session_secret: str

    # Pipeline settings, from config/config.yaml.
    embedding: EmbeddingConfig

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority order: explicit init args, environment,
        # .env file, then YAML for the pipeline block.
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


@lru_cache
def get_settings() -> Settings:
    """Return the cached, validated project settings."""
    return Settings()
