import unittest
from unittest import mock

import app


class AsyncErrorCallbackTests(unittest.TestCase):
    def test_save_selected_brief_worker_captures_exception_message_for_later_callback(self):
        ui = app.FloatVocabApp()
        scheduled = []
        errors = []

        def fake_after(_delay, callback):
            scheduled.append(callback)

        try:
            ui.root.after = fake_after
            with mock.patch.object(app.news_digest, "save_brief_to_favorites", side_effect=RuntimeError("boom")):
                with mock.patch.object(app.messagebox, "showerror", side_effect=lambda title, msg: errors.append((title, msg))):
                    ui._save_selected_brief_worker(123)

                    self.assertEqual(len(scheduled), 1)
                    scheduled[0]()

            self.assertEqual(len(errors), 1)
            self.assertIn("boom", errors[0][1])
        finally:
            ui.root.destroy()


if __name__ == "__main__":
    unittest.main()
