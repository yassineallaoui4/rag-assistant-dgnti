"""Indexation explicite : python ingest.py [--rebuild]."""

import argparse
from pathlib import Path
from dotenv import load_dotenv


def main() -> int:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    from rag.vectorstore import reconstruire_base, synchroniser_base
    parser = argparse.ArgumentParser(description="Synchroniser les PDF avec la base documentaire.")
    parser.add_argument("--rebuild", action="store_true", help="Refaire aussi l'extraction des PDF inchangés.")
    args = parser.parse_args()
    try:
        db = reconstruire_base() if args.rebuild else synchroniser_base()
    except Exception as exc:
        print(f"Indexation interrompue : {exc}")
        return 1
    print(f"Indexation terminée : {len(db.get(include=[])['ids'])} passages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
