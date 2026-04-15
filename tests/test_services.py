import sqlite3
import shutil
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock
from uuid import uuid4

import app


class ServiceBoundaryTests(unittest.TestCase):
    def setUp(self):
        ignored_temp_root = Path(app.APP_ROOT) / ".worktrees"
        ignored_temp_root.mkdir(parents=True, exist_ok=True)
        self.temp_root_path = ignored_temp_root / f"test_services_{uuid4().hex}"
        self.temp_root_path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(self.temp_root_path, ignore_errors=True))
        self.db_path = self.temp_root_path / "test.db"
        self.db = app.FloatVocabDB(self.db_path)
        self.addCleanup(self.db.conn.close)

    def _seed_study_words(self):
        lexicon_id = self.db.create_lexicon("Study Boundary", "test")
        today = date.today().isoformat()
        for word in ["alpha", "beta", "gamma"]:
            self.db.conn.execute(
                """
                INSERT INTO words
                (lexicon_id, word, phonetic, meaning, example, next_review_date)
                VALUES (?, ?, '', ?, '', ?)
                """,
                (lexicon_id, word, f"{word} meaning", today),
            )
        self.db.conn.commit()
        plan = self.db.plan()
        self.db.save_plan(
            lexicon_id,
            plan["daily_new"],
            plan["target_date"] or (date.today() + timedelta(days=30)).isoformat(),
            plan["float_alpha"],
            plan["font_size"],
            plan["bg_color"],
            plan["widget_size"],
        )
        return lexicon_id

    def test_study_service_get_next_card_and_submit_review_persists_current_word_until_review(self):
        self._seed_study_words()

        service = app.StudyService(self.db)

        first = service.get_next_card()
        self.assertIsNotNone(first)
        self.assertEqual(self.db.plan()["current_word_id"], first.id)

        service.submit_review(first.id, 4)

        self.assertIsNone(self.db.plan()["current_word_id"])

    def test_settings_service_save_plan_rejects_invalid_target_date_format(self):
        service = app.SettingsService(self.db)

        with self.assertRaises(ValueError):
            service.save_plan(
                lexicon_id=1,
                daily_new=20,
                target_date="2026/04/15",
                alpha=0.88,
                font_size=26,
                bg_color="#FFFFFF",
                widget_size="medium",
            )

    def test_settings_service_save_plan_delegates_valid_values_after_validation(self):
        service = app.SettingsService(self.db)
        expected = {
            "lexicon_id": 7,
            "daily_new": 18,
            "target_date": "2026-04-15",
            "alpha": 0.92,
            "font_size": 24,
            "bg_color": "#FAFAFA",
            "widget_size": "large",
        }

        with mock.patch.object(self.db, "save_plan", return_value=None) as save_plan_mock:
            service.save_plan(**expected)

        save_plan_mock.assert_called_once_with(
            expected["lexicon_id"],
            expected["daily_new"],
            expected["target_date"],
            expected["alpha"],
            expected["font_size"],
            expected["bg_color"],
            expected["widget_size"],
        )

    def test_news_service_save_brief_to_favorites_delegates_with_sqlite_connection(self):
        sentinel_conn = mock.Mock(spec=sqlite3.Connection)
        connection_context = mock.MagicMock()
        connection_context.__enter__.return_value = sentinel_conn
        connection_factory = mock.Mock(return_value=connection_context)

        with mock.patch.object(app.news_digest, "save_brief_to_favorites", return_value={"saved": True}) as save_mock:
            service = app.NewsService(self.db_path, connection_factory=connection_factory)
            result = service.save_brief_to_favorites(brief_id=1)

        self.assertEqual(result, {"saved": True})
        connection_factory.assert_called_once_with(self.db_path)
        connection_context.__enter__.assert_called_once_with()
        connection_context.__exit__.assert_called_once()
        save_mock.assert_called_once()
        conn_arg, brief_id_arg = save_mock.call_args.args
        self.assertIs(conn_arg, sentinel_conn)
        self.assertEqual(brief_id_arg, 1)

    def test_enrichment_service_enrich_examples_forwards_result_shape(self):
        service = app.EnrichmentService(self.db_path)
        payload = {"processed": 2, "updated": 1, "skipped": 1, "failures": []}

        with mock.patch.object(app, "enrich_database", return_value=payload) as enrich_mock:
            result = service.enrich_examples(lexicon_id=7, limit=5, refresh=True)

        self.assertEqual(result, payload)
        enrich_mock.assert_called_once_with(self.db_path, limit=5, refresh=True, lexicon_id=7)


if __name__ == "__main__":
    unittest.main()
