from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import date, timedelta


class StudyRepository:
    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        calculate_srs: Callable[[sqlite3.Row, int], dict],
        row_to_card: Callable[[sqlite3.Row], object],
    ):
        self.conn = conn
        self.calculate_srs = calculate_srs
        self.row_to_card = row_to_card

    def next_card(self):
        plan = self.conn.execute("SELECT * FROM plans WHERE id = 1").fetchone()
        if not plan or not plan["lexicon_id"]:
            return None
        lexicon_id = plan["lexicon_id"]
        current_word_id = plan["current_word_id"] if "current_word_id" in plan.keys() else None
        if current_word_id:
            current_card = self.conn.execute(
                """
                SELECT w.*, l.name AS lexicon_name
                FROM words w JOIN lexicons l ON l.id = w.lexicon_id
                WHERE w.id = ? AND w.lexicon_id = ? AND w.status != 'mastered'
                """,
                (current_word_id, lexicon_id),
            ).fetchone()
            if current_card:
                return self.row_to_card(current_card)
            self.conn.execute("UPDATE plans SET current_word_id = NULL WHERE id = 1")
            self.conn.commit()
        today = date.today().isoformat()
        card = self.conn.execute(
            """
            SELECT w.*, l.name AS lexicon_name
            FROM words w JOIN lexicons l ON l.id = w.lexicon_id
            WHERE w.lexicon_id = ?
              AND w.status != 'mastered'
            ORDER BY
              CASE WHEN w.next_review_date <= ? THEN 0 ELSE 1 END,
              CASE WHEN w.repetitions = 0 THEN 1 ELSE 0 END,
              w.next_review_date,
              w.seen_count,
              w.id
            LIMIT 1
            """,
            (lexicon_id, today),
        ).fetchone()
        if card:
            self.conn.execute("UPDATE plans SET current_word_id = ? WHERE id = 1", (card["id"],))
            self.conn.commit()
        return self.row_to_card(card) if card else None

    def review(self, word_id: int, rating: int) -> None:
        row = self.conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
        if not row:
            return
        old_interval = row["interval_days"]
        next_state = self.calculate_srs(row, rating)
        status = "mastered" if rating >= 4 and next_state["repetitions"] >= 3 else "fuzzy" if rating >= 3 else "new"
        self.conn.execute(
            """
            UPDATE words
            SET status = ?, next_review_date = ?, interval_days = ?, repetitions = ?,
                ease_factor = ?, seen_count = seen_count + 1,
                correct_count = correct_count + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                next_state["next_review_date"],
                next_state["interval_days"],
                next_state["repetitions"],
                next_state["ease_factor"],
                1 if rating >= 3 else 0,
                word_id,
            ),
        )
        self.conn.execute(
            "INSERT INTO reviews (word_id, rating, old_interval_days, new_interval_days) VALUES (?, ?, ?, ?)",
            (word_id, rating, old_interval, next_state["interval_days"]),
        )
        today = date.today().isoformat()
        self.conn.execute(
            """
            INSERT INTO daily_stats (day, reviewed, known, unknown, new_seen)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
              reviewed = reviewed + 1,
              known = known + excluded.known,
              unknown = unknown + excluded.unknown,
              new_seen = new_seen + excluded.new_seen
            """,
            (today, 1 if rating >= 3 else 0, 1 if rating < 3 else 0, 1 if row["seen_count"] == 0 else 0),
        )
        self.conn.execute("UPDATE plans SET current_word_id = NULL WHERE id = 1 AND current_word_id = ?", (word_id,))
        self.conn.commit()

    def stats(self):
        plan = self.conn.execute("SELECT * FROM plans WHERE id = 1").fetchone()
        if not plan or not plan["lexicon_id"]:
            return {}
        summary = self.conn.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN status = 'mastered' THEN 1 ELSE 0 END) AS mastered,
              SUM(CASE WHEN status = 'fuzzy' THEN 1 ELSE 0 END) AS fuzzy,
              SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS fresh,
              SUM(CASE WHEN next_review_date <= date('now', 'localtime') AND status != 'mastered' THEN 1 ELSE 0 END) AS due
            FROM words
            WHERE lexicon_id = ?
            """,
            (plan["lexicon_id"],),
        ).fetchone()
        days = self.conn.execute(
            "SELECT * FROM daily_stats WHERE day >= ? ORDER BY day",
            ((date.today() - timedelta(days=29)).isoformat(),),
        ).fetchall()
        return {"summary": summary, "days": days}

    def missing_examples_count(self, lexicon_id: int | None = None) -> int:
        if lexicon_id:
            row = self.conn.execute(
                "SELECT COUNT(*) AS total FROM words WHERE lexicon_id = ? AND (example IS NULL OR TRIM(example) = '')",
                (lexicon_id,),
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) AS total FROM words WHERE example IS NULL OR TRIM(example) = ''").fetchone()
        return int(row["total"] or 0)
