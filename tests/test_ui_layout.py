import shutil
import sqlite3
import time
import tkinter.font as tkfont
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import app


class AppLayoutTests(unittest.TestCase):
    def test_build_dashboard_summary_text_prefers_due_and_mastery_snapshot(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.study_service = mock.Mock()
        ui.study_service.get_study_stats.return_value = {
            "summary": {
                "total": 120,
                "mastered": 84,
                "due": 18,
            }
        }

        summary = ui.build_dashboard_summary_text()

        self.assertEqual(summary, "今日待复习 18 个，已掌握 70%")

    def test_build_dashboard_summary_text_uses_empty_state_when_stats_missing(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.study_service = mock.Mock()
        ui.study_service.get_study_stats.return_value = None

        summary = ui.build_dashboard_summary_text()

        self.assertEqual(summary, "今天还没有学习记录，先开始一轮复习。")

    def test_build_dashboard_badge_items_returns_today_snapshot_cards(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.study_service = mock.Mock()
        ui.study_service.get_study_stats.return_value = {
            "summary": {
                "total": 120,
                "mastered": 84,
                "due": 18,
            }
        }
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "current_language_code": "en",
            "lexicon_id": 7,
        }
        ui.settings_service.list_supported_languages.return_value = [("en", "英语")]
        ui.db = mock.Mock()
        ui.db.get_lexicon.return_value = {"id": 7, "name": "考研词汇"}

        badges = ui.build_dashboard_badge_items()

        self.assertEqual(
            badges,
            [("今日待复习", "18"), ("已掌握", "70%"), ("当前词库", "考研词汇")],
        )

    def test_build_dashboard_badge_items_supports_row_like_plan_objects(self):
        class RowLikePlan:
            def __getitem__(self, key):
                values = {
                    "current_language_code": "en",
                    "lexicon_id": 9,
                }
                return values[key]

        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.study_service = mock.Mock()
        ui.study_service.get_study_stats.return_value = {
            "summary": {
                "total": 40,
                "mastered": 10,
                "due": 6,
            }
        }
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = RowLikePlan()
        ui.db = mock.Mock()
        ui.db.get_lexicon.return_value = {"id": 9, "name": "基础词库"}

        badges = ui.build_dashboard_badge_items()

        self.assertEqual(
            badges,
            [("今日待复习", "6"), ("已掌握", "25%"), ("当前词库", "基础词库")],
        )

    def test_build_dashboard_intro_text_mentions_today_focus(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        self.assertEqual(
            ui.build_dashboard_intro_text(),
            "今天先完成复习，再决定是否调整计划和样式。",
        )

    def test_build_dashboard_focus_steps_returns_three_startup_actions(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.study_service = mock.Mock()
        ui.study_service.get_study_stats.return_value = {
            "summary": {
                "total": 120,
                "mastered": 84,
                "due": 18,
            }
        }
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "current_language_code": "en",
            "lexicon_id": 7,
            "daily_new": 20,
        }
        ui.db = mock.Mock()
        ui.db.get_lexicon.return_value = {"id": 7, "name": "考研词汇"}

        steps = ui.build_dashboard_focus_steps()

        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0][0], "01")
        self.assertIn("18 个待复习", steps[0][2])
        self.assertIn("考研词汇", steps[1][2])
        self.assertIn("20 个新词", steps[1][2])
        self.assertIn("悬浮窗", steps[2][2])

    def test_build_dashboard_focus_steps_supports_missing_lexicon(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.study_service = mock.Mock()
        ui.study_service.get_study_stats.return_value = None
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "current_language_code": "en",
            "lexicon_id": None,
            "daily_new": 12,
        }
        ui.db = mock.Mock()

        steps = ui.build_dashboard_focus_steps()

        self.assertIn("0 个待复习", steps[0][2])
        self.assertIn("先选一个词库", steps[1][2])

    def test_build_plan_snapshot_items_summarizes_language_lexicon_and_target(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "current_language_code": "en",
            "lexicon_id": 7,
            "daily_new": 20,
            "target_date": "2026-05-20",
        }
        ui.settings_service.list_supported_languages.return_value = [("en", "英语"), ("ja", "日语")]
        ui.db = mock.Mock()
        ui.db.get_lexicon.return_value = {"id": 7, "name": "考研词汇"}

        items = ui.build_plan_snapshot_items()

        self.assertEqual(
            items,
            [("学习语言", "英语"), ("当前词库", "考研词汇"), ("学习节奏", "20 个/天 · 截止 2026-05-20")],
        )

    def test_build_style_snapshot_items_formats_float_window_preferences(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "float_alpha": 0.88,
            "font_size": 26,
            "bg_color": "#F7FAF5",
            "widget_size": "medium",
        }

        items = ui.build_style_snapshot_items()

        self.assertEqual(
            items,
            [("透明度", "88%"), ("字号", "26 px"), ("卡片尺寸", "MEDIUM · #F7FAF5")],
        )

    def test_build_stats_progress_text_summarizes_completion_snapshot(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        text = ui.build_stats_progress_text(
            {
                "summary": {
                    "total": 120,
                    "mastered": 84,
                    "fuzzy": 9,
                    "due": 18,
                }
            }
        )

        self.assertEqual(text, "完成度 70% · 已掌握 84/120 · 模糊 9 · 今日待复习 18")

    def test_build_stats_spotlight_items_returns_dashboard_cards(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        items = ui.build_stats_spotlight_items(
            {
                "summary": {
                    "total": 120,
                    "mastered": 84,
                    "fuzzy": 9,
                    "due": 18,
                },
                "days": [
                    {"day": "2026-04-17", "reviewed": 12},
                    {"day": "2026-04-18", "reviewed": 8},
                    {"day": "2026-04-19", "reviewed": 14},
                ],
            }
        )

        self.assertEqual(
            items,
            [("今日待复习", "18"), ("模糊词", "9"), ("活跃天数", "3/30")],
        )

    def test_build_heatmap_caption_text_summarizes_recent_streak(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        caption = ui.build_heatmap_caption_text(
            {
                "days": [
                    {"day": "2026-04-17", "reviewed": 12},
                    {"day": "2026-04-18", "reviewed": 8},
                    {"day": "2026-04-19", "reviewed": 14},
                ]
            }
        )

        self.assertEqual(caption, "最近 30 天累计复习 34 次，有记录的学习日是 3 天。")

    def test_build_words_overview_text_summarizes_language_and_lexicon(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "current_language_code": "en",
            "lexicon_id": 7,
        }
        ui.settings_service.list_supported_languages.return_value = [("en", "英语")]
        ui.db = mock.Mock()
        ui.db.get_lexicon.return_value = {"id": 7, "name": "考研词汇"}

        text = ui.build_words_overview_text()

        self.assertEqual(text, "当前正在浏览英语 · 考研词汇，最近更新的词条会显示在这里。")

    def test_build_news_overview_items_summarizes_language_and_actions(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)
        ui.settings_service = mock.Mock()
        ui.settings_service.get_plan_settings.return_value = {
            "current_language_code": "ja",
        }
        ui.settings_service.list_supported_languages.return_value = [("ja", "日语")]

        items = ui.build_news_overview_items()

        self.assertEqual(
            items,
            [("当前语言", "日语"), ("内容节奏", "最新 10 篇"), ("操作入口", "收藏并翻译")],
        )

    def test_build_words_action_hint_encourages_fast_browsing(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        self.assertEqual(
            ui.build_words_action_hint(),
            "切换词库后列表会立刻刷新，适合快速扫一遍最近新增或刚复习过的词条。",
        )

    def test_build_news_action_hint_guides_refresh_and_collect_flow(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        self.assertEqual(
            ui.build_news_action_hint(),
            "先刷新，再选中条目预览；觉得合适就直接收藏并翻译。",
        )

    def test_build_words_tab_title_uses_language_name(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        self.assertEqual(ui.build_words_tab_title("英语"), "英语 词库概览")

    def test_build_metric_items_returns_due_mastered_and_total_counts(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        metrics = ui.build_metric_items(
            {
                "summary": {
                    "due": 7,
                    "mastered": 22,
                    "total": 40,
                }
            }
        )

        self.assertEqual(
            metrics,
            [("今日待复习", "7"), ("已掌握", "22"), ("总词数", "40")],
        )

    def test_build_heatmap_legend_items_returns_progressive_levels(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        legend = ui.build_heatmap_legend_items()

        self.assertEqual(
            legend,
            [
                ("较少", app.THEME["heat_0"]),
                ("稳定", app.THEME["heat_1"]),
                ("投入", app.THEME["heat_2"]),
                ("高强度", app.THEME["heat_3"]),
            ],
        )

    def test_format_brief_preview_includes_structured_metadata_and_state(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        preview = ui.format_brief_preview(
            {
                "title": "Morning Brief",
                "summary": "Key updates for today.",
                "source_name": "Reuters",
                "published_at": "2026-04-19T08:30:00",
                "saved": 1,
                "url": "https://example.com/brief",
            }
        )

        self.assertIn("Morning Brief", preview)
        self.assertIn("Reuters", preview)
        self.assertIn("已收藏", preview)
        self.assertIn("双击条目", preview)

    def test_build_brief_preview_parts_returns_layered_content(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        title, meta, summary, footer = ui.build_brief_preview_parts(
            {
                "title": "Morning Brief",
                "summary": "Key updates for today.",
                "source_name": "Reuters",
                "published_at": "2026-04-19T08:30:00",
                "saved": 0,
                "url": "https://example.com/brief",
            }
        )

        self.assertEqual(title, "Morning Brief")
        self.assertIn("Reuters", meta)
        self.assertIn("可收藏并翻译", meta)
        self.assertEqual(summary, "Key updates for today.")
        self.assertIn("https://example.com/brief", footer)

    def test_build_news_titles_for_language_uses_reading_first_labels(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        latest_title, favorite_title = ui.build_news_titles_for_language("英语")

        self.assertEqual(latest_title, "英语 最新阅读")
        self.assertEqual(favorite_title, "英语 收藏夹")

    def test_build_lexicon_state_text_returns_actionable_copy(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        self.assertEqual(
            ui.build_lexicon_state_text(True),
            "当前语言下已有词库，可以直接继续学习。",
        )
        self.assertEqual(
            ui.build_lexicon_state_text(False),
            "这个语言下还没有词库，先导入一个词包再开始。",
        )

    def test_build_brief_empty_state_distinguishes_empty_vs_unconfigured(self):
        ui = app.FloatVocabApp.__new__(app.FloatVocabApp)

        title, meta, summary, footer = ui.build_brief_empty_state(has_lexicons=False)
        self.assertIn("还没有新内容", title)
        self.assertIn("没有配置日报源", meta)
        self.assertIn("没有配置日报源", summary)
        self.assertIn("先导入词库", footer)

        title, meta, summary, footer = ui.build_brief_empty_state(has_lexicons=True)
        self.assertIn("还没有新内容", title)
        self.assertIn("稍后刷新", footer)
        self.assertEqual(meta, "这个语言还没有配置日报源，或者今天还没有抓到新内容。")
        self.assertEqual(summary, "这个语言还没有配置日报源，或者今天还没有抓到新内容。")

    def test_floating_window_header_text_uses_card_presence(self):
        floating = app.FloatingWindow.__new__(app.FloatingWindow)
        floating.card = None
        self.assertEqual(floating.build_header_text(), "FloatVocab · 准备开始")

        floating.card = app.WordCard(
            id=1,
            word="abandon",
            phonetic="/test/",
            meaning="放弃",
            example="Example",
            status="new",
            lexicon_name="test",
        )
        self.assertEqual(floating.build_header_text(), "FloatVocab · 当前学习卡")

    def test_floating_window_header_subtitle_changes_with_card_state(self):
        floating = app.FloatingWindow.__new__(app.FloatingWindow)
        floating.card = None
        floating.flipped = False
        self.assertEqual(floating.build_header_subtitle(), "拖动卡片开始今天的复习。")

        floating.card = app.WordCard(
            id=1,
            word="abandon",
            phonetic="/test/",
            meaning="放弃",
            example="Example",
            status="new",
            lexicon_name="test",
        )
        self.assertEqual(floating.build_header_subtitle(), "正面 · 点击翻面查看释义。")

        floating.flipped = True
        self.assertEqual(floating.build_header_subtitle(), "释义面 · 左右键快速判断。")

    def test_floating_window_shortcut_hint_is_compact(self):
        floating = app.FloatingWindow.__new__(app.FloatingWindow)

        self.assertEqual(
            floating.build_shortcut_hint(),
            "快捷键：Space 翻面 · ← 不认识 · → 认识",
        )

    def test_floating_window_flipped_side_keeps_meaning_visible(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/test/",
                meaning="放弃；抛弃",
                example="Example sentence",
                status="new",
                lexicon_name="test",
            )
            ui.float_window.flipped = True
            ui.float_window.apply_style()
            ui.float_window.render()

            visible_text = "\n".join(
                [ui.float_window.word_label.cget("text"), ui.float_window.detail_label.cget("text")]
            )
            self.assertIn("放弃", visible_text)
        finally:
            ui.close()

    def test_floating_window_flipped_side_keeps_word_as_title_for_short_meaning(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 28, "#F7FAF5", "large")
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/test/",
                meaning="放弃；抛弃",
                example="Example sentence",
                status="new",
                lexicon_name="test",
            )
            ui.float_window.flipped = True
            ui.float_window.apply_style()
            ui.float_window.render()

            self.assertEqual(ui.float_window.word_label.cget("text"), "abandon")
            self.assertIn("放弃", ui.float_window.detail_label.cget("text"))
        finally:
            ui.close()

    def test_main_window_exposes_brand_header_and_today_workbench(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertEqual(ui.hero_title_label.cget("text"), "FloatVocab")
            self.assertIn("安静", ui.hero_body_label.cget("text"))
            self.assertFalse(hasattr(ui, "hero_summary_label"))
            self.assertFalse(hasattr(ui, "hero_intro_label"))
            self.assertEqual(ui.style_box_title_label.cget("text"), "阅读外观")
            self.assertEqual(ui.stats_box_title_label.cget("text"), "学习状态")
            self.assertFalse(hasattr(ui, "hero_badge_value_labels"))

            tab_labels = [ui.content_notebook.tab(tab_id, "text") for tab_id in ui.content_notebook.tabs()]
            self.assertEqual(tab_labels[0], "工作台")
            self.assertTrue(any("词库概览" in label for label in tab_labels))
        finally:
            ui.close()

    def test_theme_uses_cool_toned_brand_palette_for_workbench_refresh(self):
        self.assertEqual(app.THEME["bg"], "#F3F7FB")
        self.assertEqual(app.THEME["panel"], "#FAFCFF")
        self.assertEqual(app.THEME["hero"], "#E8F0F8")
        self.assertEqual(app.THEME["accent"], "#5C7C99")
        self.assertEqual(app.THEME["muted"], "#607287")

    def test_dashboard_panels_use_calm_copy_and_supporting_status_layout(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertIn("悬浮窗会自动同步", ui.float_style_hint_label.cget("text"))
            self.assertIn("最近 30 天", ui.stats_summary_label.cget("text"))
        finally:
            ui.close()

    def test_dashboard_keeps_compact_plan_controls_without_today_route(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            plan_grid = ui.plan_box_frame.grid_info()
            style_grid = ui.style_box_frame.grid_info()
            stats_grid = ui.stats_box_frame.grid_info()

            self.assertFalse(hasattr(ui, "workbench_title_label"))
            self.assertFalse(hasattr(ui, "dashboard_focus_title_labels"))
            self.assertFalse(hasattr(ui, "metric_strip"))
            self.assertFalse(hasattr(ui, "stats_spotlight_value_labels"))
            self.assertTrue(hasattr(ui, "language_combo"))
            self.assertTrue(hasattr(ui, "lexicon_combo"))
            self.assertTrue(hasattr(ui, "daily_new_spinbox"))
            self.assertEqual(int(plan_grid["column"]), 0)
            self.assertEqual(int(plan_grid["row"]), 0)
            self.assertEqual(int(style_grid["column"]), 1)
            self.assertEqual(int(style_grid["row"]), 0)
            self.assertEqual(int(stats_grid["column"]), 0)
            self.assertEqual(int(stats_grid["row"]), 1)
            self.assertEqual(int(stats_grid["columnspan"]), 2)
        finally:
            ui.close()

    def test_dashboard_fits_primary_controls_without_vertical_scrollbar(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.geometry("1080x760")
            ui.root.update_idletasks()
            ui.root.update()

            self.assertFalse(hasattr(ui, "dashboard_canvas"))
            self.assertFalse(hasattr(ui, "dashboard_scrollbar"))
            self.assertLessEqual(ui.style_box_frame.winfo_height(), ui.content_notebook.winfo_height())
            self.assertLessEqual(ui.stats_box_frame.winfo_height(), ui.content_notebook.winfo_height())
        finally:
            ui.close()

    def test_dashboard_uses_compact_panel_spacing(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertLessEqual(max(map(int, ui.plan_box_frame.cget("padding"))), 14)
            self.assertLessEqual(max(map(int, ui.style_box_frame.cget("padding"))), 14)
            self.assertLessEqual(max(map(int, ui.stats_box_frame.cget("padding"))), 14)
            self.assertLess(ui.content_notebook.grid_info()["pady"][0], 14)
        finally:
            ui.close()

    def test_main_window_exposes_bottom_content_tabs(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertTrue(hasattr(ui, "content_notebook"))
            self.assertGreater(ui.content_notebook.winfo_height(), 240)

            tab_labels = [ui.content_notebook.tab(tab_id, "text") for tab_id in ui.content_notebook.tabs()]
            self.assertTrue(any("词库概览" in label for label in tab_labels))
            expected_news_tab = f"{dict(ui.settings_service.list_supported_languages())[ui.active_language_code()]} 日报"
            self.assertIn(expected_news_tab, tab_labels)
        finally:
            ui.close()

    def test_app_creates_single_style_object_and_main_widgets_initialize_once(self):
        ui = app.FloatVocabApp()
        try:
            self.assertIsNotNone(ui.style)
            self.assertTrue(hasattr(ui, "content_notebook"))
            self.assertTrue(hasattr(ui, "float_window"))
            self.assertTrue(hasattr(ui, "article_window"))
        finally:
            ui.close()

    def test_switching_to_language_without_lexicons_updates_hidden_language_state(self):
        temp_root = Path(app.APP_ROOT) / "tests" / "_tmp_ui_layout" / uuid.uuid4().hex
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = temp_root / "test.db"

        try:
            with mock.patch.object(app, "DB_PATH", db_path):
                ui = app.FloatVocabApp()
                try:
                    for row in ui.db.lexicons("ja"):
                        ui.db.delete_lexicon(row["id"])
                    ui.language_var.set("Japanese · ja")
                    ui.on_language_selected()
                    ui.root.update_idletasks()
                    ui.root.update()

                    self.assertEqual(ui.active_language_code(), "ja")
                    self.assertEqual(ui.lexicon_var.get(), "")
                finally:
                    ui.close()
        finally:
            for _ in range(5):
                try:
                    shutil.rmtree(temp_root, ignore_errors=False)
                    break
                except PermissionError:
                    time.sleep(0.1)
            else:
                shutil.rmtree(temp_root, ignore_errors=True)

    def test_destroying_main_window_closes_database_connection(self):
        ui = app.FloatVocabApp()
        ui.root.update_idletasks()
        ui.root.destroy()

        with self.assertRaises(sqlite3.ProgrammingError):
            ui.db.conn.execute("SELECT 1")

    def test_words_overview_loads_full_lexicon_instead_of_capping_at_80(self):
        temp_root = Path(app.APP_ROOT) / "tests" / "_tmp_ui_layout" / uuid.uuid4().hex
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = temp_root / "test.db"

        try:
            db = app.FloatVocabDB(db_path)
            lexicon_id = db.create_lexicon("UI Word List", "test")
            today = date.today().isoformat()
            for index in range(100):
                db.conn.execute(
                    """
                    INSERT INTO words
                    (lexicon_id, word, phonetic, meaning, example, next_review_date)
                    VALUES (?, ?, '', ?, '', ?)
                    """,
                    (lexicon_id, f"word-{index:03d}", f"meaning-{index:03d}", today),
                )
            plan = db.plan()
            db.save_plan(
                lexicon_id,
                plan["daily_new"],
                plan["target_date"] or (date.today() + timedelta(days=30)).isoformat(),
                plan["float_alpha"],
                plan["font_size"],
                plan["bg_color"],
                plan["widget_size"],
            )
            db.conn.close()

            with mock.patch.object(app, "DB_PATH", db_path):
                ui = app.FloatVocabApp()
                try:
                    ui.refresh_words()
                    self.assertEqual(len(ui.words_tree.get_children()), 100)
                finally:
                    ui.close()
        finally:
            for _ in range(5):
                try:
                    shutil.rmtree(temp_root, ignore_errors=False)
                    break
                except PermissionError:
                    time.sleep(0.1)
            else:
                shutil.rmtree(temp_root, ignore_errors=True)

    def test_words_overview_search_filters_by_word_and_meaning(self):
        temp_root = Path(app.APP_ROOT) / "tests" / "_tmp_ui_layout" / uuid.uuid4().hex
        temp_root.mkdir(parents=True, exist_ok=True)
        db_path = temp_root / "test.db"

        try:
            db = app.FloatVocabDB(db_path)
            lexicon_id = db.create_lexicon("Search Word List", "test")
            today = date.today().isoformat()
            rows = [
                ("abandon", "放弃"),
                ("apple", "苹果"),
                ("capacity", "容量"),
            ]
            for word, meaning in rows:
                db.conn.execute(
                    """
                    INSERT INTO words
                    (lexicon_id, word, phonetic, meaning, example, next_review_date)
                    VALUES (?, ?, '', ?, '', ?)
                    """,
                    (lexicon_id, word, meaning, today),
                )
            plan = db.plan()
            db.save_plan(
                lexicon_id,
                plan["daily_new"],
                plan["target_date"] or (date.today() + timedelta(days=30)).isoformat(),
                plan["float_alpha"],
                plan["font_size"],
                plan["bg_color"],
                plan["widget_size"],
            )
            db.conn.close()

            with mock.patch.object(app, "DB_PATH", db_path):
                ui = app.FloatVocabApp()
                try:
                    ui.words_search_var.set("app")
                    ui.refresh_words()
                    english_matches = [ui.words_tree.item(item, "values")[0] for item in ui.words_tree.get_children()]
                    self.assertEqual(english_matches, ["apple"])

                    ui.words_search_var.set("放弃")
                    ui.refresh_words()
                    chinese_matches = [ui.words_tree.item(item, "values")[0] for item in ui.words_tree.get_children()]
                    self.assertEqual(chinese_matches, ["abandon"])
                finally:
                    ui.close()
        finally:
            for _ in range(5):
                try:
                    shutil.rmtree(temp_root, ignore_errors=False)
                    break
                except PermissionError:
                    time.sleep(0.1)
            else:
                shutil.rmtree(temp_root, ignore_errors=True)

    def test_floating_window_keeps_action_buttons_visible_with_long_translation(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="；".join(["这是一个很长的中文释义，用来验证悬浮窗在内容很多的时候也不会把按钮挤出界面"] * 12),
                example="A long example sentence.",
                status="new",
                lexicon_name="test",
            )
            ui.float_window.flipped = True
            ui.float_window.apply_style()
            ui.float_window.render()
            ui.float_window.deiconify()
            ui.root.update_idletasks()
            ui.root.update()

            self.assertTrue(ui.float_window.word_label.winfo_ismapped())
            self.assertTrue(ui.float_window.action_frame.winfo_ismapped())
            self.assertTrue(ui.float_window.hint_label.winfo_ismapped())
            self.assertTrue(ui.float_window.drag_bar.winfo_ismapped())
        finally:
            ui.close()

    def test_floating_window_resize_keeps_small_card_above_readable_minimum_height(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.apply_style()
            ui.float_window.deiconify()
            ui.root.update_idletasks()
            ui.root.update()

            ui.float_window.resize_start_x = 0
            ui.float_window.resize_start_y = 0
            ui.float_window.resize_start_width = 300
            ui.float_window.resize_start_height = 210
            ui.float_window.resize(SimpleNamespace(x_root=-120, y_root=-120))
            ui.root.update_idletasks()
            ui.root.update()

            self.assertGreaterEqual(ui.float_window.winfo_width(), 300)
            self.assertGreaterEqual(ui.float_window.winfo_height(), 210)
        finally:
            ui.close()

    def test_floating_window_uses_premium_card_defaults_after_refresh(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.apply_style()
            ui.root.update_idletasks()
            ui.root.update()

            self.assertEqual(ui.float_window.card_header.cget("fg"), app.THEME["muted"])
            self.assertEqual(ui.float_window.action_frame.cget("bg"), ui.settings_service.get_plan_settings()["bg_color"])
            self.assertEqual(ui.float_window.drag_bar.cget("bg"), app.THEME["panel_alt"])
            self.assertGreater(int(ui.float_window.panel_frame.cget("padx")), 24)
        finally:
            ui.close()

    def test_floating_window_exposes_pronunciation_button_for_current_word(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="放弃",
                example="He decided to abandon the plan.",
                status="new",
                lexicon_name="test",
            )
            with mock.patch.object(ui.float_window, "play_pronunciation") as play_pronunciation:
                ui.float_window.pronunciation_button.invoke()

            play_pronunciation.assert_called_once_with()
        finally:
            ui.close()

    def test_floating_window_places_pronunciation_button_next_to_word(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="放弃",
                example="He decided to abandon the plan.",
                status="new",
                lexicon_name="test",
            )
            ui.float_window.apply_style()
            ui.float_window.render()
            ui.float_window.deiconify()
            ui.root.update_idletasks()
            ui.root.update()

            label_font = tkfont.Font(font=ui.float_window.word_label.cget("font"))
            text_width = label_font.measure(ui.float_window.word_label.cget("text"))
            text_right = (
                ui.float_window.word_label.winfo_rootx()
                + (ui.float_window.word_label.winfo_width() + text_width) // 2
            )
            gap = ui.float_window.pronunciation_button.winfo_rootx() - text_right
            self.assertLessEqual(gap, 16)
        finally:
            ui.close()

    def test_floating_window_play_pronunciation_does_nothing_without_real_audio(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="放弃",
                example="He decided to abandon the plan.",
                status="new",
                lexicon_name="test",
            )
            with mock.patch.object(app.threading, "Thread") as thread_cls:
                with mock.patch.object(ui.float_window, "resolve_pronunciation_audio_url", return_value=None):
                    ui.float_window.play_pronunciation()

            thread_cls.assert_not_called()
        finally:
            ui.close()

    def test_floating_window_prefers_word_audio_source_when_available(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="放弃",
                example="He decided to abandon the plan.",
                status="new",
                lexicon_name="test",
            )
            with mock.patch.object(ui.float_window, "resolve_pronunciation_audio_url", return_value="https://example.com/abandon.mp3"):
                with mock.patch.object(app.threading, "Thread") as thread_cls:
                    ui.float_window.play_pronunciation()

            thread_cls.assert_called_once_with(
                target=ui.float_window._play_audio_url,
                args=("https://example.com/abandon.mp3",),
                daemon=True,
            )
            thread_cls.return_value.start.assert_called_once_with()
        finally:
            ui.close()

    def test_extract_pronunciation_audio_url_returns_first_non_empty_audio(self):
        payload = [
            {
                "phonetics": [
                    {"text": "/əˈbændən/", "audio": ""},
                    {"text": "/əˈbændən/", "audio": "https://api.dictionaryapi.dev/media/pronunciations/en/abandon-us.mp3"},
                ]
            }
        ]

        self.assertEqual(
            app.extract_pronunciation_audio_url(payload),
            "https://api.dictionaryapi.dev/media/pronunciations/en/abandon-us.mp3",
        )

    def test_floating_window_disables_pronunciation_button_without_real_audio(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="放弃",
                example="He decided to abandon the plan.",
                status="new",
                lexicon_name="test",
            )
            with mock.patch.object(ui.float_window, "resolve_pronunciation_audio_url", return_value=None):
                ui.float_window.apply_style()
                ui.float_window.render()

            self.assertEqual(str(ui.float_window.pronunciation_button.cget("state")), "disabled")
        finally:
            ui.close()

    def test_floating_window_enables_pronunciation_button_with_real_audio(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="放弃",
                example="He decided to abandon the plan.",
                status="new",
                lexicon_name="test",
            )
            with mock.patch.object(ui.float_window, "resolve_pronunciation_audio_url", return_value="https://example.com/abandon.mp3"):
                ui.float_window.apply_style()
                ui.float_window.render()

            self.assertEqual(str(ui.float_window.pronunciation_button.cget("state")), "normal")
        finally:
            ui.close()

    def test_floating_window_uses_smaller_title_font_for_long_meaning_when_flipped(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.card = app.WordCard(
                id=1,
                word="aggressive",
                phonetic="/əˈɡresɪv/",
                meaning="故作勇为的；有进取心的；积极的；咄咄逼人的；主动出击的；强势的；好斗的",
                example="Aggressive sales tactics can backfire.",
                status="new",
                lexicon_name="test",
            )
            ui.float_window.flipped = True
            ui.float_window.apply_style()
            ui.float_window.render()
            ui.float_window.deiconify()
            ui.root.update_idletasks()
            ui.root.update()

            word_font_size = abs(int(tkfont.Font(font=ui.float_window.word_label.cget("font")).actual("size")))
            detail_font_size = abs(int(tkfont.Font(font=ui.float_window.detail_label.cget("font")).actual("size")))

            self.assertEqual(ui.float_window.word_label.cget("text"), "aggressive")
            self.assertIn("故作勇为的", ui.float_window.detail_label.cget("text"))
            self.assertLessEqual(word_font_size, 22)
            self.assertGreater(word_font_size, detail_font_size)
        finally:
            ui.close()

    def test_floating_window_prioritizes_meaning_over_example_for_dense_flipped_cards(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.card = app.WordCard(
                id=1,
                word="accommodate",
                phonetic="/əˈkɒmədeɪt/",
                meaning="容纳；给……提供住处；顺应；帮忙；调节；适应；和解；照顾",
                example="The hotel can accommodate up to 300 guests.",
                status="new",
                lexicon_name="test",
            )
            ui.float_window.flipped = True
            ui.float_window.apply_style()
            ui.float_window.render()

            detail_text = ui.float_window.detail_label.cget("text")
            self.assertIn("容纳", detail_text)
            self.assertNotIn("The hotel can accommodate", detail_text)
        finally:
            ui.close()

    def test_article_reader_matches_refreshed_reading_surface(self):
        ui = app.FloatVocabApp()
        try:
            self.assertEqual(ui.article_window.container.cget("bg"), app.THEME["panel"])
            self.assertEqual(ui.article_window.header.cget("bg"), app.THEME["hero"])
            self.assertEqual(ui.article_window.title_label.cget("fg"), app.THEME["text"])
            self.assertEqual(ui.article_window.meta_label.cget("fg"), app.THEME["muted"])
        finally:
            ui.close()


if __name__ == "__main__":
    unittest.main()
