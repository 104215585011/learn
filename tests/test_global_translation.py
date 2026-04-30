import unittest
from unittest import mock

from floatvocab.global_translation import (
    calculate_bubble_position,
    capture_window_expired,
    current_cursor_position,
    moved_enough_for_selection,
    mymemory_language_candidates,
    normalize_selection_text,
    should_translate_clipboard_text,
    translate_to_chinese,
)


class GlobalTranslationLogicTests(unittest.TestCase):
    def test_normalize_selection_text_ignores_empty_or_oversized_values(self):
        self.assertIsNone(normalize_selection_text("  \n\t  "))
        self.assertIsNone(normalize_selection_text("x" * 601))

    def test_normalize_selection_text_collapses_whitespace(self):
        self.assertEqual(
            normalize_selection_text("  selected\n\n text\tfrom   another app  "),
            "selected text from another app",
        )

    def test_should_translate_clipboard_text_skips_empty_duplicate_and_internal_sentinel(self):
        self.assertFalse(should_translate_clipboard_text(""))
        self.assertFalse(should_translate_clipboard_text("__FLOATVOCAB_SELECTION_123"))
        self.assertFalse(should_translate_clipboard_text(" product ", "product"))
        self.assertTrue(should_translate_clipboard_text(" producto ", "product"))

    def test_capture_window_expired_checks_deadline(self):
        self.assertFalse(capture_window_expired(10.0, now=9.9))
        self.assertTrue(capture_window_expired(10.0, now=10.0))
        self.assertTrue(capture_window_expired(None, now=1.0))

    def test_moved_enough_for_selection_requires_meaningful_drag(self):
        self.assertFalse(moved_enough_for_selection(None, (10, 10)))
        self.assertFalse(moved_enough_for_selection((10, 10), (13, 14)))
        self.assertTrue(moved_enough_for_selection((10, 10), (20, 10)))

    def test_calculate_bubble_position_offsets_from_pointer_when_space_allows(self):
        self.assertEqual(
            calculate_bubble_position(100, 120, 320, 180, 1366, 768),
            (118, 138),
        )

    def test_calculate_bubble_position_clamps_near_screen_edges(self):
        self.assertEqual(
            calculate_bubble_position(1340, 740, 320, 180, 1366, 768),
            (1034, 576),
        )

    def test_translate_to_chinese_uses_mymemory_response_before_google_fallback(self):
        payload = '{"responseData":{"translatedText":"你好"},"responseStatus":200}'

        with mock.patch("floatvocab.global_translation.news_digest.fetch_text", return_value=payload):
            self.assertEqual(translate_to_chinese("hello"), "你好")

    def test_translate_to_chinese_uses_current_language_for_mymemory(self):
        payload = '{"responseData":{"translatedText":"谢谢"},"responseStatus":200}'

        with mock.patch("floatvocab.global_translation.news_digest.fetch_text", return_value=payload) as fetch_mock:
            self.assertEqual(translate_to_chinese("gracias", source_language_code="es"), "谢谢")

        self.assertIn("langpair=es|zh-CN", fetch_mock.call_args.args[0])

    def test_mymemory_language_candidates_prioritize_current_language_then_english(self):
        self.assertEqual(mymemory_language_candidates("es")[:2], ["es", "en"])
        self.assertEqual(mymemory_language_candidates("en")[:2], ["en", "es"])

    def test_translate_to_chinese_falls_back_to_existing_google_translator(self):
        payload = '{"responseData":{"translatedText":""},"responseStatus":429}'

        with mock.patch("floatvocab.global_translation.news_digest.fetch_text", return_value=payload):
            with mock.patch("floatvocab.global_translation.news_digest.translate_text", return_value="备用翻译"):
                self.assertEqual(translate_to_chinese("hello"), "备用翻译")

    def test_current_cursor_position_returns_zero_without_windows_api(self):
        with mock.patch("floatvocab.global_translation.ctypes.windll", None, create=True):
            self.assertEqual(current_cursor_position(), (0, 0))


if __name__ == "__main__":
    unittest.main()
