import json
import sqlite3
import shutil
import unittest
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

from floatvocab.db import (
    BUILTIN_LEXICON_NAME,
    LEGACY_BUILTIN_LEXICON_NAME,
    initialize_database,
    open_connection,
)
from floatvocab.repositories.lexicon_repository import LexiconRepository
from floatvocab.repositories.plan_repository import PlanRepository


class MultilingualSchemaTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / "_tmp_multilingual" / uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.db_path = self.root / "multilingual.db"
        self.builtin_lexicon = self.root / "builtin.json"
        self.builtin_lexicon.write_text("[]", encoding="utf-8")
        self.vocab_source_dir = self.root / "vocab"
        self.vocab_source_dir.mkdir()

    def _create_legacy_schema(self) -> sqlite3.Connection:
        conn = open_connection(self.db_path)
        conn.executescript(
            """
            CREATE TABLE lexicons (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              source TEXT NOT NULL DEFAULT 'built-in',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

            CREATE TABLE words (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              lexicon_id INTEGER NOT NULL,
              word TEXT NOT NULL,
              phonetic TEXT DEFAULT '',
              meaning TEXT NOT NULL,
              example TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'new',
              next_review_date TEXT NOT NULL,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE CASCADE
            );

            INSERT INTO lexicons (id, name, source) VALUES (1, 'Legacy English', 'custom');
            INSERT INTO plans (id, lexicon_id, daily_new, target_date) VALUES (1, 1, 20, '2030-01-01');
            INSERT INTO words (id, lexicon_id, word, meaning, next_review_date) VALUES (1, 1, 'legacy', 'old meaning', '2030-01-01');
            """
        )
        conn.commit()
        return conn

    def _initialize(self, conn: sqlite3.Connection) -> None:
        initialize_database(
            conn,
            builtin_lexicon=self.builtin_lexicon,
            vocab_source_dir=self.vocab_source_dir,
            exam_lexicons=[],
            qwerty_item_to_word=lambda item, _lexicon_name: None,
        )

    def test_schema_migration_adds_language_columns_and_defaults_to_english(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)

        self._initialize(conn)

        lexicon_columns = {row["name"] for row in conn.execute("PRAGMA table_info(lexicons)").fetchall()}
        plan_columns = {row["name"] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}

        self.assertIn("language_code", lexicon_columns)
        self.assertIn("current_language_code", plan_columns)

        legacy_lexicon = conn.execute(
            "SELECT name, language_code FROM lexicons WHERE id = 1"
        ).fetchone()
        plan = conn.execute("SELECT current_language_code FROM plans WHERE id = 1").fetchone()
        legacy_word = conn.execute("SELECT lexicon_id, word, meaning FROM words WHERE id = 1").fetchone()

        self.assertEqual(legacy_lexicon["language_code"], "en")
        self.assertEqual(plan["current_language_code"], "en")
        self.assertEqual(legacy_word["lexicon_id"], 1)
        self.assertEqual(legacy_word["word"], "legacy")
        self.assertEqual(legacy_word["meaning"], "old meaning")

    def test_builtin_lexicon_uses_readable_chinese_name_on_fresh_database(self):
        self.builtin_lexicon.write_text(
            json.dumps(
                [
                    {
                        "word": "personnel",
                        "phonetic": "/ˌpɜːsəˈnel/",
                        "meaning": "人员",
                        "example": "The personnel file was updated.",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        conn = open_connection(self.db_path)
        self.addCleanup(conn.close)

        self._initialize(conn)

        lexicons = conn.execute("SELECT name FROM lexicons ORDER BY id").fetchall()
        self.assertEqual([row["name"] for row in lexicons], [BUILTIN_LEXICON_NAME])
        self.assertNotIn(LEGACY_BUILTIN_LEXICON_NAME, [row["name"] for row in lexicons])

    def test_legacy_builtin_lexicon_name_is_renamed_during_migration(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)
        conn.execute("UPDATE lexicons SET name = ? WHERE id = 1", (LEGACY_BUILTIN_LEXICON_NAME,))
        conn.commit()

        self._initialize(conn)

        lexicon = conn.execute("SELECT id, name FROM lexicons WHERE id = 1").fetchone()
        plan = conn.execute("SELECT lexicon_id FROM plans WHERE id = 1").fetchone()
        self.assertEqual(lexicon["name"], BUILTIN_LEXICON_NAME)
        self.assertEqual(plan["lexicon_id"], 1)

    def test_legacy_builtin_lexicon_is_merged_when_canonical_already_exists(self):
        conn = open_connection(self.db_path)
        self.addCleanup(conn.close)
        self._initialize(conn)
        conn.execute(
            "INSERT INTO lexicons (id, name, language_code, source) VALUES (100, ?, 'en', 'built-in')",
            (LEGACY_BUILTIN_LEXICON_NAME,),
        )
        conn.execute(
            "INSERT INTO words (lexicon_id, word, meaning, next_review_date) VALUES (100, 'legacy-only', 'old', '2030-01-01')"
        )
        canonical_id = conn.execute(
            "SELECT id FROM lexicons WHERE name = ? AND language_code = 'en'",
            (BUILTIN_LEXICON_NAME,),
        ).fetchone()["id"]
        conn.execute("UPDATE plans SET lexicon_id = ? WHERE id = 1", (100,))
        conn.commit()

        self._initialize(conn)

        rows = conn.execute(
            "SELECT id, name FROM lexicons WHERE language_code = 'en' AND name IN (?, ?)",
            (BUILTIN_LEXICON_NAME, LEGACY_BUILTIN_LEXICON_NAME),
        ).fetchall()
        plan = conn.execute("SELECT lexicon_id FROM plans WHERE id = 1").fetchone()
        self.assertEqual([(row["id"], row["name"]) for row in rows], [(canonical_id, BUILTIN_LEXICON_NAME)])
        self.assertEqual(plan["lexicon_id"], canonical_id)

    def test_schema_migration_adds_global_translation_toggle_disabled_by_default(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)

        self._initialize(conn)

        plan_columns = {row["name"] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
        plan = conn.execute("SELECT global_translation_enabled FROM plans WHERE id = 1").fetchone()

        self.assertIn("global_translation_enabled", plan_columns)
        self.assertEqual(plan["global_translation_enabled"], 0)

    def test_lexicon_creation_is_unique_per_language_and_import_accepts_language_code(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)
        self._initialize(conn)

        repo = LexiconRepository(conn)

        english_id = repo.create_lexicon("Shared List", source="custom", language_code="en")
        french_import_count = repo.import_word_rows(
            "Shared List",
            [{"word": "bonjour", "meaning": "hello"}],
            source="import",
            language_code="fr",
        )
        duplicate_import_count = repo.import_word_rows(
            "Shared List",
            [{"word": "bonjour", "meaning": "hello"}],
            source="import",
            language_code="fr",
        )
        english_duplicate_id = repo.create_lexicon("Shared List", source="custom", language_code="en")

        self.assertEqual(english_id, english_duplicate_id)
        self.assertEqual(french_import_count, 1)
        self.assertEqual(duplicate_import_count, 0)

        rows = conn.execute(
            "SELECT language_code, name FROM lexicons WHERE name = ? ORDER BY language_code",
            ("Shared List",),
        ).fetchall()
        self.assertEqual([row["language_code"] for row in rows], ["en", "fr"])
        word_count = conn.execute(
            "SELECT COUNT(*) AS total FROM words WHERE lexicon_id = ?",
            (conn.execute("SELECT id FROM lexicons WHERE name = ? AND language_code = ?", ("Shared List", "fr")).fetchone()["id"],),
        ).fetchone()
        self.assertEqual(word_count["total"], 1)

    def test_list_lexicons_can_filter_by_language(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)
        self._initialize(conn)

        repo = LexiconRepository(conn)
        repo.create_lexicon("English Only", source="custom", language_code="en")
        repo.create_lexicon("Français", source="custom", language_code="fr")
        repo.create_lexicon("Español", source="custom", language_code="es")

        french_lexicons = repo.list_lexicons(language_code="fr")

        self.assertEqual([row["name"] for row in french_lexicons], ["Français"])
        self.assertTrue(all(row["language_code"] == "fr" for row in french_lexicons))

    def test_save_plan_persists_current_language_code(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)
        self._initialize(conn)

        repo = PlanRepository(conn)
        plan = repo.fetch_plan()
        repo.save_plan(
            lexicon_id=plan["lexicon_id"],
            daily_new=plan["daily_new"],
            target_date=plan["target_date"] or (date.today() + timedelta(days=30)).isoformat(),
            alpha=plan["float_alpha"],
            font_size=plan["font_size"],
            bg_color=plan["bg_color"],
            widget_size=plan["widget_size"],
            current_language_code="zh",
        )

        updated_plan = repo.fetch_plan()
        self.assertEqual(updated_plan["current_language_code"], "zh")

    def test_set_global_translation_enabled_persists_toggle(self):
        conn = self._create_legacy_schema()
        self.addCleanup(conn.close)
        self._initialize(conn)

        repo = PlanRepository(conn)
        repo.set_global_translation_enabled(True)
        self.assertEqual(repo.fetch_plan()["global_translation_enabled"], 1)

        repo.set_global_translation_enabled(False)
        self.assertEqual(repo.fetch_plan()["global_translation_enabled"], 0)


if __name__ == "__main__":
    unittest.main()
