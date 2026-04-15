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
            INSERT INTO daily_briefs (id, source_key, source_name, title, summary, url, published_at, saved)
            VALUES (1, 'bbc_world', 'BBC World', 'Sample title', 'Sample summary', 'https://example.com/story', '2026-04-15T10:00:00', 0)
            """
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_save_brief_to_favorites_still_saves_when_translation_fails(self):
        with mock.patch.object(news_digest, "fetch_article_content", return_value="Paragraph one.\n\nParagraph two."):
            with mock.patch.object(news_digest, "to_bilingual_text", side_effect=RuntimeError("ssl eof")):
                row = news_digest.save_brief_to_favorites(self.conn, 1)

        self.assertIsNotNone(row)
        self.assertEqual(row["content_text"], "Paragraph one.\n\nParagraph two.")
        self.assertEqual(row["bilingual_text"], "Paragraph one.\n\nParagraph two.")
        metadata = row["metadata_json"]
        self.assertIn("translation_error", metadata)

    def test_save_brief_to_favorites_falls_back_to_summary_when_article_fetch_fails(self):
        with mock.patch.object(news_digest, "fetch_article_content", side_effect=RuntimeError("network down")):
            row = news_digest.save_brief_to_favorites(self.conn, 1)

        self.assertIsNotNone(row)
        self.assertIn("Sample title", row["content_text"])
        self.assertIn("Sample summary", row["content_text"])
        self.assertEqual(row["bilingual_text"], row["content_text"])
        self.assertIn("content_error", row["metadata_json"])


if __name__ == "__main__":
    unittest.main()
