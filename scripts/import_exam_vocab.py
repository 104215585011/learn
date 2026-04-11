import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "floatvocab.db"
CACHE_DIR = ROOT / "data" / "vocab_sources"
RAW_BASE = "https://raw.githubusercontent.com/RealKai42/qwerty-learner/master/public/dicts"


@dataclass(frozen=True)
class Source:
    key: str
    lexicon_name: str
    file_name: str
    source_name: str = "qwerty-learner"

    @property
    def url(self) -> str:
        return f"{RAW_BASE}/{self.file_name}"


SOURCES = [
    Source("kaoyan", "考研词汇", "KaoYan_3_T.json"),
    Source("cet4", "大学英语四级 CET-4", "CET4_T.json"),
    Source("cet6", "大学英语六级 CET-6", "CET6_T.json"),
    Source("tem4", "英语专业四级 TEM-4", "Level4luan_2_T.json"),
    Source("tem8", "英语专业八级 TEM-8", "Level8luan_2_T.json"),
    Source("toefl", "托福 TOEFL", "TOEFL_3_T.json"),
    Source("ielts", "雅思 IELTS", "IELTS_3_T.json"),
    Source("pte_wfd", "PTE WFD", "PTE_WFD.json"),
    Source("pte_fib_l", "PTE FIB Listening", "PTE_FIB_L.json"),
    Source("pte_fib_r", "PTE FIB Reading", "PTE_FIB_R_junior.json"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download exam vocabulary lists and import them into FloatVocab."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help=f"FloatVocab SQLite database path. Default: {DB_PATH}",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=CACHE_DIR,
        help=f"Downloaded source cache directory. Default: {CACHE_DIR}",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=[source.key for source in SOURCES],
        help="Only import selected source keys.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Download again even when a cached source file exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download and parse, but do not write to the database.",
    )
    return parser.parse_args()


def download_json(source: Source, cache_dir: Path, refresh: bool) -> list[dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / source.file_name
    if cache_path.exists() and not refresh:
        text = cache_path.read_text(encoding="utf-8")
    else:
        request = Request(
            source.url,
            headers={
                "User-Agent": "FloatVocab-importer/1.0",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                text = response.read().decode("utf-8")
        except URLError as exc:
            if cache_path.exists():
                print(f"[warn] {source.key}: download failed, using cache: {exc}")
                text = cache_path.read_text(encoding="utf-8")
            else:
                raise RuntimeError(f"{source.key}: failed to download {source.url}: {exc}") from exc
        else:
            cache_path.write_text(text, encoding="utf-8")

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{source.key}: source JSON must be a list")
    return [item for item in data if isinstance(item, dict)]


def normalize_word(item: dict[str, Any], source: Source) -> dict[str, str] | None:
    word = first_text(item, "name", "word", "text", "content").strip()
    if not word:
        return None

    trans = item.get("trans")
    if isinstance(trans, list):
        meaning = "；".join(str(part).strip() for part in trans if str(part).strip())
    else:
        meaning = first_text(item, "translation", "meaning", "definition", "desc").strip()
    if not meaning:
        meaning = f"{source.lexicon_name} 词条"

    phonetic = first_text(item, "usphone", "ukphone", "phone", "phonetic").strip()
    if phonetic and not (phonetic.startswith("/") and phonetic.endswith("/")):
        phonetic = f"/{phonetic}/"

    example = first_text(item, "sentence", "example", "phrase", "remark").strip()
    return {
        "word": word,
        "phonetic": phonetic,
        "meaning": meaning,
        "example": example,
    }


def first_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS lexicons (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          source TEXT NOT NULL DEFAULT 'built-in',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS words (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          lexicon_id INTEGER NOT NULL,
          word TEXT NOT NULL,
          phonetic TEXT DEFAULT '',
          meaning TEXT NOT NULL,
          example TEXT DEFAULT '',
          status TEXT NOT NULL DEFAULT 'new',
          next_review_date TEXT NOT NULL,
          interval_days INTEGER NOT NULL DEFAULT 0,
          repetitions INTEGER NOT NULL DEFAULT 0,
          ease_factor REAL NOT NULL DEFAULT 2.5,
          seen_count INTEGER NOT NULL DEFAULT 0,
          correct_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(lexicon_id, word),
          FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS plans (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          lexicon_id INTEGER,
          daily_new INTEGER NOT NULL DEFAULT 20,
          target_date TEXT NOT NULL,
          float_alpha REAL NOT NULL DEFAULT 0.88,
          font_size INTEGER NOT NULL DEFAULT 22,
          bg_color TEXT NOT NULL DEFAULT '#fff8d7',
          widget_size TEXT NOT NULL DEFAULT 'medium',
          FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE SET NULL
        );
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if "widget_size" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN widget_size TEXT NOT NULL DEFAULT 'medium'")


def create_lexicon(conn: sqlite3.Connection, name: str, source: str) -> int:
    conn.execute("INSERT OR IGNORE INTO lexicons (name, source) VALUES (?, ?)", (name, source))
    row = conn.execute("SELECT id FROM lexicons WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"failed to create lexicon: {name}")
    return int(row[0])


def import_source(conn: sqlite3.Connection, source: Source, rows: list[dict[str, str]]) -> tuple[int, int]:
    lexicon_id = create_lexicon(conn, source.lexicon_name, source.source_name)
    today = date.today().isoformat()
    inserted = 0
    skipped = 0
    for row in rows:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO words
            (lexicon_id, word, phonetic, meaning, example, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                lexicon_id,
                row["word"],
                row["phonetic"],
                row["meaning"],
                row["example"],
                today,
            ),
        )
        if cursor.rowcount:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def main() -> int:
    args = parse_args()
    selected = [source for source in SOURCES if not args.only or source.key in args.only]
    if not selected:
        print("No sources selected.")
        return 1

    prepared: list[tuple[Source, list[dict[str, str]]]] = []
    for source in selected:
        raw_rows = download_json(source, args.cache_dir, args.refresh)
        rows = [row for item in raw_rows if (row := normalize_word(item, source))]
        prepared.append((source, rows))
        print(f"[parse] {source.key}: {len(rows)} rows from {source.file_name}")

    if args.dry_run:
        print("[dry-run] database was not changed.")
        return 0

    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        ensure_schema(conn)
        total_inserted = 0
        total_skipped = 0
        for source, rows in prepared:
            inserted, skipped = import_source(conn, source, rows)
            total_inserted += inserted
            total_skipped += skipped
            print(f"[import] {source.lexicon_name}: +{inserted}, skipped {skipped}")
        conn.commit()

    print(f"[done] inserted {total_inserted}, skipped {total_skipped}, db={args.db}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)
