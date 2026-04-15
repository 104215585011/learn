import unittest

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


if __name__ == "__main__":
    unittest.main()
