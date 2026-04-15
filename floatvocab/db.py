import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import news_digest


def open_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(
    conn: sqlite3.Connection,
    *,
    builtin_lexicon: Path,
    vocab_source_dir: Path,
    exam_lexicons: list[tuple[str, str]],
    qwerty_item_to_word: Callable[[dict, str], dict | None],
) -> None:
    _init_schema(conn)
    news_digest.ensure_schema(conn)
    _seed_builtin_lexicon(conn, builtin_lexicon)
    _seed_exam_lexicons(conn, vocab_source_dir, exam_lexicons, qwerty_item_to_word)


def _init_schema(conn: sqlite3.Connection) -> None:
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
          example_attempted_at TEXT,
          example_attempts INTEGER NOT NULL DEFAULT 0,
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
          target_date TEXT,
          float_alpha REAL NOT NULL DEFAULT 0.88,
          font_size INTEGER NOT NULL DEFAULT 26,
          bg_color TEXT NOT NULL DEFAULT '#F7FAF5',
          widget_size TEXT NOT NULL DEFAULT 'medium',
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS reviews (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          word_id INTEGER NOT NULL,
          rating INTEGER NOT NULL,
          old_interval_days INTEGER NOT NULL,
          new_interval_days INTEGER NOT NULL,
          reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS daily_stats (
          day TEXT PRIMARY KEY,
          reviewed INTEGER NOT NULL DEFAULT 0,
          known INTEGER NOT NULL DEFAULT 0,
          unknown INTEGER NOT NULL DEFAULT 0,
          new_seen INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    _ensure_plan_columns(conn)
    _ensure_word_columns(conn)
    conn.execute(
        "INSERT OR IGNORE INTO plans (id, lexicon_id, daily_new, target_date) VALUES (1, NULL, 20, ?)",
        [(date.today() + timedelta(days=90)).isoformat()],
    )
    conn.commit()


def _ensure_plan_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if "widget_size" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN widget_size TEXT NOT NULL DEFAULT 'medium'")
    if "current_word_id" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN current_word_id INTEGER")


def _ensure_word_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(words)").fetchall()}
    if "example_source" not in columns:
        conn.execute("ALTER TABLE words ADD COLUMN example_source TEXT DEFAULT ''")
    if "example_updated_at" not in columns:
        conn.execute("ALTER TABLE words ADD COLUMN example_updated_at TEXT")
    if "example_attempted_at" not in columns:
        conn.execute("ALTER TABLE words ADD COLUMN example_attempted_at TEXT")
    if "example_attempts" not in columns:
        conn.execute("ALTER TABLE words ADD COLUMN example_attempts INTEGER NOT NULL DEFAULT 0")


def _seed_builtin_lexicon(conn: sqlite3.Connection, builtin_lexicon: Path) -> None:
    if conn.execute("SELECT 1 FROM lexicons WHERE name = ?", ("考研核心 50",)).fetchone():
        return
    with builtin_lexicon.open("r", encoding="utf-8") as file:
        words = json.load(file)
    lexicon_id = _create_lexicon(conn, "考研核心 50", "built-in")
    today = date.today().isoformat()
    for item in words:
        conn.execute(
            """
            INSERT OR IGNORE INTO words
            (lexicon_id, word, phonetic, meaning, example, next_review_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (lexicon_id, item["word"], item.get("phonetic", ""), item["meaning"], item.get("example", ""), today),
        )
    conn.execute("UPDATE plans SET lexicon_id = ? WHERE id = 1 AND lexicon_id IS NULL", (lexicon_id,))
    conn.commit()


def _seed_exam_lexicons(
    conn: sqlite3.Connection,
    vocab_source_dir: Path,
    exam_lexicons: list[tuple[str, str]],
    qwerty_item_to_word: Callable[[dict, str], dict | None],
) -> None:
    if not vocab_source_dir.exists():
        return
    today = date.today().isoformat()
    for lexicon_name, file_name in exam_lexicons:
        if conn.execute("SELECT 1 FROM lexicons WHERE name = ?", (lexicon_name,)).fetchone():
            continue
        source_path = vocab_source_dir / file_name
        if not source_path.exists():
            continue
        with source_path.open("r", encoding="utf-8") as file:
            rows = json.load(file)
        lexicon_id = _create_lexicon(conn, lexicon_name, "built-in")
        for item in rows:
            row = qwerty_item_to_word(item, lexicon_name)
            if not row:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO words
                (lexicon_id, word, phonetic, meaning, example, next_review_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (lexicon_id, row["word"], row["phonetic"], row["meaning"], row["example"], today),
            )
    conn.commit()


def _create_lexicon(conn: sqlite3.Connection, name: str, source: str = "custom") -> int:
    cursor = conn.execute("INSERT OR IGNORE INTO lexicons (name, source) VALUES (?, ?)", (name, source))
    conn.commit()
    if cursor.lastrowid:
        return cursor.lastrowid
    return conn.execute("SELECT id FROM lexicons WHERE name = ?", (name,)).fetchone()["id"]

