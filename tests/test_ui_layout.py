import unittest
import sqlite3

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
            ui.root.destroy()

    def test_destroying_main_window_closes_database_connection(self):
        ui = app.FloatVocabApp()
        ui.root.update_idletasks()
        ui.root.destroy()

        with self.assertRaises(sqlite3.ProgrammingError):
            ui.db.conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
