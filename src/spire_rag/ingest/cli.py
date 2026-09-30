"""Ingestion CLI entry point.

For now this only runs the start-up guard so ingestion refuses to run on a
mismatched embedding model. Pipeline stages are added in later milestones.
"""
from spire_rag.core.embedding_config import run_startup_check


def main():
    run_startup_check()
    print("embedding_config ok; ingest pipeline not yet implemented")


if __name__ == "__main__":
    main()
