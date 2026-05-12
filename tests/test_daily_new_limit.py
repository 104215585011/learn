import shutil
import unittest
from datetime import date, timedelta
from pathlib import Path

import app


class DailyNewLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(app.APP_ROOT) / "tests" / "_tmp_daily_new_limit"
        if self.temp_root.exists():
            shutil.rmtree(self.temp_root)
        self.temp_root.mkdir(parents=True, exist_ok=True)
        self.db = app.FloatVocabDB(self.temp_root / "test.db")
        self.lexicon_id = self.db.create_lexicon("Daily New Limit", "test")
        self.today = date.today().isoformat()
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()
        plan = self.db.plan()
        self.db.save_plan(
            self.lexicon_id,
            3,
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

    def add_word(
        self,
        word,
        *,
        next_review_date=None,
        seen_count=0,
        repetitions=0,
        status="new",
    ):
        self.db.conn.execute(
            """
            INSERT INTO words
            (lexicon_id, word, phonetic, meaning, example, next_review_date, seen_count, repetitions, status)
            VALUES (?, ?, '', ?, '', ?, ?, ?, ?)
            """,
            (
                self.lexicon_id,
                word,
                f"{word} meaning",
                next_review_date or self.today,
                seen_count,
                repetitions,
                status,
            ),
        )
        self.db.conn.commit()

    def set_new_seen_today(self, count):
        self.db.conn.execute(
            """
            INSERT INTO daily_stats (day, reviewed, known, unknown, new_seen)
            VALUES (?, 0, 0, 0, ?)
            ON CONFLICT(day) DO UPDATE SET new_seen = excluded.new_seen
            """,
            (self.today, count),
        )
        self.db.conn.commit()

    def test_daily_new_limit_stops_unseen_words_after_limit(self):
        for index in range(10):
            self.add_word(f"new-{index}")

        shown = []
        for _ in range(10):
            card = self.db.next_card()
            if card is None:
                break
            shown.append(card.word)
            self.db.review(card.id, 4)

        self.assertEqual(len(shown), 3)
        self.assertIsNone(self.db.next_card())
        stats = self.db.conn.execute("SELECT new_seen FROM daily_stats WHERE day = ?", (self.today,)).fetchone()
        self.assertEqual(stats["new_seen"], 3)

    def test_due_reviews_continue_after_new_limit_is_reached(self):
        self.set_new_seen_today(3)
        self.add_word("unseen-new")
        self.add_word("due-review", seen_count=2, repetitions=1, status="fuzzy")

        card = self.db.next_card()

        self.assertIsNotNone(card)
        self.assertEqual(card.word, "due-review")

    def test_next_card_returns_none_when_new_limit_and_reviews_are_done(self):
        self.set_new_seen_today(3)
        self.add_word("unseen-new")
        self.add_word("future-review", next_review_date=self.tomorrow, seen_count=2, repetitions=1, status="fuzzy")

        self.assertIsNone(self.db.next_card())


if __name__ == "__main__":
    unittest.main()
