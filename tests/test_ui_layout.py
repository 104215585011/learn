import shutil
import sqlite3
import time
import tkinter.font as tkfont
import unittest
import uuid
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import app


class AppLayoutTests(unittest.TestCase):
    def test_main_window_exposes_bottom_content_tabs(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertTrue(hasattr(ui, "content_notebook"))
            self.assertTrue(hasattr(ui, "language_combo"))
            self.assertGreater(ui.content_notebook.winfo_height(), 240)

            tab_labels = [ui.content_notebook.tab(tab_id, "text") for tab_id in ui.content_notebook.tabs()]
            self.assertIn("词库概览", tab_labels)
            expected_news_tab = f"{dict(ui.settings_service.list_supported_languages())[ui.active_language_code()]} 日报"
            self.assertIn(expected_news_tab, tab_labels)
        finally:
            ui.root.destroy()

    def test_switching_to_language_without_lexicons_disables_lexicon_selector(self):
        ui = app.FloatVocabApp()
        try:
            ui.language_var.set("Japanese · ja")
            ui.on_language_selected()
            ui.root.update_idletasks()
            ui.root.update()

            self.assertEqual(ui.active_language_code(), "ja")
            self.assertEqual(str(ui.lexicon_combo.cget("state")), "disabled")
            self.assertIn("还没有词库", ui.lexicon_state_label.cget("text"))
            self.assertIn("没有配置日报源", ui.brief_summary.get("1.0", "end").strip())
        finally:
            ui.root.destroy()

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
            ui.root.destroy()

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
            ui.root.destroy()

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
            ui.root.destroy()


if __name__ == "__main__":
    unittest.main()
