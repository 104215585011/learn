import unittest
from datetime import date, timedelta
from pathlib import Path
import shutil

import app


class StudyStateTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(app.APP_ROOT) / "tests" / "_tmp_study_state"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.temp_root / "test.db"
        self.db = app.FloatVocabDB(self.db_path)
        self.lexicon_id = self.db.create_lexicon("Resume Test", "test")
        today = date.today().isoformat()
        for word in ["alpha", "beta", "gamma"]:
            self.db.conn.execute(
                """
                INSERT INTO words
                (lexicon_id, word, phonetic, meaning, example, next_review_date)
                VALUES (?, ?, '', ?, '', ?)
                """,
                (self.lexicon_id, word, f"{word} meaning", today),
            )
        self.db.conn.commit()
        plan = self.db.plan()
        self.db.save_plan(
            self.lexicon_id,
            plan["daily_new"],
            plan["target_date"] or (date.today() + timedelta(days=30)).isoformat(),
            plan["float_alpha"],
            plan["font_size"],
            plan["bg_color"],
            plan["widget_size"],
        )

    def tearDown(self):
        self.db.conn.close()
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)

    def test_plan_schema_tracks_current_word(self):
        self.assertIn("current_word_id", self.db.plan().keys())

    def test_current_word_persists_until_reviewed(self):
        first = self.db.next_card()
        self.assertIsNotNone(first)
        self.assertEqual(self.db.plan()["current_word_id"], first.id)

        self.db.conn.close()
        self.db = app.FloatVocabDB(self.db_path)

        resumed = self.db.next_card()
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.id, first.id)

        self.db.review(resumed.id, 4)
        self.assertIsNone(self.db.plan()["current_word_id"])

        next_card = self.db.next_card()
        self.assertIsNotNone(next_card)
        self.assertNotEqual(next_card.id, resumed.id)


if __name__ == "__main__":
    unittest.main()
