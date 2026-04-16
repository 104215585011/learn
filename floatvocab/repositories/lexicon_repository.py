from __future__ import annotations

import sqlite3
from datetime import date


class LexiconRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_lexicon(self, name: str, source: str = "custom") -> int:
        cursor = self.conn.execute("INSERT OR IGNORE INTO lexicons (name, source) VALUES (?, ?)", (name, source))
        self.conn.commit()
        if cursor.rowcount:
            return int(cursor.lastrowid)
        row = self.conn.execute("SELECT id FROM lexicons WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise RuntimeError(f"failed to create lexicon: {name}")
        return int(row["id"])

    def list_lexicons(self):
        return self.conn.execute(
            """
            SELECT l.*,
              COUNT(w.id) AS total,
              SUM(CASE WHEN w.status = 'mastered' THEN 1 ELSE 0 END) AS mastered
            FROM lexicons l
            LEFT JOIN words w ON w.lexicon_id = l.id
            GROUP BY l.id
            ORDER BY l.created_at
            """
        ).fetchall()

    def import_word_rows(self, lexicon_name: str, rows: list[dict], source: str = "import") -> int:
        lexicon_id = self.create_lexicon(lexicon_name, source)
        today = date.today().isoformat()
        imported = 0
        for row in rows:
            word = (row.get("word") or "").strip()
            meaning = (row.get("meaning") or "").strip()
            if not word or not meaning:
                continue
            self.conn.execute(
                """
                INSERT OR IGNORE INTO words
                (lexicon_id, word, phonetic, meaning, example, next_review_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lexicon_id,
                    word,
                    (row.get("phonetic") or "").strip(),
                    meaning,
                    (row.get("example") or "").strip(),
                    today,
                ),
            )
            imported += 1
        self.conn.commit()
        return imported

    def recent_words(self, lexicon_id: int, limit: int = 80):
        return self.conn.execute(
            """
            SELECT word, meaning, status
            FROM words
            WHERE lexicon_id = ?
            ORDER BY updated_at DESC, id
            LIMIT ?
            """,
            (lexicon_id, limit),
        ).fetchall()
