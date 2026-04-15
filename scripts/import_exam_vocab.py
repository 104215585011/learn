import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import date
from http.client import IncompleteRead
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "floatvocab.db"
CACHE_DIR = ROOT / "data" / "vocab_sources"
QWERTY_BASE = "https://raw.githubusercontent.com/RealKai42/qwerty-learner/master/public/dicts"
KYLEBING_BASE = "https://raw.githubusercontent.com/KyleBing/english-vocabulary/master/json_original/json-sentence"


@dataclass(frozen=True)
class Source:
    key: str
    lexicon_name: str
    cache_name: str
    upstream_name: str
    provider: str
    source_name: str

    @property
    def url(self) -> str:
        base = KYLEBING_BASE if self.provider == "kylebing" else QWERTY_BASE
        return f"{base}/{self.upstream_name}"


SOURCES = [
    Source("junior", "初中词汇", "ChuZhong_3_T.json", "ChuZhong_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("senior", "高中词汇", "GaoZhong_3_T.json", "GaoZhong_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("cet4", "大学英语四级 CET-4", "CET4_T.json", "CET4_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("cet6", "大学英语六级 CET-6", "CET6_T.json", "CET6_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("kaoyan", "考研词汇", "KaoYan_3_T.json", "KaoYan_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("toefl", "托福 TOEFL", "TOEFL_3_T.json", "TOEFL_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("ielts", "雅思 IELTS", "IELTS_3_T.json", "IELTS_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("tem4", "英语专业四级 TEM-4", "Level4luan_2_T.json", "Level4luan_2.json", "kylebing", "KyleBing english-vocabulary"),
    Source("tem8", "英语专业八级 TEM-8", "Level8luan_2_T.json", "Level8luan_2.json", "kylebing", "KyleBing english-vocabulary"),
    Source("sat", "SAT", "SAT_3_T.json", "SAT_3.json", "kylebing", "KyleBing english-vocabulary"),
    Source("pte_wfd", "PTE WFD", "PTE_WFD.json", "PTE_WFD.json", "qwerty", "qwerty-learner"),
    Source("pte_fib_l", "PTE FIB Listening", "PTE_FIB_L.json", "PTE_FIB_L.json", "qwerty", "qwerty-learner"),
    Source("pte_fib_r", "PTE FIB Reading", "PTE_FIB_R_junior.json", "PTE_FIB_R_junior.json", "qwerty", "qwerty-learner"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download exam vocabulary lists and import them into FloatVocab.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help=f"FloatVocab SQLite database path. Default: {DB_PATH}")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR, help=f"Vocabulary cache directory. Default: {CACHE_DIR}")
    parser.add_argument("--only", nargs="+", choices=[source.key for source in SOURCES], help="Only import selected source keys.")
    parser.add_argument("--refresh", action="store_true", help="Download again even when a cached source file exists.")
    parser.add_argument("--dry-run", action="store_true", help="Download and parse, but do not write to the database.")
    return parser.parse_args()


def fetch_text(url: str, timeout: int = 60, retries: int = 3) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "FloatVocab-importer/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    last_error: Exception | None = None
    for _attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except (URLError, IncompleteRead) as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"failed to fetch {url}")


def first_text(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def normalize_qwerty(item: dict[str, Any], source: Source) -> dict[str, str] | None:
    word = first_text(item, "name", "word", "text", "content")
    if not word:
        return None

    trans = item.get("trans")
    if isinstance(trans, list):
        meaning = "；".join(str(part).strip() for part in trans if str(part).strip())
    else:
        meaning = first_text(item, "translation", "meaning", "definition", "desc")
    if not meaning:
        meaning = source.lexicon_name

    phonetic = first_text(item, "usphone", "ukphone", "phone", "phonetic")
    if phonetic and not (phonetic.startswith("/") and phonetic.endswith("/")):
        phonetic = f"/{phonetic}/"

    example = first_text(item, "sentence", "example", "phrase", "remark")
    return {
        "word": word,
        "phonetic": phonetic,
        "meaning": meaning,
        "example": example,
        "example_source": source.source_name if example else "",
    }


def normalize_kylebing(item: dict[str, Any], source: Source) -> dict[str, str] | None:
    word = first_text(item, "word")
    if not word:
        return None

    translations = item.get("translations")
    parts: list[str] = []
    if isinstance(translations, list):
        for entry in translations:
            if not isinstance(entry, dict):
                continue
            translation = first_text(entry, "translation")
            word_type = first_text(entry, "type")
            if translation and word_type:
                parts.append(f"{word_type}. {translation}")
            elif translation:
                parts.append(translation)
    meaning = "；".join(parts) if parts else source.lexicon_name

    us = first_text(item, "us")
    uk = first_text(item, "uk")
    phonetic = us or uk
    if phonetic and not (phonetic.startswith("/") and phonetic.endswith("/")):
        phonetic = f"/{phonetic}/"

    example = ""
    sentences = item.get("sentences")
    if isinstance(sentences, list):
        for entry in sentences:
            if not isinstance(entry, dict):
                continue
            example = first_text(entry, "sentence")
            if example:
                break

    return {
        "word": word,
        "phonetic": phonetic,
        "meaning": meaning,
        "example": example,
        "example_source": source.source_name if example else "",
    }


def normalize_rows(raw_rows: list[dict[str, Any]], source: Source) -> list[dict[str, str]]:
    normalizer = normalize_kylebing if source.provider == "kylebing" else normalize_qwerty
    rows = []
    for item in raw_rows:
        row = normalizer(item, source)
        if row:
            rows.append(row)
    return rows


def load_source(source: Source, cache_dir: Path, refresh: bool) -> list[dict[str, str]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / source.cache_name
    if cache_path.exists() and not refresh:
        text = cache_path.read_text(encoding="utf-8")
    else:
        try:
            text = fetch_text(source.url)
        except URLError as exc:
            if cache_path.exists():
                print(f"[warn] {source.key}: download failed, using cache: {exc}")
                text = cache_path.read_text(encoding="utf-8")
            else:
                raise RuntimeError(f"{source.key}: failed to download {source.url}: {exc}") from exc
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"{source.key}: source JSON must be a list")
    rows = normalize_rows([item for item in data if isinstance(item, dict)], source)
    cache_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows


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
          example_source TEXT DEFAULT '',
          example_updated_at TEXT,
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
    plan_columns = {row[1] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if "widget_size" not in plan_columns:
        conn.execute("ALTER TABLE plans ADD COLUMN widget_size TEXT NOT NULL DEFAULT 'medium'")
    word_columns = {row[1] for row in conn.execute("PRAGMA table_info(words)").fetchall()}
    if "example_source" not in word_columns:
        conn.execute("ALTER TABLE words ADD COLUMN example_source TEXT DEFAULT ''")
    if "example_updated_at" not in word_columns:
        conn.execute("ALTER TABLE words ADD COLUMN example_updated_at TEXT")


def create_lexicon(conn: sqlite3.Connection, name: str, source: str) -> int:
    conn.execute("INSERT OR IGNORE INTO lexicons (name, source) VALUES (?, ?)", (name, source))
    row = conn.execute("SELECT id FROM lexicons WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"failed to create lexicon: {name}")
    return int(row[0])


def import_source(conn: sqlite3.Connection, source: Source, rows: list[dict[str, str]]) -> tuple[int, int, int]:
    lexicon_id = create_lexicon(conn, source.lexicon_name, source.source_name)
    today = date.today().isoformat()
    inserted = 0
    updated = 0
    unchanged = 0

    for row in rows:
        existing = conn.execute(
            "SELECT id, example FROM words WHERE lexicon_id = ? AND word = ?",
            (lexicon_id, row["word"]),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO words
                (lexicon_id, word, phonetic, meaning, example, example_source, example_updated_at, next_review_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lexicon_id,
                    row["word"],
                    row["phonetic"],
                    row["meaning"],
                    row["example"],
                    row.get("example_source", ""),
                    None,
                    today,
                ),
            )
            if row["example"]:
                conn.execute(
                    "UPDATE words SET example_updated_at = CURRENT_TIMESTAMP WHERE lexicon_id = ? AND word = ?",
                    (lexicon_id, row["word"]),
                )
            inserted += 1
            continue

        changes = []
        params: list[Any] = []
        if row["phonetic"]:
            changes.append("phonetic = ?")
            params.append(row["phonetic"])
        if row["meaning"]:
            changes.append("meaning = ?")
            params.append(row["meaning"])
        if row["example"] and not str(existing["example"] or "").strip():
            changes.append("example = ?")
            params.append(row["example"])
            changes.append("example_source = ?")
            params.append(row.get("example_source", ""))
            changes.append("example_updated_at = CURRENT_TIMESTAMP")
        if changes:
            params.append(existing["id"])
            conn.execute(f"UPDATE words SET {', '.join(changes)} WHERE id = ?", params)
            if row["example"] and not str(existing["example"] or "").strip():
                updated += 1
            else:
                unchanged += 1
        else:
            unchanged += 1

    return inserted, updated, unchanged


def main() -> int:
    args = parse_args()
    selected = [source for source in SOURCES if not args.only or source.key in args.only]
    if not selected:
        print("No sources selected.")
        return 1

    prepared: list[tuple[Source, list[dict[str, str]]]] = []
    for source in selected:
        rows = load_source(source, args.cache_dir, args.refresh)
        prepared.append((source, rows))
        print(f"[parse] {source.key}: {len(rows)} rows from {source.url}")

    if args.dry_run:
        print("[dry-run] database was not changed.")
        return 0

    args.db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.db) as conn:
        ensure_schema(conn)
        total_inserted = 0
        total_updated = 0
        total_unchanged = 0
        for source, rows in prepared:
            inserted, updated, unchanged = import_source(conn, source, rows)
            total_inserted += inserted
            total_updated += updated
            total_unchanged += unchanged
            print(f"[import] {source.lexicon_name}: +{inserted}, updated {updated}, unchanged {unchanged}")
        conn.commit()

    print(f"[done] inserted {total_inserted}, updated {total_updated}, unchanged {total_unchanged}, db={args.db}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1)
