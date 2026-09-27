"""initial schema

Enables the required extensions (pgvector, pg_trgm) and creates every table in
the tech spec's data model, with foreign keys and indexes.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-25 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Embedding dimension is still an open question in the tech spec. HNSW and the
# vector columns need a fixed dimension at creation time, so we pin a placeholder
# here; the real value lives in embedding_config and is checked at start-up. Change
# this and re-migrate once the embedding model is chosen.
EMBED_DIM = 1024

CONTENT_TYPES = ("rule", "lore", "stat_block", "table", "sidebar", "caption")
ENTITY_TYPES = (
    "npc", "faction", "location", "item", "deity", "event", "class", "ancestry",
    "ability", "resistance", "condition", "skill", "domain", "creature", "game_term", "other",
)
SECTION_STATUS = ("included", "excluded", "suspected_scenario")
SUMMARY_LEVELS = ("section", "chapter", "book")
MESSAGE_ROLES = ("user", "assistant")

# Closed set of relationship predicates; entity_relations.predicate is an FK to
# this table so the extraction pass can only emit values that live here. Extend
# via a later migration, not ad hoc.
PREDICATES = [
    ("member_of", "subject is a member of object"),
    ("leads", "subject leads object"),
    ("located_in", "subject is located in object"),
    ("allied_with", "subject is allied with object"),
    ("rival_of", "subject is a rival of object"),
    ("worships", "subject (faction) worships object (deity)"),
]


def _in_check(column: str, values: tuple[str, ...], name: str) -> sa.CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return sa.CheckConstraint(f"{column} IN ({allowed})", name=name)


def _pk() -> sa.Column:
    return sa.Column("id", sa.BigInteger, sa.Identity(always=True), primary_key=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "books",
        _pk(),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("short_code", sa.Text, nullable=False, unique=True),
        sa.Column("book_type", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "sections",
        _pk(),
        sa.Column("book_id", sa.BigInteger, sa.ForeignKey("books.id"), nullable=False),
        sa.Column("parent_id", sa.BigInteger, sa.ForeignKey("sections.id")),
        sa.Column("title", sa.Text),
        sa.Column("path", sa.Text),
        sa.Column("page_start", sa.Integer),
        sa.Column("page_end", sa.Integer),
        sa.Column("status", sa.Text, nullable=False, server_default="included"),
        _in_check("status", SECTION_STATUS, "sections_status_check"),
    )

    op.create_table(
        "chunks",
        _pk(),
        sa.Column("section_id", sa.BigInteger, sa.ForeignKey("sections.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embed_text", sa.Text),
        sa.Column("content_type", sa.Text, nullable=False),
        sa.Column("mechanics", ARRAY(sa.Text), nullable=False,
                  server_default=sa.text("'{}'::text[]")),
        sa.Column("page_start", sa.Integer),
        sa.Column("page_end", sa.Integer),
        sa.Column("canonical_id", sa.BigInteger, sa.ForeignKey("chunks.id")),
        sa.Column("tsv", TSVECTOR,
                  sa.Computed("to_tsvector('english', text)", persisted=True)),
        sa.Column("embedding", Vector(EMBED_DIM)),
        _in_check("content_type", CONTENT_TYPES, "chunks_content_type_check"),
    )

    op.create_table(
        "chunk_locations",
        _pk(),
        sa.Column("chunk_id", sa.BigInteger, sa.ForeignKey("chunks.id"), nullable=False),
        sa.Column("book_id", sa.BigInteger, sa.ForeignKey("books.id"), nullable=False),
        sa.Column("page", sa.Integer, nullable=False),
    )

    op.create_table(
        "section_refs",
        _pk(),
        sa.Column("from_chunk_id", sa.BigInteger, sa.ForeignKey("chunks.id"), nullable=False),
        sa.Column("to_section_id", sa.BigInteger, sa.ForeignKey("sections.id")),
        sa.Column("raw_text", sa.Text, nullable=False),
    )

    op.create_table(
        "entities",
        _pk(),
        sa.Column("canonical_name", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("dossier", sa.Text),
        sa.Column("dossier_embedding", Vector(EMBED_DIM)),
        _in_check("type", ENTITY_TYPES, "entities_type_check"),
    )

    op.create_table(
        "entity_aliases",
        _pk(),
        sa.Column("entity_id", sa.BigInteger, sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("alias", sa.Text, nullable=False),
    )

    op.create_table(
        "entity_mentions",
        _pk(),
        sa.Column("entity_id", sa.BigInteger, sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("chunk_id", sa.BigInteger, sa.ForeignKey("chunks.id"), nullable=False),
        sa.Column("surface_form", sa.Text),
    )

    op.create_table(
        "relation_predicates",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("description", sa.Text),
    )

    op.create_table(
        "entity_relations",
        _pk(),
        sa.Column("subject_id", sa.BigInteger, sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("predicate", sa.Text,
                  sa.ForeignKey("relation_predicates.name"), nullable=False),
        sa.Column("object_id", sa.BigInteger, sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("chunk_id", sa.BigInteger, sa.ForeignKey("chunks.id"), nullable=False),
    )

    op.create_table(
        "summaries",
        _pk(),
        sa.Column("level", sa.Text, nullable=False),
        sa.Column("ref_id", sa.BigInteger, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBED_DIM)),
        _in_check("level", SUMMARY_LEVELS, "summaries_level_check"),
    )

    op.create_table(
        "embedding_config",
        sa.Column("id", sa.Integer, primary_key=True, server_default="1"),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("version", sa.Text, nullable=False),
        sa.Column("dims", sa.Integer, nullable=False),
        sa.CheckConstraint("id = 1", name="embedding_config_singleton_check"),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "invites",
        _pk(),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("redeemed_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "messages",
        _pk(),
        sa.Column("conversation_id", UUID(as_uuid=True),
                  sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("citations", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        _in_check("role", MESSAGE_ROLES, "messages_role_check"),
    )

    op.create_table(
        "eval_questions",
        _pk(),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("expected_answer", sa.Text),
        sa.Column("expected_pages", JSONB),
        sa.Column("category", sa.Text),
    )

    op.create_table(
        "eval_runs",
        _pk(),
        sa.Column("question_id", sa.BigInteger,
                  sa.ForeignKey("eval_questions.id"), nullable=False),
        sa.Column("scores", JSONB),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
    )

    # Seed the closed predicate vocabulary.
    predicates = sa.table(
        "relation_predicates",
        sa.column("name", sa.Text),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(
        predicates,
        [{"name": name, "description": desc} for name, desc in PREDICATES],
    )

    # HNSW on every embedding column (cosine; embeddings are expected normalised).
    op.create_index("ix_chunks_embedding", "chunks", ["embedding"],
                    postgresql_using="hnsw",
                    postgresql_ops={"embedding": "vector_cosine_ops"})
    op.create_index("ix_entities_dossier_embedding", "entities", ["dossier_embedding"],
                    postgresql_using="hnsw",
                    postgresql_ops={"dossier_embedding": "vector_cosine_ops"})
    op.create_index("ix_summaries_embedding", "summaries", ["embedding"],
                    postgresql_using="hnsw",
                    postgresql_ops={"embedding": "vector_cosine_ops"})

    # Full-text and mechanics.
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")
    op.create_index("ix_chunks_mechanics", "chunks", ["mechanics"], postgresql_using="gin")

    # Trigram for fuzzy alias lookup.
    op.create_index("ix_entity_aliases_alias_trgm", "entity_aliases", ["alias"],
                    postgresql_using="gin",
                    postgresql_ops={"alias": "gin_trgm_ops"})

    # B-tree on content_type and every foreign key.
    op.create_index("ix_chunks_content_type", "chunks", ["content_type"])
    op.create_index("ix_sections_book_id", "sections", ["book_id"])
    op.create_index("ix_sections_parent_id", "sections", ["parent_id"])
    op.create_index("ix_sections_status", "sections", ["status"])
    op.create_index("ix_chunks_section_id", "chunks", ["section_id"])
    op.create_index("ix_chunks_canonical_id", "chunks", ["canonical_id"])
    op.create_index("ix_chunk_locations_chunk_id", "chunk_locations", ["chunk_id"])
    op.create_index("ix_chunk_locations_book_id", "chunk_locations", ["book_id"])
    op.create_index("ix_section_refs_from_chunk_id", "section_refs", ["from_chunk_id"])
    op.create_index("ix_section_refs_to_section_id", "section_refs", ["to_section_id"])
    op.create_index("ix_entity_aliases_entity_id", "entity_aliases", ["entity_id"])
    op.create_index("ix_entity_mentions_entity_id", "entity_mentions", ["entity_id"])
    op.create_index("ix_entity_mentions_chunk_id", "entity_mentions", ["chunk_id"])
    op.create_index("ix_entity_relations_subject_id", "entity_relations", ["subject_id"])
    op.create_index("ix_entity_relations_object_id", "entity_relations", ["object_id"])
    op.create_index("ix_entity_relations_predicate", "entity_relations", ["predicate"])
    op.create_index("ix_entity_relations_chunk_id", "entity_relations", ["chunk_id"])
    op.create_index("ix_invites_created_by", "invites", ["created_by"])
    op.create_index("ix_invites_redeemed_by", "invites", ["redeemed_by"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_eval_runs_question_id", "eval_runs", ["question_id"])


def downgrade() -> None:
    # Reverse of creation order so foreign keys never block a drop. Indexes are
    # dropped implicitly with their tables.
    for table in (
        "eval_runs", "eval_questions", "messages", "conversations", "invites", "users",
        "embedding_config", "summaries", "entity_relations", "relation_predicates",
        "entity_mentions", "entity_aliases", "entities", "section_refs", "chunk_locations",
        "chunks", "sections", "books",
    ):
        op.drop_table(table)

    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS vector")
