import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from example_pipeline import enrich_database

DB_PATH = ROOT / "floatvocab.db"


def parse_args():
    parser = argparse.ArgumentParser(description="Batch enrich missing word examples for FloatVocab.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    result = enrich_database(args.db, limit=args.limit, refresh=args.refresh)
    print(
        f"[done] processed={result['processed']} updated={result['updated']} skipped={result['skipped']} failures={len(result['failures'])}"
    )
    for word, error in result["failures"][:10]:
        print(f"[fail] {word}: {error}")


if __name__ == "__main__":
    main()
