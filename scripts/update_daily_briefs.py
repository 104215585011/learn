import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "floatvocab.db"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from news_digest import latest_briefs, refresh_latest_briefs


def main() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        refresh_latest_briefs(conn, limit=10)
        rows = latest_briefs(conn, limit=10)
    for row in rows:
        print(f"{row['source_name']}\t{row['published_at']}\t{row['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
