from spire_rag.core.embedding_config import run_startup_check


def main():
    # Refuse to start on a mismatched or unreachable embedding_config.
    run_startup_check()
    print("Hello from spire-rag!")


if __name__ == "__main__":
    main()
