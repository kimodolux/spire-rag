"""Unit tests for the typed settings object. No database required."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from spire_rag.core.config import Settings

SECRET_ENV_VARS = ("DATABASE_URL", "ANTHROPIC_API_KEY", "SESSION_SECRET")


@pytest.fixture
def clear_secret_env(monkeypatch):
    for name in SECRET_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_missing_required_env_var_raises_readable_error(clear_secret_env):
    # _env_file=None so a developer's local .env can't satisfy the secrets and
    # mask the failure we're asserting.
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    message = str(exc_info.value)
    # Every missing secret is named, so the error tells you exactly what to set.
    for name in ("database_url", "anthropic_api_key", "session_secret"):
        assert name in message


def test_secrets_from_env_and_embedding_from_yaml(clear_secret_env, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost/db")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("SESSION_SECRET", "shhh")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://u:p@localhost/db"
    # Pipeline block comes from config/config.yaml.
    assert settings.embedding.model == "Alibaba-NLP/gte-large-en-v1.5"
    assert settings.embedding.dims == 1024
