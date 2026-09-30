"""Start-up guard that stops the API and ingest running on a mismatched model."""
from __future__ import annotations

import sys

import psycopg

from spire_rag.core.config import EmbeddingConfig, Settings, get_settings


class EmbeddingConfigMismatch(RuntimeError):
    """Raised when the configured embedding contract differs from the stored row."""


def seed_embedding_config(conn: psycopg.Connection, cfg: EmbeddingConfig) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO embedding_config (id, model, version, dims) "
            "VALUES (1, %s, %s, %s)",
            (cfg.model, cfg.version, cfg.dims),
        )
    conn.commit()


def check_embedding_config(conn: psycopg.Connection, cfg: EmbeddingConfig) -> None:
    """Compare ``cfg`` to the embedding_config row, seeding it if the table is empty."""
    with conn.cursor() as cur:
        cur.execute("SELECT model, version, dims FROM embedding_config WHERE id = 1")
        row = cur.fetchone()

    if row is None:
        seed_embedding_config(conn, cfg)
        return

    stored_model, stored_version, stored_dims = row
    diffs: list[str] = []
    if stored_model != cfg.model:
        diffs.append(f"model: stored={stored_model!r} configured={cfg.model!r}")
    if stored_version != cfg.version:
        diffs.append(f"version: stored={stored_version!r} configured={cfg.version!r}")
    if stored_dims != cfg.dims:
        diffs.append(f"dims: stored={stored_dims} configured={cfg.dims}")

    if diffs:
        raise EmbeddingConfigMismatch(
            "Configured embedding model does not match the embedding_config row:\n  "
            + "\n  ".join(diffs)
            + "\nThe index was built with the stored model. Re-embed the corpus, or "
            "restore the configured model to match, before starting."
        )


def run_startup_check(settings: Settings | None = None) -> None:
    """Load settings, open a DB connection and run the guard."""
    settings = settings or get_settings()
    try:
        with psycopg.connect(settings.database_url) as conn:
            check_embedding_config(conn, settings.embedding)
    except EmbeddingConfigMismatch as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except psycopg.Error as exc:
        print(f"error: could not verify embedding_config: {exc}", file=sys.stderr)
        sys.exit(1)
