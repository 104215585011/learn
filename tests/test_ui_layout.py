import shutil
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
            self.assertGreater(ui.content_notebook.winfo_height(), 240)

            tab_labels = [ui.content_notebook.tab(tab_id, "text") for tab_id in ui.content_notebook.tabs()]
            self.assertIn("词库概览", tab_labels)
            self.assertIn("英语日报", tab_labels)
        finally:
            ui.db.conn.close()
            ui.root.destroy()

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
                    ui.db.conn.close()
                    ui.root.destroy()
        finally:
            shutil.rmtree(temp_root)

    def test_floating_window_keeps_action_buttons_visible_with_long_translation(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.card = app.WordCard(
                id=1,
                word="abandon",
                phonetic="/əˈbændən/",
                meaning="；".join(["这是一个非常长的中文释义，用来验证悬浮窗在内容很多的时候也不会把按钮挤出界面"] * 12),
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
            ui.db.conn.close()
            ui.root.destroy()

    def test_floating_window_uses_smaller_title_font_for_long_meaning_when_flipped(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.card = app.WordCard(
                id=1,
                word="aggressive",
                phonetic="/əˈɡresɪv/",
                meaning="故作敢为的；有进取心的；积极的；咄咄逼人的；主动出击的；强势的；好斗的",
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
            self.assertIn("故作敢为的", ui.float_window.detail_label.cget("text"))
            self.assertLessEqual(word_font_size, 22)
            self.assertGreater(word_font_size, detail_font_size)
        finally:
            ui.db.conn.close()
            ui.root.destroy()

    def test_floating_window_prioritizes_meaning_over_example_for_dense_flipped_cards(self):
        ui = app.FloatVocabApp()
        try:
            ui.db.save_float_style(0.88, 32, "#F7FAF5", "small")
            ui.float_window.card = app.WordCard(
                id=1,
                word="accommodate",
                phonetic="/əˈkɒmədeɪt/",
                meaning="容纳；给……提供住宿；顺应；帮忙；调节；适应；和解；照顾",
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
            ui.db.conn.close()
            ui.root.destroy()


if __name__ == "__main__":
    unittest.main()
