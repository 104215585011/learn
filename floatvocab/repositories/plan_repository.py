from __future__ import annotations

import sqlite3

from floatvocab.db import DEFAULT_LANGUAGE_CODE


class PlanRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def fetch_plan(self):
        return self.conn.execute("SELECT * FROM plans WHERE id = 1").fetchone()

    def save_plan(
        self,
        lexicon_id: int,
        daily_new: int,
        target_date: str,
        alpha: float,
        font_size: int,
        bg_color: str,
        widget_size: str,
        current_language_code: str | None = None,
    ) -> None:
        current_plan = self.fetch_plan()
        current_word_id = current_plan["current_word_id"] if "current_word_id" in current_plan.keys() else None
        next_language_code = current_language_code or current_plan["current_language_code"] or DEFAULT_LANGUAGE_CODE
        if current_plan["lexicon_id"] != lexicon_id:
            current_word_id = None
        self.conn.execute(
            """
            UPDATE plans
            SET lexicon_id = ?, daily_new = ?, target_date = ?, float_alpha = ?,
                font_size = ?, bg_color = ?, widget_size = ?, current_word_id = ?,
                current_language_code = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (
                lexicon_id,
                daily_new,
                target_date,
                alpha,
                font_size,
                bg_color,
                widget_size,
                current_word_id,
                next_language_code,
            ),
        )
        self.conn.commit()

    def save_float_style(self, alpha: float, font_size: int, bg_color: str, widget_size: str) -> None:
        self.conn.execute(
            """
            UPDATE plans
            SET float_alpha = ?, font_size = ?, bg_color = ?, widget_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (alpha, font_size, bg_color, widget_size),
        )
        self.conn.commit()

    def set_current_language(self, language_code: str, lexicon_id: int | None) -> None:
        current_plan = self.fetch_plan()
        current_word_id = current_plan["current_word_id"] if "current_word_id" in current_plan.keys() else None
        if current_plan["lexicon_id"] != lexicon_id:
            current_word_id = None
        self.conn.execute(
            """
            UPDATE plans
            SET current_language_code = ?, lexicon_id = ?, current_word_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (language_code, lexicon_id, current_word_id),
        )
        self.conn.commit()

    def set_global_translation_enabled(self, enabled: bool) -> None:
        self.conn.execute(
            """
            UPDATE plans
            SET global_translation_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (1 if enabled else 0,),
        )
        self.conn.commit()
