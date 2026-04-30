import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

import news_digest

DEFAULT_LANGUAGE_CODE = "en"


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
    _seed_multilingual_lexicons(conn, vocab_source_dir)


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
          global_translation_enabled INTEGER NOT NULL DEFAULT 0,
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

        CREATE TABLE IF NOT EXISTS user_profile (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          display_name TEXT NOT NULL DEFAULT 'FloatVocab User',
          avatar_url TEXT NOT NULL DEFAULT '',
          bio TEXT NOT NULL DEFAULT '',
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS app_settings (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          theme TEXT NOT NULL DEFAULT 'light',
          default_window_width INTEGER NOT NULL DEFAULT 1180,
          default_window_height INTEGER NOT NULL DEFAULT 760,
          launch_at_startup INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    _ensure_lexicon_schema(conn)
    _ensure_plan_columns(conn)
    _ensure_word_columns(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO plans (id, lexicon_id, daily_new, target_date, current_language_code)
        VALUES (1, NULL, 20, ?, ?)
        """,
        [(date.today() + timedelta(days=90)).isoformat(), DEFAULT_LANGUAGE_CODE],
    )
    conn.execute("INSERT OR IGNORE INTO user_profile (id) VALUES (1)")
    conn.execute("INSERT OR IGNORE INTO app_settings (id) VALUES (1)")
    conn.commit()


def _ensure_lexicon_schema(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(lexicons)").fetchall()}
    if "language_code" in columns:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        f"""
        CREATE TABLE lexicons_new (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          language_code TEXT NOT NULL DEFAULT '{DEFAULT_LANGUAGE_CODE}',
          source TEXT NOT NULL DEFAULT 'built-in',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(language_code, name)
        );

        INSERT INTO lexicons_new (id, name, language_code, source, created_at)
        SELECT id, name, '{DEFAULT_LANGUAGE_CODE}', source, created_at
        FROM lexicons;

        DROP TABLE lexicons;
        ALTER TABLE lexicons_new RENAME TO lexicons;
        """
    )
    conn.execute("PRAGMA foreign_keys = ON")


def _ensure_plan_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if "widget_size" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN widget_size TEXT NOT NULL DEFAULT 'medium'")
    if "current_word_id" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN current_word_id INTEGER")
    if "current_language_code" not in columns:
        conn.execute(f"ALTER TABLE plans ADD COLUMN current_language_code TEXT NOT NULL DEFAULT '{DEFAULT_LANGUAGE_CODE}'")
    if "global_translation_enabled" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN global_translation_enabled INTEGER NOT NULL DEFAULT 0")


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
    if conn.execute(
        "SELECT 1 FROM lexicons WHERE name = ? AND language_code = ?",
        ("鑰冪爺鏍稿績 50", DEFAULT_LANGUAGE_CODE),
    ).fetchone():
        return
    with builtin_lexicon.open("r", encoding="utf-8") as file:
        words = json.load(file)
    lexicon_id = _create_lexicon(conn, "鑰冪爺鏍稿績 50", "built-in", DEFAULT_LANGUAGE_CODE)
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
    conn.execute(
        "UPDATE plans SET lexicon_id = ?, current_language_code = ? WHERE id = 1 AND lexicon_id IS NULL",
        (lexicon_id, DEFAULT_LANGUAGE_CODE),
    )
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
        if conn.execute(
            "SELECT 1 FROM lexicons WHERE name = ? AND language_code = ?",
            (lexicon_name, DEFAULT_LANGUAGE_CODE),
        ).fetchone():
            continue
        source_path = vocab_source_dir / file_name
        if not source_path.exists():
            continue
        with source_path.open("r", encoding="utf-8") as file:
            rows = json.load(file)
        lexicon_id = _create_lexicon(conn, lexicon_name, "built-in", DEFAULT_LANGUAGE_CODE)
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


def _seed_multilingual_lexicons(conn: sqlite3.Connection, vocab_source_dir: Path) -> None:
    if not vocab_source_dir.exists():
        return
    today = date.today().isoformat()
    for language_dir in vocab_source_dir.iterdir():
        if not language_dir.is_dir():
            continue
        language_code = language_dir.name.strip().lower()
        for source_path in sorted(language_dir.glob("*.json")):
            with source_path.open("r", encoding="utf-8") as file:
                rows = json.load(file)
            if not isinstance(rows, list) or not rows:
                continue
            explicit_language_code = next(
                (str(row.get("language_code", "")).strip().lower() for row in rows if isinstance(row, dict) and str(row.get("language_code", "")).strip()),
                "",
            )
            next_language_code = explicit_language_code or language_code or DEFAULT_LANGUAGE_CODE
            lexicon_name = next(
                (str(row.get("lexicon_name", "")).strip() for row in rows if isinstance(row, dict) and str(row.get("lexicon_name", "")).strip()),
                source_path.stem,
            )
            lexicon_id = _create_lexicon(conn, lexicon_name, "built-in", next_language_code)
            for row in rows:
                if not isinstance(row, dict):
                    continue
                word = str(row.get("word") or "").strip()
                meaning = str(row.get("meaning") or "").strip()
                if not word or not meaning:
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO words
                    (lexicon_id, word, phonetic, meaning, example, next_review_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexicon_id,
                        word,
                        str(row.get("phonetic") or "").strip(),
                        meaning,
                        str(row.get("example") or "").strip(),
                        today,
                    ),
                )
    conn.commit()


def _create_lexicon(
    conn: sqlite3.Connection,
    name: str,
    source: str = "custom",
    language_code: str = DEFAULT_LANGUAGE_CODE,
) -> int:
    cursor = conn.execute(
        "INSERT OR IGNORE INTO lexicons (name, language_code, source) VALUES (?, ?, ?)",
        (name, language_code, source),
    )
    conn.commit()
    if cursor.lastrowid:
        return cursor.lastrowid
    return conn.execute(
        "SELECT id FROM lexicons WHERE name = ? AND language_code = ?",
        (name, language_code),
    ).fetchone()["id"]
