from __future__ import annotations

from datetime import datetime

class SettingsService:
    def __init__(self, db):
        self.db = db

    def get_plan_settings(self):
        return self.db.plan()

    def list_supported_languages(self):
        return self.db.supported_languages()

    def switch_language(self, language_code: str):
        supported_codes = {code for code, _label in self.db.supported_languages()}
        if language_code not in supported_codes:
            raise ValueError(f"unsupported language_code: {language_code}")
        return self.db.set_current_language(language_code)

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
    ):
        parsed_target_date = datetime.strptime(target_date, "%Y-%m-%d")
        if parsed_target_date.strftime("%Y-%m-%d") != target_date:
            raise ValueError("target_date must use YYYY-MM-DD format")
        args = (
            lexicon_id,
            daily_new,
            target_date,
            alpha,
            font_size,
            bg_color,
            widget_size,
        )
        if current_language_code is None:
            return self.db.save_plan(*args)
        return self.db.save_plan(*args, current_language_code=current_language_code)

    def save_float_style(self, alpha: float, font_size: int, bg_color: str, widget_size: str):
        return self.db.save_float_style(alpha, font_size, bg_color, widget_size)

    def set_global_translation_enabled(self, enabled: bool):
        return self.db.plan_repository.set_global_translation_enabled(enabled)

    def get_user_profile(self):
        return self.db.user_profile()

    def save_user_profile(self, display_name: str, avatar_url: str = "", bio: str = ""):
        normalized_name = (display_name or "").strip()
        if not normalized_name:
            raise ValueError("display_name is required")
        return self.db.save_user_profile(normalized_name, (avatar_url or "").strip(), (bio or "").strip())

    def get_app_settings(self):
        return self.db.app_settings()

    def save_app_settings(
        self,
        *,
        theme: str,
        default_window_width: int,
        default_window_height: int,
        launch_at_startup: bool,
    ):
        if theme not in {"light", "dark", "system"}:
            raise ValueError("theme must be light, dark, or system")
        if default_window_width < 900 or default_window_height < 600:
            raise ValueError("default window size is too small")
        return self.db.save_app_settings(
            theme=theme,
            default_window_width=default_window_width,
            default_window_height=default_window_height,
            launch_at_startup=launch_at_startup,
        )
