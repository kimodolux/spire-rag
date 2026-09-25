# spire-rag

A chat assistant that answers questions about the tabletop RPG *Spire: The City Must Fall*
from its sourcebooks, with book, section, and page citations. It handles both mechanical
rules questions and setting lore, and says clearly when the sources don't answer rather than
filling gaps from general game knowledge.

Retrieval runs over Postgres with the `pgvector` (embeddings) and `pg_trgm` (fuzzy text)
extensions — no dedicated vector database. See [TECH_SPEC.md](TECH_SPEC.md) for the full design.

## Layout

```
src/spire_rag/
  core/        shared models, DB access, config loading
  ingest/      layout-aware parsing and chunking of sourcebooks
  app/         chat application / query pipeline
  eval/        evaluation harness
config/        runtime configuration
migrations/    Alembic migrations (schema + extensions)
books/          source PDFs — git-ignored, personal-use copies
```

## Setup

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker, and Docker Compose.

1. **Install dependencies** into a local virtual environment:
   ```bash
   uv sync
   ```

2. **Start Postgres** (Postgres 16 with `pgvector` and `pg_trgm` available):
   ```bash
   docker compose up -d
   ```

3. **Apply migrations** to create the schema and enable the extensions:
   ```bash
   uv run alembic upgrade head
   ```

4. **Add your books** — drop your owned PDFs into `books/` (git-ignored).

That's it. Verify the database is ready:

```bash
docker compose exec db psql -U spire -d spire_rag -c "\dx"
```

You should see `vector` and `pg_trgm` listed.

## Development

```bash
uv run ruff check .     # lint
uv run ruff format .    # format
uv run pytest           # tests
```

The default database URL is `postgresql+psycopg://spire:spire@localhost:5432/spire_rag`.
