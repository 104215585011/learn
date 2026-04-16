from __future__ import annotations

from datetime import datetime


class SettingsService:
    def __init__(self, db):
        self.db = db

    def get_plan_settings(self):
        return self.db.plan()

    def save_plan(
        self,
        lexicon_id: int,
        daily_new: int,
        target_date: str,
        alpha: float,
        font_size: int,
        bg_color: str,
        widget_size: str,
    ):
        parsed_target_date = datetime.strptime(target_date, "%Y-%m-%d")
        if parsed_target_date.strftime("%Y-%m-%d") != target_date:
            raise ValueError("target_date must use YYYY-MM-DD format")
        return self.db.save_plan(lexicon_id, daily_new, target_date, alpha, font_size, bg_color, widget_size)

    def save_float_style(self, alpha: float, font_size: int, bg_color: str, widget_size: str):
        return self.db.save_float_style(alpha, font_size, bg_color, widget_size)
