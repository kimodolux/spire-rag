"""Integration tests for the embedding_config guard.

These need the Postgres from docker-compose with migrations applied. Set
DATABASE_URL to the libpq DSN (e.g. postgresql://spire:spire@localhost:5432/spire_rag);
the tests skip cleanly if it is unset or the database is unreachable.
"""
from __future__ import annotations

import os

import psycopg
import pytest

from spire_rag.core.config import EmbeddingConfig
from spire_rag.core.embedding_config import (
    EmbeddingConfigMismatch,
    check_embedding_config,
)

CONFIGURED = EmbeddingConfig(model="Alibaba-NLP/gte-large-en-v1.5", version="v1", dims=1024)


@pytest.fixture
def db_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    try:
        conn = psycopg.connect(url)
    except psycopg.Error as exc:
        pytest.skip(f"database unreachable: {exc}")

    # Start each test from an empty singleton table, and leave it empty after.
    def _clear():
        with conn.cursor() as cur:
            cur.execute("DELETE FROM embedding_config")
        conn.commit()

    _clear()
    try:
        yield conn
    finally:
        _clear()
        conn.close()


def test_empty_table_is_seeded(db_conn):
    check_embedding_config(db_conn, CONFIGURED)

    with db_conn.cursor() as cur:
        cur.execute("SELECT model, version, dims FROM embedding_config")
        assert cur.fetchone() == (CONFIGURED.model, CONFIGURED.version, CONFIGURED.dims)


def test_mismatched_dims_fails_startup(db_conn):
    # Seed the row as if the index were built at 768 dims.
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO embedding_config (id, model, version, dims) VALUES (1, %s, %s, %s)",
            (CONFIGURED.model, CONFIGURED.version, 768),
        )
    db_conn.commit()

    # Configured at 1024 -> must refuse to start.
    with pytest.raises(EmbeddingConfigMismatch) as exc_info:
        check_embedding_config(db_conn, CONFIGURED)

    message = str(exc_info.value)
    assert "dims" in message
    assert "768" in message and "1024" in message


def test_matching_row_passes(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO embedding_config (id, model, version, dims) VALUES (1, %s, %s, %s)",
            (CONFIGURED.model, CONFIGURED.version, CONFIGURED.dims),
        )
    db_conn.commit()

    # No exception.
    check_embedding_config(db_conn, CONFIGURED)
