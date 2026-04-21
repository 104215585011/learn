from __future__ import annotations

import sqlite3
from datetime import date

from floatvocab.db import DEFAULT_LANGUAGE_CODE


SUPPORTED_LANGUAGES = (
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("ko", "Korean"),
    ("ja", "Japanese"),
    ("it", "Italian"),
    ("id", "Indonesian"),
    ("ru", "Russian"),
    ("ar", "Arabic"),
    ("pt", "Portuguese"),
)


class LexiconRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_supported_languages(self):
        return SUPPORTED_LANGUAGES

    def create_lexicon(
        self,
        name: str,
        source: str = "custom",
        language_code: str = DEFAULT_LANGUAGE_CODE,
    ) -> int:
        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO lexicons (name, language_code, source) VALUES (?, ?, ?)",
            (name, language_code, source),
        )
        self.conn.commit()
        if cursor.rowcount:
            return int(cursor.lastrowid)
        row = self.conn.execute(
            "SELECT id FROM lexicons WHERE name = ? AND language_code = ?",
            (name, language_code),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"failed to create lexicon: {language_code}/{name}")
        return int(row["id"])

    def list_lexicons(self, language_code: str | None = None):
        query = """
        SELECT l.*,
          COUNT(w.id) AS total,
          SUM(CASE WHEN w.status = 'mastered' THEN 1 ELSE 0 END) AS mastered
        FROM lexicons l
        LEFT JOIN words w ON w.lexicon_id = l.id
        """
        params: tuple[object, ...] = ()
        if language_code:
            query += " WHERE l.language_code = ?"
            params = (language_code,)
        query += " GROUP BY l.id ORDER BY l.created_at"
        return self.conn.execute(query, params).fetchall()

    def get_lexicon(self, lexicon_id: int):
        return self.conn.execute("SELECT * FROM lexicons WHERE id = ?", (lexicon_id,)).fetchone()

    def update_lexicon(self, lexicon_id: int, name: str, language_code: str):
        self.conn.execute(
            "UPDATE lexicons SET name = ?, language_code = ? WHERE id = ?",
            (name, language_code, lexicon_id),
        )
        self.conn.commit()
        return self.get_lexicon(lexicon_id)

    def delete_lexicon(self, lexicon_id: int) -> None:
        self.conn.execute("DELETE FROM words WHERE lexicon_id = ?", (lexicon_id,))
        self.conn.execute("DELETE FROM lexicons WHERE id = ?", (lexicon_id,))
        self.conn.commit()

    def first_lexicon_for_language(self, language_code: str):
        return self.conn.execute(
            "SELECT * FROM lexicons WHERE language_code = ? ORDER BY created_at, id LIMIT 1",
            (language_code,),
        ).fetchone()

    def import_word_rows(
        self,
        lexicon_name: str,
        rows: list[dict],
        source: str = "import",
        language_code: str = DEFAULT_LANGUAGE_CODE,
    ) -> int:
        lexicon_id = self.create_lexicon(lexicon_name, source, language_code)
        today = date.today().isoformat()
        imported = 0
        for row in rows:
            word = (row.get("word") or "").strip()
            meaning = (row.get("meaning") or "").strip()
            if not word or not meaning:
                continue
            exists = self.conn.execute(
                "SELECT 1 FROM words WHERE lexicon_id = ? AND word = ?",
                (lexicon_id, word),
            ).fetchone()
            if exists:
                continue
            self.conn.execute(
                """
                INSERT INTO words
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
