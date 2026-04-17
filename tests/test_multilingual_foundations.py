import shutil
import sqlite3
import unittest
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import app
from floatvocab.db import DEFAULT_LANGUAGE_CODE, initialize_database, open_connection
from floatvocab.repositories.lexicon_repository import SUPPORTED_LANGUAGES


class MultilingualFoundationTests(unittest.TestCase):
    def setUp(self):
        ignored_temp_root = Path(app.APP_ROOT) / ".worktrees"
        ignored_temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_root_path = ignored_temp_root / f"test_multilingual_{uuid4().hex}"
        self.temp_root_path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(self.temp_root_path, ignore_errors=True))
        self.db_path = self.temp_root_path / "test.db"

    def test_initialize_database_migrates_legacy_lexicons_and_plan_to_english(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE lexicons (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              source TEXT NOT NULL DEFAULT 'built-in',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE words (
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
              UNIQUE(lexicon_id, word)
            );

            CREATE TABLE plans (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              lexicon_id INTEGER,
              daily_new INTEGER NOT NULL DEFAULT 20,
              target_date TEXT,
              float_alpha REAL NOT NULL DEFAULT 0.88,
              font_size INTEGER NOT NULL DEFAULT 26,
              bg_color TEXT NOT NULL DEFAULT '#F7FAF5',
              widget_size TEXT NOT NULL DEFAULT 'medium',
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            "INSERT INTO lexicons (id, name, source) VALUES (1, 'Legacy Pack', 'import')"
        )
        conn.execute(
            """
            INSERT INTO words
            (lexicon_id, word, phonetic, meaning, example, next_review_date)
            VALUES (1, 'legacy', '', 'legacy meaning', '', ?)
            """,
            (date.today().isoformat(),),
        )
        conn.execute(
            "INSERT INTO plans (id, lexicon_id, daily_new, target_date) VALUES (1, 1, 20, ?)",
            ((date.today() + timedelta(days=90)).isoformat(),),
        )
        conn.commit()

        initialize_database(
            conn,
            builtin_lexicon=app.BUILTIN_LEXICON,
            vocab_source_dir=self.temp_root_path / "missing-sources",
            exam_lexicons=[],
            qwerty_item_to_word=app.qwerty_item_to_word,
        )

        lexicon = conn.execute("SELECT * FROM lexicons WHERE id = 1").fetchone()
        plan = conn.execute("SELECT * FROM plans WHERE id = 1").fetchone()
        word = conn.execute("SELECT * FROM words WHERE lexicon_id = 1").fetchone()

        self.assertEqual(lexicon["language_code"], DEFAULT_LANGUAGE_CODE)
        self.assertEqual(plan["current_language_code"], DEFAULT_LANGUAGE_CODE)
        self.assertEqual(plan["lexicon_id"], 1)
        self.assertEqual(word["word"], "legacy")
        conn.close()

    def test_lexicon_repository_allows_same_name_in_different_languages(self):
        db = app.FloatVocabDB(self.db_path)
        self.addCleanup(db.conn.close)

        english_id = db.create_lexicon("Core 3000", "import", "en")
        japanese_id = db.create_lexicon("Core 3000", "import", "ja")

        self.assertNotEqual(english_id, japanese_id)
        english_only = db.lexicons("en")
        japanese_only = db.lexicons("ja")
        self.assertEqual([row["language_code"] for row in english_only], ["en"] * len(english_only))
        self.assertEqual([row["language_code"] for row in japanese_only], ["ja"] * len(japanese_only))

    def test_import_word_rows_counts_only_new_rows_within_same_language_lexicon(self):
        db = app.FloatVocabDB(self.db_path)
        self.addCleanup(db.conn.close)

        first = db.lexicon_repository.import_word_rows(
            "Spanish Basics",
            [{"word": "hola", "meaning": "hello"}, {"word": "adios", "meaning": "bye"}],
            language_code="es",
        )
        second = db.lexicon_repository.import_word_rows(
            "Spanish Basics",
            [{"word": "hola", "meaning": "hello"}, {"word": "gracias", "meaning": "thanks"}],
            language_code="es",
        )
        rows = db.conn.execute(
            "SELECT word FROM words WHERE lexicon_id = (SELECT id FROM lexicons WHERE name = ? AND language_code = ?)",
            ("Spanish Basics", "es"),
        ).fetchall()

        self.assertEqual(first, 2)
        self.assertEqual(second, 1)
        self.assertEqual({row["word"] for row in rows}, {"hola", "adios", "gracias"})

    def test_supported_languages_match_design_codes(self):
        self.assertEqual(
            [code for code, _label in SUPPORTED_LANGUAGES],
            ["en", "es", "fr", "ko", "ja", "it", "id", "ru", "ar", "pt"],
        )

    def test_import_words_prefers_embedded_language_code_over_current_language(self):
        csv_path = self.temp_root_path / "words.csv"
        csv_path.write_text("word,meaning,language_code\nhola,hello,es\ngracias,thanks,es\n", encoding="utf-8")

        db = app.FloatVocabDB(self.db_path)
        self.addCleanup(db.conn.close)

        imported, name, language_code = db.import_words(str(csv_path), current_language_code="ja")
        lexicon = db.conn.execute("SELECT * FROM lexicons WHERE name = ?", (name,)).fetchone()

        self.assertEqual(imported, 2)
        self.assertEqual(language_code, "es")
        self.assertEqual(lexicon["language_code"], "es")


if __name__ == "__main__":
    unittest.main()
