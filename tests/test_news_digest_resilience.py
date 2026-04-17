import sqlite3
import unittest
from unittest import mock

import news_digest


class NewsDigestResilienceTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        news_digest.ensure_schema(self.conn)
        self.conn.execute(
            """
            INSERT INTO daily_briefs (id, language_code, source_key, source_name, title, summary, url, published_at, saved)
            VALUES (1, 'en', 'bbc_world', 'BBC World', 'Sample title', 'Sample summary', 'https://example.com/story', '2026-04-15T10:00:00', 0)
            """
        )
        self.conn.execute(
            """
            INSERT INTO daily_briefs (id, language_code, source_key, source_name, title, summary, url, published_at, saved)
            VALUES (2, 'es', 'bbc_world_es', 'BBC Mundo', 'Titulo', 'Resumen', 'https://example.com/story', '2026-04-15T11:00:00', 0)
            """
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_save_brief_to_favorites_still_saves_when_translation_fails(self):
        with mock.patch.object(news_digest, "fetch_article_content", return_value="Paragraph one.\n\nParagraph two."):
            with mock.patch.object(news_digest, "to_bilingual_text", side_effect=RuntimeError("ssl eof")):
                row = news_digest.save_brief_to_favorites(self.conn, 1, language_code="en")

        self.assertIsNotNone(row)
        self.assertEqual(row["content_text"], "Paragraph one.\n\nParagraph two.")
        self.assertEqual(row["bilingual_text"], "Paragraph one.\n\nParagraph two.")
        metadata = row["metadata_json"]
        self.assertIn("translation_error", metadata)

    def test_save_brief_to_favorites_falls_back_to_summary_when_article_fetch_fails(self):
        with mock.patch.object(news_digest, "fetch_article_content", side_effect=RuntimeError("network down")):
            row = news_digest.save_brief_to_favorites(self.conn, 1, language_code="en")

        self.assertIsNotNone(row)
        self.assertIn("Sample title", row["content_text"])
        self.assertIn("Sample summary", row["content_text"])
        self.assertEqual(row["bilingual_text"], row["content_text"])
        self.assertIn("content_error", row["metadata_json"])

    def test_save_brief_to_favorites_returns_existing_article_for_duplicate_url(self):
        self.conn.execute(
            """
            INSERT INTO favorite_articles
            (brief_id, language_code, source_key, source_name, title, summary, url, published_at, content_text, bilingual_text)
            VALUES (99, 'en', 'bbc_world', 'BBC World', 'Old title', 'Old summary', 'https://example.com/story', '2026-04-14T11:00:00', 'Old article.', 'Old article.')
            """,
        )
        self.conn.commit()

        with mock.patch.object(news_digest, "fetch_article_content", side_effect=AssertionError("should not refetch duplicate URL")):
            row = news_digest.save_brief_to_favorites(self.conn, 1, language_code="en")

        self.assertEqual(row["brief_id"], 99)
        self.assertEqual(row["url"], "https://example.com/story")
        self.assertEqual(self.conn.execute("SELECT saved FROM daily_briefs WHERE id = 1").fetchone()["saved"], 1)

    def test_save_brief_to_favorites_treats_same_url_in_other_language_as_separate_article(self):
        with mock.patch.object(news_digest, "fetch_article_content", return_value="Hola.\n\nMundo."):
            with mock.patch.object(news_digest, "to_bilingual_text", return_value="Hola.\n你好\n\nMundo.\n世界"):
                row = news_digest.save_brief_to_favorites(self.conn, 2, language_code="es")

        self.assertEqual(row["language_code"], "es")
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) AS total FROM favorite_articles WHERE url = ?", ("https://example.com/story",)).fetchone()["total"],
            1,
        )

    def test_latest_briefs_filters_by_language(self):
        english = news_digest.latest_briefs(self.conn, language_code="en", limit=10)
        spanish = news_digest.latest_briefs(self.conn, language_code="es", limit=10)

        self.assertEqual([row["language_code"] for row in english], ["en"])
        self.assertEqual([row["language_code"] for row in spanish], ["es"])

    def test_ensure_schema_migrates_legacy_news_tables_to_language_aware_shape(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(
            """
            CREATE TABLE daily_briefs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              source_key TEXT NOT NULL,
              source_name TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              url TEXT NOT NULL UNIQUE,
              published_at TEXT NOT NULL DEFAULT '',
              fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              saved INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE favorite_articles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              brief_id INTEGER NOT NULL UNIQUE,
              source_key TEXT NOT NULL,
              source_name TEXT NOT NULL,
              title TEXT NOT NULL,
              summary TEXT NOT NULL DEFAULT '',
              url TEXT NOT NULL UNIQUE,
              published_at TEXT NOT NULL DEFAULT '',
              content_text TEXT NOT NULL DEFAULT '',
              bilingual_text TEXT NOT NULL DEFAULT '',
              metadata_json TEXT NOT NULL DEFAULT '{}',
              saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (brief_id) REFERENCES daily_briefs(id) ON DELETE CASCADE
            );

            INSERT INTO daily_briefs (id, source_key, source_name, title, summary, url, published_at, saved)
            VALUES (1, 'bbc_world', 'BBC World', 'Legacy brief', 'Legacy summary', 'https://example.com/legacy', '2026-04-15T10:00:00', 1);

            INSERT INTO favorite_articles
            (id, brief_id, source_key, source_name, title, summary, url, published_at, content_text, bilingual_text)
            VALUES (1, 1, 'bbc_world', 'BBC World', 'Legacy brief', 'Legacy summary', 'https://example.com/legacy', '2026-04-15T10:00:00', 'Legacy body', 'Legacy body');
            """
        )

        news_digest.ensure_schema(conn)

        brief = conn.execute("SELECT * FROM daily_briefs WHERE id = 1").fetchone()
        favorite = conn.execute("SELECT * FROM favorite_articles WHERE id = 1").fetchone()
        conn.close()

        self.assertEqual(brief["language_code"], "en")
        self.assertEqual(favorite["language_code"], "en")

if __name__ == "__main__":
    unittest.main()
